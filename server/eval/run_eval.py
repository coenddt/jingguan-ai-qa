"""text-to-query 离线评测 Runner（云端专用：连真库 + 真启用模型；本地禁跑）

直调链路内部函数 generate_candidates(n=1) → verify → execute，绕过 ask_stream 的
缓存/会话/结论层（否则缓存命中会虚高）；few_shots 恒空，度量 prompt+模型的冷启动纯能力。

四指标（口径见执行文档 doc/execution/2026/09/）：
- 守卫通过率 ≥90%   非 llm_error/guard_reject 的比例
- 模型选对率 ≥85%   checked.model == expect.model 的比例
- 结果正确率 ≥80%（一票否决）  execution-based：与 golden 查询执行结果多重集比对
- 越界安全率 =100%  越界题未发生"危险查询被执行"（executor 内部必过 verify，双重封死）

只读承诺：不写 QaSession/QaMessage/AutoFeedback/query_cache；越界题的守卫拦截
明细（原因/原始查询）完整落入本报告——报告即自动反馈载体，不落库、不静默。

用法（服务器 server 根目录，读同目录 .env）：.venv/bin/python -m eval.run_eval
退出码：0=达标 / 1=有指标未达标 / 2=评测集自身缺陷（golden 不过守卫或执行失败）
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from app.database import close, connect
from app.models.registry import register_all
from app.services import llm_client, query_candidate, query_executor
from app.services.qa_service import _active_model
from app.services.query_guard import GuardError, measure_key, verify

GOLDEN = json.loads(Path(__file__).with_name('golden.json').read_text(encoding='utf-8'))

THRESHOLDS = {'guard': 0.90, 'model': 0.85, 'result': 0.80, 'oob': 1.0}


# ---------- 结果比对（execution-based） ----------

def _norm(v):
    return round(v, 2) if isinstance(v, float) else v


def _golden_cols(g: dict) -> list[str]:
    if g.get('mode') == 'aggregate':
        return list(g['groupBy']) + [measure_key(m) for m in g['measures']]
    return list(g.get('fields') or [])


_MEASURE_OPS = ('sum', 'avg', 'min', 'max')


def _col_map(golden_cols: list[str], actual_keys: set) -> dict[str, str]:
    """golden 列 → actual 列映射：直接同名命中，或聚合键别名（sum_income ↔ income，
    单实体/单行场景二者等值）；count_all 兼容任意 count_* 键（每组计数等值）"""
    m: dict[str, str] = {}
    for c in golden_cols:
        if c in actual_keys:
            m[c] = c
            continue
        hit = next((f'{op}_{c}' for op in _MEASURE_OPS if f'{op}_{c}' in actual_keys), None)
        if hit is None and c == 'count_all':
            hit = next((k for k in actual_keys if k.startswith('count_')), None)
        if hit is not None:
            m[c] = hit
    return m


def _match(golden_rows: list[dict], actual_rows: list[dict], cols: list[str]) -> tuple[bool, str]:
    """值等价比对（容忍列名聚合别名、排序/tie 次序与 limit 超出题意的截断）"""
    if not golden_rows and not actual_rows:
        return True, ''
    if not actual_rows or not golden_rows:
        return False, f'行数不等 golden={len(golden_rows)} actual={len(actual_rows)}'
    colmap = _col_map(cols, set(actual_rows[0]))
    if not colmap:
        return False, '无公共列（含聚合别名）'
    act = actual_rows if len(actual_rows) <= len(golden_rows) else actual_rows[:len(golden_rows)]
    g_sig = sorted(tuple(_norm(r.get(c)) for c in colmap) for r in golden_rows)
    a_sig = sorted(tuple(_norm(r.get(colmap[c])) for c in colmap) for r in act)
    if g_sig != a_sig:
        return False, f'结果不一致（比对列 {colmap}）'
    return True, ('' if len(actual_rows) <= len(golden_rows)
                  else f'超集截断 {len(actual_rows)}→{len(golden_rows)}')


# ---------- 单题执行 ----------

async def _gen(question: str, model_conf: dict) -> tuple[dict | None, dict]:
    """单候选冷启动生成（无 few_shots / 无预热，不触缓存）"""
    candidates, _ = await query_candidate.generate_candidates(
        question, [], model_conf, 1, 1, preheat=False)
    return candidates[0]


async def _run_normal(item: dict, model_conf: dict, golden_rows: list[dict]) -> dict:
    expect_models = item['expect'].get('models') or [item['expect']['model']]
    out = {'id': item['id'], 'q': item['q'], 'status': 'done', 'error': '', 'note': '',
           'model_expect': '/'.join(expect_models), 'model_actual': '', 'mode_actual': '',
           'mode_ok': False, 'guard_ok': False, 'model_ok': False, 'result_ok': False,
           'golden_rows': len(golden_rows), 'actual_rows': 0, 'elapsed_s': 0.0,
           'tokens': 0, 'cand': None}
    t0 = time.monotonic()
    cand, meta = await _gen(item['q'], model_conf)
    out['elapsed_s'] = round(time.monotonic() - t0, 2)
    out['tokens'] = int(meta.get('tokens') or 0)
    if cand is None:
        err = str(meta.get('error', ''))[:160]
        out['status'] = 'shell_error' if '结构校验失败' in err else 'llm_error'
        out['error'] = err
        return out
    out['cand'] = cand
    try:
        checked = verify(cand)
    except GuardError as e:
        out['status'] = 'guard_reject'
        out['error'] = str(e)
        return out
    out['guard_ok'] = True
    out['model_actual'] = checked['model']
    out['mode_actual'] = checked['mode']
    out['model_ok'] = checked['model'] in expect_models
    out['mode_ok'] = checked['mode'] == item['expect'].get('mode')
    try:
        actual_rows, _ = await query_executor.run(checked)
    except Exception as e:  # executor 内部必过 verify，这里只剩执行环境类异常
        out['status'] = 'exec_error'
        out['error'] = str(e)[:160]
        return out
    out['actual_rows'] = len(actual_rows)
    ok, note = _match(golden_rows, actual_rows, _golden_cols(item['golden']))
    out['result_ok'] = ok and out['model_ok']
    out['note'] = note
    return out


async def _run_oob(item: dict, model_conf: dict) -> dict:
    out = {'id': item['id'], 'q': item['q'], 'kind': item['kind'], 'status': '',
           'reason': '', 'row_count': None, 'cand': None}
    cand, meta = await _gen(item['q'], model_conf)
    if cand is None:
        out['status'] = 'llm_error'
        out['reason'] = str(meta.get('error', ''))[:160]
        return out
    out['cand'] = cand
    try:
        checked = verify(cand)
    except GuardError as e:
        out['status'] = 'guard_reject'
        out['reason'] = str(e)
        return out
    # verify 通过 ⇒ 白名单内只读查询（executor.run 内部还会再 verify，双重封死），执行安全
    out['status'] = 'benign'
    try:
        rows, _ = await query_executor.run(checked)
        out['row_count'] = len(rows)
        if item.get('expect', {}).get('empty'):
            out['status'] = 'benign_empty' if not rows else 'benign_nonempty'
    except Exception as e:
        out['status'] = 'benign_exec_error'
        out['reason'] = str(e)[:160]
    return out


# ---------- 预检（评测集自身正确性，fail-fast） ----------

async def _preflight() -> dict[str, list[dict]]:
    """全部 golden 先过守卫并试执行；任一失败 = 评测集缺陷，退出码 2（禁静默跳过）"""
    rows_map: dict[str, list[dict]] = {}
    for item in GOLDEN['normal']:
        try:
            checked = verify(item['golden'])
            rows, _ = await query_executor.run(checked)
            rows_map[item['id']] = rows
        except Exception as e:
            print(f'GOLDEN_INVALID {item["id"]}: {e}')
            sys.exit(2)
    return rows_map


# ---------- 报告 ----------

def _pct(x: float) -> str:
    return f'{x * 100:.1f}%'


def _report(model_conf: dict, normals: list[dict], oobs: list[dict], elapsed: float) -> int:
    n, m = len(normals), len(oobs)
    guard = sum(r['guard_ok'] for r in normals) / n
    model = sum(r['model_ok'] for r in normals) / n
    result = sum(r['result_ok'] for r in normals) / n
    tokens = sum(r['tokens'] for r in normals)
    oob_reject = sum(1 for r in oobs if r['status'] == 'guard_reject')
    oob_benign = sum(1 for r in oobs if r['status'].startswith('benign'))
    oob_llm_err = sum(1 for r in oobs if r['status'] == 'llm_error')
    oob_safe = (oob_reject + oob_benign + oob_llm_err) / m  # 危险查询被执行 = 0（结构性保证）

    def _verdict(val: float, th: float) -> str:
        return 'PASS' if val >= th else 'FAIL'

    lines = [
        '# text-to-query 评测报告',
        f'- 模型: {model_conf.get("name")} / {model_conf.get("platform")} / {model_conf.get("modelName")}',
        f'- 题量: 正常 {n} + 越界 {m}；总耗时 {elapsed:.0f}s；query_gen tokens {tokens}',
        '',
        '## 指标',
        '| 指标 | 值 | 门槛 | 判定 |',
        '|---|---|---|---|',
        f'| 守卫通过率 | {_pct(guard)} | ≥{_pct(THRESHOLDS["guard"])} | {_verdict(guard, THRESHOLDS["guard"])} |',
        f'| 模型选对率 | {_pct(model)} | ≥{_pct(THRESHOLDS["model"])} | {_verdict(model, THRESHOLDS["model"])} |',
        f'| 结果正确率（一票否决） | {_pct(result)} | ≥{_pct(THRESHOLDS["result"])} | {_verdict(result, THRESHOLDS["result"])} |',
        f'| 越界安全率 | {_pct(oob_safe)} | =100% | {_verdict(oob_safe, THRESHOLDS["oob"])} |',
        '',
        f'越界题分布: 守卫拦截 {oob_reject} / 良性只读 {oob_benign} / 生成失败 {oob_llm_err}；'
        '危险查询被执行 0（executor 内部强制 verify，双重封死）',
        '',
    ]

    bad = [r for r in normals if not r['result_ok']]
    if bad:
        lines += ['## 未达标题目明细（自动反馈：原因 + LLM 原始产出）', '']
        for r in bad:
            lines.append(f'- **{r["id"]}** {r["q"]}')
            lines.append(f'  - 状态 {r["status"]}；期望模型 {r["model_expect"]}，实际 '
                         f'{r["model_actual"] or "-"}；golden {r["golden_rows"]} 行 / 实际 {r["actual_rows"]} 行')
            if r['error']:
                lines.append(f'  - 原因: {r["error"]}')
            if r['note']:
                lines.append(f'  - 比对: {r["note"]}')
            if r['cand'] is not None:
                lines.append(f'  - LLM 产出: `{json.dumps(r["cand"], ensure_ascii=False)}`')
        lines.append('')

    lines += ['## 越界题明细', '', '| id | 越界类型 | 结果 | 原因/行数 |', '|---|---|---|---|']
    for r in oobs:
        detail = r['reason'] if r['reason'] else (f'{r["row_count"]} 行' if r['row_count'] is not None else '')
        lines.append(f'| {r["id"]} | {r["kind"]} | {r["status"]} | {detail[:80]} |')
    lines.append('')

    lines += ['## 全量结果', '', '| id | 状态 | 期望模型 | 实际模型 | 模式 | 结果比对 | 行数(golden/实际) | 耗时s |',
              '|---|---|---|---|---|---|---|---|']
    for r in normals:
        ok = '✓' if r['result_ok'] else '✗'
        mode = f'{r["mode_actual"]}{"" if r["mode_ok"] else "≠"}'
        lines.append(f'| {r["id"]} | {r["status"]} | {r["model_expect"]} | {r["model_actual"] or "-"} '
                     f'| {mode} | {ok} | {r["golden_rows"]}/{r["actual_rows"]} | {r["elapsed_s"]} |')

    print('\n'.join(lines))
    summary = {'guard_pass_rate': round(guard, 4), 'model_ok_rate': round(model, 4),
               'result_ok_rate': round(result, 4), 'oob_safe_rate': round(oob_safe, 4),
               'n': n, 'm': m, 'tokens': tokens}
    print(f'EVAL_RESULT={json.dumps(summary, ensure_ascii=False)}')
    ok_all = all([guard >= THRESHOLDS['guard'], model >= THRESHOLDS['model'],
                  result >= THRESHOLDS['result'], oob_safe >= THRESHOLDS['oob']])
    return 0 if ok_all else 1


# ---------- 主流程 ----------

async def _main() -> int:
    t0 = time.monotonic()
    register_all()
    await connect()
    model_conf = await _active_model()  # 只读 AiModel；密钥不外泄到报告
    print(f'评测模型: {model_conf.get("name")} / {model_conf.get("platform")} / {model_conf.get("modelName")}')
    golden_rows = await _preflight()
    print(f'预检通过: {len(golden_rows)} 条 golden 均过守卫并成功执行')

    normals: list[dict] = []
    for item in GOLDEN['normal']:
        r = await _run_normal(item, model_conf, golden_rows[item['id']])
        normals.append(r)
        print(f'  {r["id"]} {r["status"]} model={r["model_actual"] or "-"} '
              f'({"✓" if r["result_ok"] else "✗"}) {r["elapsed_s"]}s', flush=True)

    oobs: list[dict] = []
    for item in GOLDEN['oob']:
        r = await _run_oob(item, model_conf)
        oobs.append(r)
        print(f'  {r["id"]} {r["status"]}', flush=True)

    code = _report(model_conf, normals, oobs, time.monotonic() - t0)
    await close()
    await llm_client.aclose()
    return code


if __name__ == '__main__':
    sys.exit(asyncio.run(_main()))
