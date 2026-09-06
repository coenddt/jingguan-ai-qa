"""问数编排：会话 →(缓存/LLM)查询 → 守卫 → 执行 → 统计/图表 → 结论 → 落库

流式编排 ask_stream：以 SSE 事件逐步产出真实中间产物——
session（会话就绪）→ steps（步骤清单）→ step（单步 running/done/fail）→
block（findings/table/stats/chart/text/follow_ups 逐块）→ done（最终完整结果，与落库 aiMeta 一致）→ 异常统一转 error 事件。
"""

import json
import time
import traceback
from typing import cast

from app.agent.prompts import scenario_params
from app.agent.schema_registry import DIM_ENUMS, FIELD_COMMENTS
from app.agent.step_tracker import StepTracker
from app.config import (
    MAX_LIMIT,
    QA_CHART,
    QA_CONCLUSION_ROWS,
    QA_FOLLOW_UPS,
    QA_HOT_FUZZY_SCORE,
    QA_NUMERIC_FIELDS,
    QA_PREHEAT_ENABLED,
    QA_QUERY_CANDIDATE_CONCURRENCY,
    QA_QUERY_CANDIDATES,
    QA_SOURCES,
    QA_TIER,
    QA_TIME_DIMS,
    QA_TITLE_MAX,
)
from app.db.mongo_store import store
from app.errors import BusinessError
from app.log import get_request_id, log
from app.services import (
    auto_feedback,
    llm_client,
    query_cache,
    query_candidate,
    query_executor,
)
from app.services.json_schema_shell import ShellError
from app.services.query_clarify import build_query_hint, completeness_issues
from app.services.query_guard import GuardError, measure_key, verify


async def _active_model() -> dict:
    m = await store.query_one(
        'AiModel($condition:@c0) { _id, name, platform, baseUrl, apiKey, modelName }',
        {'c0': {'enabled': True}})
    if not m or not m.get('apiKey'):
        raise BusinessError('无启用的 AI 模型，请先在模型配置中启用', 400)
    if m.get('platform') not in llm_client.PLATFORM_PRESETS:
        raise BusinessError('启用中的 AI 模型缺少有效平台配置，请删除后重新添加', 400)
    return m


def _round_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    return out


# 服务端 join 注入字段的中文表头兜底（不入 schema 描述，避免污染 LLM 可查字段白名单）
_INJECTED_HEADERS = {'commercialGoal': '商业目标(万元)'}

# 聚合键算子 → 中文（measure_key 形如 sum_contractAmt / count_all，见 query_guard.measure_key）
_OP_HEADERS = {'sum': '合计', 'avg': '均值', 'count': '记录数', 'min': '最小', 'max': '最大'}


def _zh_name(model: str, name: str) -> str:
    """字段/聚合键 → 中文名：字段中文注释优先 → join 注入字段兜底 → 聚合键(字段中文+算子) → 原样保底。

    用户可见名（表头/发现/图表标题图例）统一走 schema_registry.FIELD_COMMENTS 中文注释
    （唯一事实源），保证与数据口径一致；不命中时保持英文原样，避免名称失真。
    """
    comments = FIELD_COMMENTS.get(model, {})
    zh = comments.get(name)
    if zh:
        return zh
    zh = _INJECTED_HEADERS.get(name)
    if zh:
        return zh
    op, _, field = name.partition('_')
    fzh = comments.get(field)
    if op in _OP_HEADERS and (field == 'all' or fzh):
        return _OP_HEADERS[op] if field == 'all' else f'{fzh}{_OP_HEADERS[op]}'
    return name


def _zh_table_headers(model: str, columns: list[str]) -> list[str]:
    """表头中文化：逐列走 _zh_name"""
    return [_zh_name(model, c) for c in columns]


