"""受限查询执行：注入只读角色 → guard 校验 → GQL/受限聚合 → 行数上限 + 超时"""

import asyncio

from app.config import EXEC_TIMEOUT
from app.db.mongo_store import store
from app.models.registry import MODEL_TABLE
from app.services.query_guard import GuardError, measure_key, verify


def _group_doc(q: dict) -> dict:
    """构建 $group 文档（含聚合键命名 sum_字段/count_all）"""
    single = len(q['groupBy']) == 1
    group_id = {g: f'${g}' for g in q['groupBy']} if not single else f'${q["groupBy"][0]}'
    doc: dict = {'_id': group_id}
    for m in q['measures']:
        key = measure_key(m)
        doc[key] = {'$sum': 1} if m['op'] == 'count' else {f'${m["op"]}': f'${m["field"]}'}
    return doc


def _sort_stage(q: dict, group_doc: dict) -> dict | None:
    """排序：显式 sort 用之；否则按首个聚合键倒序（保证结果稳定可预判）"""
    if q.get('sort'):
        return {'$sort': q['sort']}
    first_key = next(iter([k for k in group_doc if k != '_id']), None)
    return {'$sort': {first_key: -1}} if first_key else None


def _project_stage(q: dict) -> dict:
    """$project：还原分组维度 + 聚合键透出，剔除 _id"""
    multi = len(q['groupBy']) > 1
    proj: dict = {g: f'$_id.{g}' if multi else '$_id' for g in q['groupBy']}
    for m in q['measures']:
        proj[measure_key(m)] = 1
    return proj


def _build_pipeline(q: dict) -> list[dict]:
    """受限聚合 pipeline（$match/$group/$sort/$limit/$project，经 guard 后组装）"""
    pl: list[dict] = []
    if q.get('condition'):
        pl.append({'$match': q['condition']})
    group_doc = _group_doc(q)
    pl.append({'$group': group_doc})
    sort_stage = _sort_stage(q, group_doc)
    if sort_stage:
        pl.append(sort_stage)
    pl.append({'$limit': q['limit']})
    pl.append({'$project': _project_stage(q)})
    return pl


async def run(q: dict) -> tuple[list[dict], bool]:
    """执行已校验查询 → (rows, truncated)；内部仅使用白名单受限形态，禁裸 pipeline 直通"""
    checked = verify(q)
    model = checked['model']
    if model not in MODEL_TABLE:
        raise GuardError(f'模型不在白名单: {model}')
    with store.scoped_roles(['query']):  # 只读角色注入（token-reset，嵌套安全）
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
    truncated = False
    if len(rows) > checked['limit']:
        rows = rows[:checked['limit']]
        truncated = True
    rows = [{k: v for k, v in r.items() if k != '_id'} for r in rows]
    return rows, truncated
