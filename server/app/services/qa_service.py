"""问数编排：会话 →(缓存/LLM)查询 → 守卫 → 执行 → 统计/图表 → 结论 → 落库

流式编排 ask_stream：以 SSE 事件逐步产出真实中间产物——
session（会话就绪）→ steps（步骤清单）→ step（单步 running/done/fail）→
block（findings/table/stats/chart/text/follow_ups 逐块）→ done（最终完整结果，与落库 aiMeta 一致）→ 异常统一转 error 事件。
"""

import json
import time

from app.agent.prompts import scenario_params
from app.agent.step_tracker import StepTracker
from app.config import (
    MAX_LIMIT, QA_CHART, QA_CONCLUSION_ROWS, QA_FOLLOW_UPS,
    QA_NUMERIC_FIELDS, QA_SOURCES, QA_TIME_DIMS, QA_TITLE_MAX,
)
from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import llm_client, query_cache, query_executor
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
        title = f'{mk}分布'
    else:
        numeric = [f for f in q['fields'] if isinstance(rows[0].get(f), (int, float))]
        if not numeric:
            return None
        dim = next((f for f in q['fields'] if isinstance(rows[0].get(f), str) and f not in ('signDate',)), None)
        mk = numeric[0]
        x = [str(r.get(dim, ''))[:8] if dim else str(i + 1) for i, r in enumerate(rows)]
        series = [round(float(r.get(mk) or 0), 2) for r in rows]
        title = f'{mk}分布'
    if any(w in question for w in QA_CHART['pie_keywords']) and len(rows) <= QA_CHART['pie_max_rows']:
        ctype = 'pie'
    elif dim in QA_TIME_DIMS:
        ctype = 'line'
    else:
        ctype = 'bar'
    unit = QA_CHART['amount_unit'] if any(m in mk for m in QA_CHART['amount_markers']) else ''
    return {'type': ctype, 'title': title, 'unit': unit, 'series': series, 'x': x,
            'legend': [mk] if ctype != 'pie' else x}


def _build_findings(stats: dict, numeric_field: str | None) -> list[str]:
    if not stats.get('count'):
        return ['未查询到符合条件的数据']
    out = [f"共 {stats['count']} 条记录，均值 {stats['avg']}"]
    if numeric_field:
        out.append(f"{numeric_field} 最大值 {stats['max']}（{stats['max_of']}），最小值 {stats['min']}（{stats['min_of']}）")
    return out


def _step_ev(tracker: StepTracker, idx: int) -> dict:
    """单步完成/失败事件（done=True→done；有 desc 未 done→fail）"""
    it = tracker.items[idx]
    status = 'done' if it['done'] else 'fail'
    return {'type': 'step', 'index': idx, 'title': it['title'], 'desc': it['desc'], 'status': status}


def _step_running(idx: int) -> dict:
    return {'type': 'step', 'index': idx, 'status': 'running'}