def _build_stats(rows: list[dict], numeric_field: str | None) -> dict:
    if not rows or not numeric_field:
        return {'count': len(rows), 'avg': 0, 'max': 0, 'max_of': '-', 'min': 0, 'min_of': '-'}
    vals = [r[numeric_field] for r in rows if isinstance(r.get(numeric_field), (int, float))]
    if not vals:
        return {'count': len(rows), 'avg': 0, 'max': 0, 'max_of': '-', 'min': 0, 'min_of': '-'}
    mx = max(vals)
    mn = min(vals)
    max_of = next((str(r.get(k, '')) for r in rows if r.get(numeric_field) == mx
                   for k in r if k != numeric_field and isinstance(r.get(k), str) and r[k]), '-')
    min_of = next((str(r.get(k, '')) for r in rows if r.get(numeric_field) == mn
                   for k in r if k != numeric_field and isinstance(r.get(k), str) and r[k]), '-')
    return {
        'count': len(rows),
        'avg': round(sum(vals) / len(vals), 2),
        'max': round(mx, 2), 'max_of': max_of,
        'min': round(mn, 2), 'min_of': min_of,
    }


def _build_chart(question: str, q: dict, rows: list[dict]) -> dict | None:
    """依据查询形态推导 4 类图：聚合→柱/条/饼，时间维→折线"""
    if not rows:
        return None
    if q['mode'] == 'aggregate':
        dim = q['groupBy'][0]
        mk = measure_key(q['measures'][0])
        x = [str(r.get(dim, '')) for r in rows]
        series = [round(float(r.get(mk) or 0), 2) for r in rows]
    else:
        numeric = [f for f in q['fields'] if isinstance(rows[0].get(f), (int, float))]
        if not numeric:
            return None
        dim = next((f for f in q['fields'] if isinstance(rows[0].get(f), str) and f not in ('signDate',)), None)
        mk = numeric[0]
        x = [str(r.get(dim, ''))[:8] if dim else str(i + 1) for i, r in enumerate(rows)]
        series = [round(float(r.get(mk) or 0), 2) for r in rows]
    pie_keywords: tuple[str, ...] = cast(tuple[str, ...], QA_CHART['pie_keywords'])
    pie_max_rows = cast(int, QA_CHART['pie_max_rows'])
    amount_markers: tuple[str, ...] = cast(tuple[str, ...], QA_CHART['amount_markers'])
    if any(w in question for w in pie_keywords) and len(rows) <= pie_max_rows:
        ctype = 'pie'
    elif dim in QA_TIME_DIMS:
        ctype = 'line'
    else:
        ctype = 'bar'
    unit = QA_CHART['amount_unit'] if any(m in mk for m in amount_markers) else ''
    mk_zh = _zh_name(q.get('model', ''), mk)
    title = f"{mk_zh.replace('(万元)', '') if unit else mk_zh}分布"
    return {'type': ctype, 'title': title, 'unit': unit, 'series': series, 'x': x,
            'legend': [mk_zh] if ctype != 'pie' else x}


def _build_findings(stats: dict, numeric_field: str | None, model: str = '') -> list[str]:
    if not stats.get('count'):
        return ['未查询到符合条件的数据']
    out = [f"共 {stats['count']} 条记录，均值 {stats['avg']}"]
    if numeric_field:
        out.append(f"{_zh_name(model, numeric_field)} 最大值 {stats['max']}（{stats['max_of']}），"
                   f"最小值 {stats['min']}（{stats['min_of']}）")
    return out


def _step_ev(tracker: StepTracker, idx: int) -> dict:
    """单步完成/失败事件（done=True→done；有 desc 未 done→fail）"""
    it = tracker.items[idx]
    status = 'done' if it['done'] else 'fail'
    return {'type': 'step', 'index': idx, 'title': it['title'], 'desc': it['desc'], 'status': status}


def _step_running(idx: int) -> dict:
    return {'type': 'step', 'index': idx, 'status': 'running'}


def _log_step(tracker: StepTracker, idx: int) -> None:
    it = tracker.items[idx]
    log('info', 'ask_step', index=idx, title=it['title'], elapsed_ms=it['elapsed'],
        status='done' if it['done'] else 'fail', desc=it['desc'])


