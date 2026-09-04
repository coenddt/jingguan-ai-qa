"""问数编排：会话 →(缓存/LLM)查询 → 守卫 → 执行 → 统计/图表 → 结论 → 落库"""

import json
import time

from app.agent.prompt_builder import build_retry_prompt, build_system_prompt
from app.agent.step_tracker import StepTracker
from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import llm_client, query_cache, query_executor
from app.services.query_guard import GuardError, measure_key, verify

_NUMERIC = {'int', 'long', 'float', 'double'}
_TIME_DIMS = {'year', 'month', 'quarter', 'signDate'}


async def _active_model() -> dict:
    m = await store.query_one('AiModel($condition:@c0) { _id, name, baseUrl, apiKey, modelName }',
                              {'c0': {'enabled': True}})
    if not m or not m.get('apiKey'):
        raise BusinessError('无启用的 AI 模型，请先在模型配置中启用', 400)
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
    if any(w in question for w in ('占比', '构成', '分布比例', '结构')) and len(rows) <= 8:
        ctype = 'pie'
    elif dim in _TIME_DIMS:
        ctype = 'line'
    else:
        ctype = 'bar'
    unit = '万元' if ('Amt' in mk or 'income' in mk or 'Goal' in mk) else ''
    return {'type': ctype, 'title': title, 'unit': unit, 'series': series, 'x': x,
            'legend': [mk] if ctype != 'pie' else x}


def _build_findings(stats: dict, numeric_field: str | None) -> list[str]:
    if not stats.get('count'):
        return ['未查询到符合条件的数据']
    out = [f"共 {stats['count']} 条记录，均值 {stats['avg']}"]
    if numeric_field:
        out.append(f"{numeric_field} 最大值 {stats['max']}（{stats['max_of']}），最小值 {stats['min']}（{stats['min_of']}）")
    return out


async def ask(question: str, session_id: str | None, source_keys: list[str],
              user_name: str = '管理员') -> dict:
    t0 = time.monotonic()
    tracker = StepTracker()
    n_sources = len(source_keys) if source_keys else 8
    tracker.done(0, f'识别问题意图，在 {n_sources} 个已选数据源分组中确定目标模型')

    model_conf = await _active_model()
    llm_kw = {'base_url': model_conf['baseUrl'], 'api_key': model_conf['apiKey'],
              'model': model_conf['modelName']}

    rows: list[dict] | None = None
    truncated = False
    used_query: dict | None = None
    tokens = 0
    cache_hit = False

    ex = await query_cache.exact_hit(question)
    if ex:
        try:
            checked = verify(ex['template'])
            rows, truncated = await query_executor.run(checked)
            used_query = checked
            cache_hit = True
            tracker.done(1, f'命中精确问法缓存，复用模板：{json.dumps(checked, ensure_ascii=False)[:180]}')
        except GuardError:
            cache_hit = False  # 缓存校验不通过一律丢弃回退 LLM，绝不跳过守卫

    if rows is None:
        few = await query_cache.top_k_fuzzy(question)
        messages = [
            {'role': 'system', 'content': build_system_prompt(few)},
            {'role': 'user', 'content': question},
        ]
        q, ret1 = await llm_client.chat_json(messages, **llm_kw)
        tokens += ret1['total_tokens']
        tracker.done(1, f'LLM 生成查询：{json.dumps(q, ensure_ascii=False)[:180]}')

        last_err = ''
        for attempt in range(3):
            try:
                checked = verify(q)
                tracker.done(2, '守卫校验通过：模型/字段/操作符均在白名单内，强制行数上限 200')
                rows, truncated = await query_executor.run(checked)
                used_query = checked
                break
            except (GuardError, BusinessError, RuntimeError, TimeoutError) as e:
                last_err = str(e)
                if attempt == 2:
                    raise BusinessError(f'查询生成失败：{last_err}', 422)
                tracker.fail(2, f'第{attempt + 1}次校验/执行未通过：{last_err[:120]}，已回传 LLM 重试')
                q, ret = await llm_client.chat_json([
                    {'role': 'system', 'content': build_system_prompt()},
                    {'role': 'user', 'content': build_retry_prompt(question, q, last_err)},
                ], **llm_kw)
                tokens += ret['total_tokens']

    tracker.done(3, f'执行取数完成，返回 {len(rows)} 条{ "（已截断）" if truncated else "" }')

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
            (f for f in ('income', 'contractAmt', 'orderAmt', 'solutionIncome', 'yoy')
             if f in used_query['fields'] and rows and isinstance(rows[0].get(f), (int, float))),
            None)
        display_fields = used_query['fields']
    display_fields = [f for f in display_fields if f != '_id']

    stats = _build_stats(rows, numeric_field) if numeric_field else _build_stats(
        rows, display_fields[0] if display_fields else None)
    chart = _build_chart(question, used_query, rows)
    findings = _build_findings(stats, numeric_field)

    sample = rows[:20]
    conclusion_sys = (
        '你是经营数据分析助手。基于给定的真实查询结果行生成分析结论。'
        '只输出 JSON：{"text": "markdown 结论（2-4 句，引用真实数字）", "follow_ups": ["追问1", "追问2", "追问3"]}。'
        f'禁止编造结果中不存在的数字。'
    )
    conclusion, ret2 = await llm_client.chat_json([
        {'role': 'system', 'content': conclusion_sys},
        {'role': 'user', 'content': f'问题：{question}\n查询：{json.dumps(used_query, ensure_ascii=False)}\n'
                                    f'结果行（共{len(rows)}条）：{json.dumps(sample, ensure_ascii=False)}'},
    ], **llm_kw)
    tokens += ret2['total_tokens']
    tracker.done(4, '基于真实结果行生成结论与 3 条追问建议')

    columns = list(rows[0].keys()) if rows else []
    resp = {
        'session_id': '',
        'steps': tracker.out(),
        'findings': findings,
        'columns': columns,
        'rows': [[r.get(c, '') for c in columns] for r in rows],
        'stats': stats,
        'chart': chart,
        'text': conclusion.get('text', ''),
        'follow_ups': (conclusion.get('follow_ups') or [])[:3],
        'meta': {'elapsed_s': round(time.monotonic() - t0, 2), 'tokens': tokens},
    }

    session = await _ensure_session(session_id, question)
    resp['session_id'] = session['_id']
    await _save_messages(session, question, resp, user_name)

    template = {k: used_query[k] for k in ('model', 'mode', 'condition', 'fields', 'sort', 'limit')
                if k in used_query}
    await query_cache.upsert(question, template, success=True)
    return resp


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
    return await store.insert('QaSession', {'title': (title or '新对话')[:20], 'userName': '管理员'})


async def _save_messages(session: dict, question: str, resp: dict, user_name: str) -> None:
    sid = session['_id']
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'user', 'content': question})
    await store.insert('QaMessage', {'sessionId': sid, 'role': 'ai',
                                     'content': resp['text'], 'aiMeta': {**resp, 'session_id': sid}})
    n = await store.count('QaMessage', {'sessionId': sid})
    await store.update('QaSession', {'_id': sid}, {'msgCount': n, 'userName': user_name})
