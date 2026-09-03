"""受限查询执行：注入只读角色 → guard 校验 → GQL/受限聚合 → 行数上限 + 超时"""

import asyncio

from app.db.mongo_store import store
from app.models.registry import MODEL_TABLE
from app.services.query_guard import GuardError, MAX_LIMIT, measure_key, verify

EXEC_TIMEOUT = 10


def _build_pipeline(q: dict) -> list[dict]:
    """受限聚合 pipeline（$match/$group/$sort/$limit/$project，经 guard 后组装）"""
    pl: list[dict] = []
    if q.get('condition'):
        pl.append({'$match': q['condition']})
    group_id = {g: f'${g}' for g in q['groupBy']} if len(q['groupBy']) > 1 else f'${q["groupBy"][0]}'
    group_doc: dict = {'_id': group_id}
    for m in q['measures']:
        key = measure_key(m)
        group_doc[key] = {'$sum': 1} if m['op'] == 'count' else {f'${m["op"]}': f'${m["field"]}'}
    pl.append({'$group': group_doc})
    if q.get('sort'):
        pl.append({'$sort': q['sort']})
    else:
        first_key = next(iter([k for k in group_doc if k != '_id']), None)
        if first_key:
            pl.append({'$sort': {first_key: -1}})
    pl.append({'$limit': q['limit']})
    project: dict = {g: f'$_id.{g}' if len(q['groupBy']) > 1 else '$_id' for g in q['groupBy']}
    for m in q['measures']:
        project[measure_key(m)] = 1
    pl.append({'$project': project})
    return pl


async def run(q: dict) -> tuple[list[dict], bool]:
    """执行已校验查询 → (rows, truncated)；内部仅使用白名单受限形态，禁裸 pipeline 直通"""
    checked = verify(q)
    model = checked['model']
    if model not in MODEL_TABLE:
        raise GuardError(f'模型不在白名单: {model}')
    store.set_context({'roles': ['query']})
    try:
        if checked['mode'] == 'query':
            fields = ', '.join(checked['fields'])
            gql = f'{model}($condition:@c0,$sort:@s0,$skip:@sk,$limit:@l) {{ {fields} }}'
            params = {
                'c0': checked['condition'], 's0': checked['sort'] or {'_id': -1},
                'sk': 0, 'l': checked['limit'] + 1,
            }
            rows = await asyncio.wait_for(store.query(gql, params), EXEC_TIMEOUT)
        else:
            pl = _build_pipeline(checked)
            rows = await asyncio.wait_for(store.aggregate(model, pl), EXEC_TIMEOUT)
    finally:
        store.set_context(None)
    truncated = False
    if len(rows) > checked['limit']:
        rows = rows[:checked['limit']]
        truncated = True
    rows = [{k: v for k, v in r.items() if k != '_id'} for r in rows]
    return rows, truncated