async def _build_clarify_resp(session: dict, tracker: StepTracker, model_conf: dict,
                              t0: float, tokens: int, clarify) -> dict:
    """clarify: str 纯文本（老会话/软门回退）| dict{'text','question','fields'} 结构化澄清表单。
    content 落库取 text，aiMeta 携带完整 clarify 对象。"""
    text = clarify if isinstance(clarify, str) else clarify['text']
    return {
        'session_id': session['_id'],
        'steps': tracker.out(),
        'findings': [], 'columns': [], 'rows': [],
        'stats': {'count': 0, 'avg': 0, 'max': 0, 'max_of': '-', 'min': 0, 'min_of': '-'},
        'chart': None,
        'text': text, 'follow_ups': [],
        'clarify': clarify,
        'query_source': None, 'truncated': False, 'row_count': 0,
        'meta': {
            'elapsed_s': round(time.monotonic() - t0, 2), 'tokens': tokens,
            'model': model_conf['name'], 'modelName': model_conf.get('modelName', ''),
            'platform': model_conf['platform'],
        },
    }


async def ask_stream(question: str, session_id: str | None, source_keys: list[str],
                     user_name: str = '管理员'):
    """流式问数编排：逐步 yield SSE 事件；逻辑与非流式版一致，异常统一转 error 事件"""
    t0 = time.monotonic()
    tracker = StepTracker()
    n_sources = len(source_keys) if source_keys else sum(len(g['items']) for g in QA_SOURCES)
    session: dict | None = None
    tokens = 0
    model_conf: dict | None = None
    saved = False
    log('info', 'ask_start', question=question, sources=n_sources,
        request_id=get_request_id())
    try:
        # 会话先行：前端尽早挂载消息流；失败（如无启用模型）不会遗留空会话
        session = await _ensure_session(session_id, question)
        yield {'type': 'session', 'data': {'session_id': session['_id']}}

        yield {'type': 'steps', 'data': [{'title': t} for t in tracker.STEPS]}
        tracker.done(0, f'识别问题意图，在 {n_sources} 个已选数据源分组中确定目标模型')
        yield _step_ev(tracker, 0)
        _log_step(tracker, 0)

        model_conf = await _active_model()
        q_params = scenario_params('query_gen')
        rows: list[dict] | None = None
        truncated = False
        used_query: dict | None = None
        tokens = 0
        query_source = 'llm'            # 精确缓存命中后覆盖为 'exact_cache'
        query_tier = 'exact'            # 热度分级：exact/warm/cold（阶段三）
        retries = 0                     # LLM 重试轮数（首轮通过为 0）
        query_raw: dict | None = None   # LLM 最后产出的原始查询（verify 前）；缓存命中为 None

        yield _step_running(1)
        ex = await query_cache.exact_hit(question)
        if ex:
            try:
                checked = verify(ex['template'])
                rows, truncated = await query_executor.run(checked)
                used_query = checked
                query_source = 'exact_cache'
                tracker.done(1, f'命中精确问法缓存，复用模板：{json.dumps(checked, ensure_ascii=False)}')
                yield _step_ev(tracker, 1)
                _log_step(tracker, 1)
                log('info', 'ask_tier', tier='exact', candidates=0, concurrency=0, best_score='-')
            except GuardError as e:
                # 缓存命中却被守卫拦下 → 静默失守点：立即自动反馈（缓存模板与 schema 脱节，是上一步病灶）
                await auto_feedback.record(
                    category='guard',
                    trigger_point='cache_exact_hit_guard',
                    reason=str(e),
                    layer='内层防护罩-守卫校验拦截',
                    upstream='精确查询缓存模板(QaMessage.aiMeta)已不通过 query_guard.verify——模板被污染或与 schema 脱节',
                    fix_hint='拿 queryRaw 与 reason 定位 query_cache.exact_hit 命中逻辑，核查该模板为何越界；修复缓存模板或 schema 后回放验证',
                    question=question, query_raw=ex['template'])

        if rows is None:
            # —— A：生成前意图门（已降级为软提示，不阻断链路）：判定"缺条件"不再弹表单追问，
            # 而是落自动反馈留痕 + 把缺省策略作为 hint 注入 query_gen（先查再说，缺省口径兜底）——
            hint = ''
            try:
                intent, _ret = await llm_client.invoke('intent_gate', {'question': question}, model_conf)
                if not isinstance(intent, dict):
                    intent = {}
                if intent.get('need_more_info'):
                    dims = [d for d in (intent.get('dimensions') or []) if d in DIM_ENUMS]
                    hint = build_query_hint(dims)
                    log('info', 'ask_intent_gate', need_more_info=True, dims=dims)
                    # 门被策略性放行 → 自动反馈（告警优先）：高频出现说明意图门 prompt 或问题本身需回溯
                    await auto_feedback.record(
                        category='fallback',
                        trigger_point='intent_gate_bypass',
                        reason=f'意图门判定条件不足（dimensions={dims}），按"先查再说"策略放行，以缺省口径兜底',
                        layer='内层防护罩-意图门(已降级软提示，不拦截)',
                        upstream='intent_gate 提示词判定保守或问题含糊；query_gen 缺省规则(年份默认2026/全量汇总)兜底',
                        fix_hint='若该告警高频出现：收紧 intent_gate 提示词或补 few-shot；若问题确属含糊：改在结论/追问层引导',
                        question=question)
            except Exception:  # noqa: BLE001  意图门软门：异常不阻断，直接走 query_gen
                hint = ''

            few = await query_cache.top_k_fuzzy(question)
            # 阶段三：热度分级——best fuzzy score 命中阈值 → warm(低开销 1 候选) / cold(候选兜底)
            best_score = few[0]['score'] if few else 0.0
            query_tier = 'warm' if best_score >= QA_HOT_FUZZY_SCORE else 'cold'
            tier_cfg = QA_TIER[query_tier]
            n_cands = max(int(tier_cfg['candidates'] or QA_QUERY_CANDIDATES), 1)
            conc = max(int(tier_cfg['concurrency'] or QA_QUERY_CANDIDATE_CONCURRENCY), 1)
            candidates, prime_meta = await query_candidate.generate_candidates(
                question, few, model_conf, n_cands, conc, preheat=bool(QA_PREHEAT_ENABLED),
                hint=hint)
            cache_hit = cache_miss = 0
            for _, meta in candidates:
                if meta.get('ok') and meta.get('tokens'):
                    tokens += int(meta['tokens'])
                cache_hit += int(meta.get('cache_hit') or 0)
                cache_miss += int(meta.get('cache_miss') or 0)
            query_raw = (candidates[0][0]) if candidates and candidates[0][0] is not None else None
            checked_list, cand_statuses = query_candidate.pick_checked(candidates)
            log('info', 'ask_tier', tier=query_tier, candidates=n_cands, concurrency=conc,
                best_score=round(best_score, 3))
            if prime_meta:
                log('info', 'ask_preheat', ok=prime_meta.get('ok', False),
                    elapsed_s=prime_meta.get('elapsed_s'),
                    cache_hit=prime_meta.get('cache_hit'), cache_miss=prime_meta.get('cache_miss'),
                    error=prime_meta.get('error', ''))
            log('info', 'ask_candidates', generated=len(candidates), passed=len(checked_list),
                cache_hit=cache_hit, cache_miss=cache_miss,
                statuses=json.dumps(
                    [{k: s.get(k) for k in ('idx', 'status', 'error') if s.get(k) is not None}
                     for s in cand_statuses], ensure_ascii=False))
            tracker.done(1, f'LLM 并行生成 {len(candidates)} 个候选查询，守卫通过 {len(checked_list)} 个，择优执行')
            yield _step_ev(tracker, 1)
            _log_step(tracker, 1)

            # 择优执行：按候选序尝试执行；全部失败 → 串行错误回传修正重试（原行为兜底）
            yield _step_running(2)
            # —— B：生成后完整度校验（硬门，收紧版）：仅统计/目标表缺年份(口径不明)时拦截追问，
            # 其余一律放行执行（空结果/全量由结论与追问建议承接，先查再说）——
            if checked_list:
                issues = completeness_issues(checked_list[0])
                if issues is not None:
                    await auto_feedback.record(
                        category='guard',
                        trigger_point='query_clarify_block',
                        reason=f'统计/目标表查询缺年份，口径不明：{json.dumps(checked_list[0], ensure_ascii=False)}',
                        layer='内层防护罩-完整度校验',
                        upstream='query_gen 未按"年份缺省取 2026"缺省规则生成条件',
                        fix_hint='核查 query_gen 提示词缺省年份规则为何未生效；若高频可把 year 缺省下沉到守卫规范化',
                        question=question, query_raw=query_raw)
                    tracker.done(2, f'查询缺少必要条件，已追问澄清：{issues["text"]}')
                    yield _step_ev(tracker, 2)
                    _log_step(tracker, 2)
                    form = {'text': issues['text'], 'question': question, 'fields': issues['fields']}
                    resp = await _build_clarify_resp(session, tracker, model_conf, t0, tokens, form)
                    await _save_messages(session, question, resp, user_name)
                    saved = True
                    yield {'type': 'done', 'data': resp}
                    return
            last_err = ''
            for checked in checked_list:
                try:
                    rows, truncated = await query_executor.run(checked)
                    used_query = checked
                    break
                except (GuardError, BusinessError, RuntimeError, TimeoutError) as e:
                    rows = None
                    last_err = str(e)
                    log('info', 'ask_candidate_exec_fail', error=last_err)

            if rows is not None:
                tracker.done(2, f'守卫校验通过，择优执行取数返回 {len(rows)} 条')
                yield _step_ev(tracker, 2)
                _log_step(tracker, 2)
                retries = 0
            else:
                # 全部候选失败 → 串行回传 LLM 修正重试（保留原兜底，保证正确性）
                base_bad = checked_list[-1] if checked_list else (query_raw or {})
                for attempt in range(q_params['retries']):
                    try:
                        q, ret = await llm_client.invoke(
                            'query_gen',
                            {'question': question, 'bad_query': base_bad, 'error': last_err},
                            model_conf)
                        tokens += ret['total_tokens']
                        log('info', 'llm_call', scenario='query_gen_retry', attempt=attempt,
                            elapsed_s=ret.get('elapsed_s'), tokens=ret.get('total_tokens'),
                            cache_hit=ret.get('cache_hit_tokens'),
                            cache_miss=ret.get('cache_miss_tokens'))
                        base_bad = cast(dict, q)  # 供下一轮错误反馈
                        query_raw = cast(dict, q)
                        checked = verify(cast(dict, q))
                        issues = completeness_issues(checked)
                        if issues is not None:   # —— B：生成后完整度校验（硬门）——
                            issues_text = issues.get('text', '问题条件不足，请补充查询条件')
                            await auto_feedback.record(
                                category='guard',
                                trigger_point='query_clarify_block',
                                reason=f'重试查询缺年份，口径不明：{json.dumps(checked, ensure_ascii=False)}',
                                layer='内层防护罩-完整度校验',
                                upstream='query_gen 重试修正仍未按"年份缺省取 2026"规则生成条件',
                                fix_hint='核查重试提示词与缺省年份规则；若高频可把 year 缺省下沉到守卫规范化',
                                question=question, query_raw=query_raw)
                            tracker.done(2, f'查询缺少必要条件，已追问澄清：{issues_text}')
                            yield _step_ev(tracker, 2)
                            form = {'text': issues_text, 'question': question, 'fields': issues['fields']}
                            resp = await _build_clarify_resp(session, tracker, model_conf, t0, tokens, form)
                            await _save_messages(session, question, resp, user_name)
                            saved = True
                            yield {'type': 'done', 'data': resp}
                            return
                        tracker.done(2, f'守卫校验通过：模型/字段/操作符均在白名单内，强制行数上限 {MAX_LIMIT}')
                        yield _step_ev(tracker, 2)
                        _log_step(tracker, 2)
                        rows, truncated = await query_executor.run(checked)
                        used_query = checked
                        retries = attempt + 1
                        break
                    except (GuardError, ShellError, BusinessError, RuntimeError, TimeoutError) as e:
                        last_err = str(e)
                        if isinstance(e, ShellError):
                            # 结构层拦截被反复触发 → 自动反馈（允许被拦，禁止静默）
                            await auto_feedback.record(
                                category='shell',
                                trigger_point='query_gen_shell_validation',
                                reason=last_err,
                                layer='外置JSONSchema壳-结构校验拦截',
                                upstream='LLM 产出结构越界，未达 query_guard',
                                fix_hint='按 reason 定位结构偏差并回传重试；必要时评估修正 OUTPUT_SCHEMAS 后回放验证',
                                question=question, query_raw=base_bad)
                        if attempt == q_params['retries'] - 1:
                            raise BusinessError(f'查询生成失败：{last_err}', 422)
                        tracker.fail(2, f'第{attempt + 1}次串行回传校验/执行未通过：{last_err}，已回传 LLM 重试')
                        yield _step_ev(tracker, 2)
                        _log_step(tracker, 2)
                        log('info', 'ask_retry', attempt=attempt, error=last_err)
                        yield _step_running(2)

        assert rows is not None      # 执行阶段后必有结果行
        assert used_query is not None  # 必有执行模板
        yield _step_running(3)
        tracker.done(3, f'执行取数完成，返回 {len(rows)} 条{ "（已截断）" if truncated else "" }')
        yield _step_ev(tracker, 3)
        _log_step(tracker, 3)

        # 目标/完成率：应用层两次查询 + 内存 join（ReportOverall × GoalLedger），不落冗余列
        if used_query['model'] == 'ReportOverall' and any(w in question for w in ('目标', '完成率', '达成')):
            year_cond = {k: v for k, v in (used_query.get('condition') or {}).items() if k == 'year'}
            goals = await store.query('GoalLedger($condition:@c0) { unit, commercialGoal }', {'c0': year_cond})
            gmap = {g['unit']: g.get('commercialGoal', 0) for g in goals}
            cond = used_query.get('condition') or {}
            cond_unit = cond.get('unit')
            if isinstance(cond_unit, dict):
                cond_unit = cond_unit.get('$eq')
            for r in rows:
                goal = gmap.get(r.get('unit') or cond_unit)
                if goal:
                    r['commercialGoal'] = round(goal, 2)
                    r['完成率%'] = round((r.get('income') or 0) / goal * 100, 1)

        rows = _round_rows(rows)
        numeric_field = None
        if used_query['mode'] == 'aggregate':
            mk = measure_key(used_query['measures'][0])
            numeric_field = mk if rows and isinstance(rows[0].get(mk), (int, float)) else None
            display_fields = list(rows[0].keys()) if rows else []
        else:
            numeric_field = next(
                (f for f in QA_NUMERIC_FIELDS
                 if f in used_query['fields'] and rows and isinstance(rows[0].get(f), (int, float))),
                None)
            display_fields = used_query['fields']
        display_fields = [f for f in display_fields if f != '_id']

        stats = _build_stats(rows, numeric_field) if numeric_field else _build_stats(
            rows, display_fields[0] if display_fields else None)
        chart = _build_chart(question, used_query, rows)
        findings = _build_findings(stats, numeric_field, used_query['model'])
        raw_columns = list(rows[0].keys()) if rows else []
        columns = _zh_table_headers(used_query['model'], raw_columns)
        rows_2d = [[r.get(c, '') for c in raw_columns] for r in rows]

        # 结果块逐块推送（出完一块推一块）
        yield {'type': 'block', 'name': 'findings', 'data': findings}
        yield {'type': 'block', 'name': 'table', 'data': {'columns': columns, 'rows': rows_2d, 'count': len(rows)}}
        yield {'type': 'block', 'name': 'stats', 'data': stats}
        yield {'type': 'block', 'name': 'chart', 'data': chart}

        yield _step_running(4)
        sample = [{k: v for k, v in r.items() if k != '_id'}
                  for r in rows[:QA_CONCLUSION_ROWS]]
        conclusion, ret2 = await llm_client.invoke(
            'conclusion', {'question': question, 'query': used_query, 'rows': sample}, model_conf)
        tokens += ret2['total_tokens']
        log('info', 'llm_call', scenario='conclusion', elapsed_s=ret2.get('elapsed_s'),
            tokens=ret2.get('total_tokens'), cache_hit=ret2.get('cache_hit_tokens'),
            cache_miss=ret2.get('cache_miss_tokens'))
        tracker.done(4, f'基于真实结果行生成结论与 {QA_FOLLOW_UPS} 条追问建议')
        yield _step_ev(tracker, 4)
        _log_step(tracker, 4)

        assert isinstance(conclusion, dict)  # conclusion 场景必定返回字典
        text = conclusion.get('text', '')
        follow_ups = (conclusion.get('follow_ups') or [])[:QA_FOLLOW_UPS]
        yield {'type': 'block', 'name': 'text', 'data': text}
        yield {'type': 'block', 'name': 'follow_ups', 'data': follow_ups}

        # 完整校验后模板：聚合查询的 groupBy/measures 一并带上（日志完整展示 + 修复聚合缓存回放必失效）
        template = {k: used_query[k] for k in ('model', 'mode', 'condition', 'fields', 'sort', 'limit',
                                               'groupBy', 'measures') if k in used_query}
        resp = {
            'session_id': session['_id'],
            'steps': tracker.out(),
            'findings': findings,
            'columns': columns,
            'rows': rows_2d,
            'stats': stats,
            'chart': chart,
            'text': text,
            'follow_ups': follow_ups,
            'query': template,
            'query_raw': query_raw,
            'query_source': query_source,
            'retries': retries,
            'truncated': truncated,
            'row_count': len(rows),
            'meta': {
                'elapsed_s': round(time.monotonic() - t0, 2),
                'tokens': tokens,
                'model': model_conf['name'],
                'modelName': model_conf.get('modelName', ''),
                'platform': model_conf['platform'],
                'request_id': get_request_id(),
            },
        }
        await _save_messages(session, question, resp, user_name)
        saved = True

        await query_cache.upsert(question, template, success=True)
        log('info', 'ask_done', total_ms=round((time.monotonic() - t0) * 1000), retries=retries,
            row_count=len(rows), query_source=query_source)
        yield {'type': 'done', 'data': resp}
    except BusinessError as e:
        if not saved:
            await _record_failure(session, question, tracker, str(e), time.monotonic() - t0,
                                  tokens, model_conf)
        yield {'type': 'error', 'message': str(e)}
    except Exception:  # noqa: BLE001  # 问数链路最外层兜底：必然结构化 error block
        if not saved:
            await _record_failure(session, question, tracker,
                                  traceback.format_exc(limit=10), time.monotonic() - t0,
                                  tokens, model_conf)
        yield {'type': 'error', 'message': '问数处理失败，请稍后重试'}