async def ask_stream(question: str, session_id: str | None, source_keys: list[str],
                     user_name: str = '管理员'):
    """流式问数编排：逐步 yield SSE 事件；逻辑与非流式版一致，异常统一转 error 事件"""
    t0 = time.monotonic()
    tracker = StepTracker()
    n_sources = len(source_keys) if source_keys else sum(len(g['items']) for g in QA_SOURCES)
    try:
        # 会话先行：前端尽早挂载消息流；失败（如无启用模型）不会遗留空会话
        session = await _ensure_session(session_id, question)
        yield {'type': 'session', 'data': {'session_id': session['_id']}}

        yield {'type': 'steps', 'data': [{'title': t} for t in tracker.STEPS]}
        tracker.done(0, f'识别问题意图，在 {n_sources} 个已选数据源分组中确定目标模型')
        yield _step_ev(tracker, 0)

        model_conf = await _active_model()
        q_params = scenario_params('query_gen')

        rows: list[dict] | None = None
        truncated = False
        used_query: dict | None = None
        tokens = 0

        yield _step_running(1)
        ex = await query_cache.exact_hit(question)
        if ex:
            try:
                checked = verify(ex['template'])
                rows, truncated = await query_executor.run(checked)
                used_query = checked
                tracker.done(1, f'命中精确问法缓存，复用模板：{json.dumps(checked, ensure_ascii=False)[:180]}')
                yield _step_ev(tracker, 1)
            except GuardError:
                pass  # 缓存校验不通过一律丢弃回退 LLM，绝不跳过守卫

        if rows is None:
            few = await query_cache.top_k_fuzzy(question)
            q, ret1 = await llm_client.invoke('query_gen', {'question': question, 'few_shots': few}, model_conf)
            tokens += ret1['total_tokens']
            tracker.done(1, f'LLM 生成查询：{json.dumps(q, ensure_ascii=False)[:180]}')
            yield _step_ev(tracker, 1)

            yield _step_running(2)
            for attempt in range(q_params['retries']):
                try:
                    checked = verify(q)
                    tracker.done(2, f'守卫校验通过：模型/字段/操作符均在白名单内，强制行数上限 {MAX_LIMIT}')
                    yield _step_ev(tracker, 2)
                    rows, truncated = await query_executor.run(checked)
                    used_query = checked
                    break
                except (GuardError, BusinessError, RuntimeError, TimeoutError) as e:
                    last_err = str(e)
                    if attempt == q_params['retries'] - 1:
                        raise BusinessError(f'查询生成失败：{last_err}', 422)
                    tracker.fail(2, f'第{attempt + 1}次校验/执行未通过：{last_err[:120]}，已回传 LLM 重试')
                    yield _step_ev(tracker, 2)
                    yield _step_running(2)
                    q, ret = await llm_client.invoke(
                        'query_gen', {'question': question, 'bad_query': q, 'error': last_err}, model_conf)
                    tokens += ret['total_tokens']

        yield _step_running(3)
        tracker.done(3, f'执行取数完成，返回 {len(rows)} 条{ "（已截断）" if truncated else "" }')
        yield _step_ev(tracker, 3)

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
        findings = _build_findings(stats, numeric_field)
        columns = list(rows[0].keys()) if rows else []
        rows_2d = [[r.get(c, '') for c in columns] for r in rows]

        # 结果块逐块推送（出完一块推一块）
        yield {'type': 'block', 'name': 'findings', 'data': findings}
        yield {'type': 'block', 'name': 'table', 'data': {'columns': columns, 'rows': rows_2d, 'count': len(rows)}}
        yield {'type': 'block', 'name': 'stats', 'data': stats}
        yield {'type': 'block', 'name': 'chart', 'data': chart}

        yield _step_running(4)
        sample = rows[:QA_CONCLUSION_ROWS]
        conclusion, ret2 = await llm_client.invoke(
            'conclusion', {'question': question, 'query': used_query, 'rows': sample}, model_conf)
        tokens += ret2['total_tokens']
        tracker.done(4, f'基于真实结果行生成结论与 {QA_FOLLOW_UPS} 条追问建议')
        yield _step_ev(tracker, 4)

        text = conclusion.get('text', '')
        follow_ups = (conclusion.get('follow_ups') or [])[:QA_FOLLOW_UPS]
        yield {'type': 'block', 'name': 'text', 'data': text}
        yield {'type': 'block', 'name': 'follow_ups', 'data': follow_ups}

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
            'meta': {'elapsed_s': round(time.monotonic() - t0, 2), 'tokens': tokens},
        }
        await _save_messages(session, question, resp, user_name)

        template = {k: used_query[k] for k in ('model', 'mode', 'condition', 'fields', 'sort', 'limit')
                    if k in used_query}
        await query_cache.upsert(question, template, success=True)
        yield {'type': 'done', 'data': resp}
    except BusinessError as e:
        yield {'type': 'error', 'message': str(e)}
    except Exception:
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


async def _save_messages(session: dict, question: str, resp: dict, user_name: str) -> None:
    sid = session['_id']
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'user', 'content': question})
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'ai',
                                     'content': resp['text'], 'aiMeta': resp})
    n = await store.count('QaMessage', {'sessionId': sid})
    await store.update('QaSession', {'_id': sid}, {'msgCount': n, 'userName': user_name})