async def downvote(question: str) -> None:
    """差评 → 缓存降权（三原则③）"""
    await query_cache.upsert(question, {}, success=False)


async def _ensure_session(session_id: str | None, title: str) -> dict:
    if session_id:
        s = await store.query_one('QaSession($condition:@c0) { _id, title, msgCount }',
                                  {'c0': {'_id': session_id}})
        if not s:
            raise BusinessError('会话不存在', 404)
        return s
    return await store.insert('QaSession', {'title': (title or '新对话')[:QA_TITLE_MAX], 'userName': '管理员'})


async def _record_failure(session: dict | None, question: str, tracker: StepTracker,
                          error: str, elapsed_s: float, tokens: int,
                          model_conf: dict | None) -> None:
    """失败留痕：把问题与失败诊断写入会话，避免日志出现空会话无从排查"""
    if not session:
        return
    sid = session['_id']
    meta = {'elapsed_s': round(elapsed_s, 2), 'tokens': tokens}
    if model_conf:
        meta.update({'model': model_conf['name'], 'modelName': model_conf.get('modelName', ''),
                     'platform': model_conf['platform']})
    ai_meta = {'session_id': sid, 'steps': tracker.out(), 'error': error, 'meta': meta}
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'user', 'content': question})
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'ai', 'content': '', 'aiMeta': ai_meta})
    n = await store.count('QaMessage', {'sessionId': sid})
    await store.update('QaSession', {'_id': sid}, {'msgCount': n})


async def _save_messages(session: dict, question: str, resp: dict, user_name: str) -> None:
    sid = session['_id']
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'user', 'content': question})
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'ai',
                                     'content': resp['text'], 'aiMeta': resp})
    n = await store.count('QaMessage', {'sessionId': sid})
    await store.update('QaSession', {'_id': sid}, {'msgCount': n, 'userName': user_name})
