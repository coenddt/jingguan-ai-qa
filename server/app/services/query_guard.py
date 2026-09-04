"""AI 查询只读守卫（纯校验，无副作用）：模型/字段/操作符/聚合白名单 + 行数上限"""

from app.config import ALLOWED_MEASURES, ALLOWED_OPS, MAX_LIMIT, NUMERIC_TYPES
from app.models.registry import BUSINESS_MODELS, MODEL_TABLE


class GuardError(Exception):
    """守卫拒绝（路由层映射 403）"""


def _walk_condition(cond, fields: set, path: str = '') -> None:
    if not isinstance(cond, dict):
        raise GuardError(f'条件格式错误: {path}')
    for k, v in cond.items():
        if k.startswith('$'):
            if k not in ALLOWED_OPS:
                raise GuardError(f'条件操作符越界: {k}')
            continue
        if k not in fields:
            raise GuardError(f'未知字段: {k}')
        if isinstance(v, dict):
            for vk in v:
                if vk.startswith('$') and vk not in ALLOWED_OPS:
                    raise GuardError(f'条件操作符越界: {vk}')


def verify(query: dict) -> dict:
    """校验 LLM 产出的查询形态，通过返回规范化 query；任何越界抛 GuardError"""
    model = query.get('model')
    schema = MODEL_TABLE.get(model or '')
    if not schema or model not in BUSINESS_MODELS:
        raise GuardError(f'模型不在白名单: {model}')
    fields_def = schema['fields']
    field_names = set(fields_def)

    cond = query.get('condition') or {}
    _walk_condition(cond, field_names)

    fields = query.get('fields') or []
    unknown = [f for f in fields if f not in field_names]
    if unknown:
        raise GuardError(f'未知字段: {unknown}')
    if not fields:
        fields = list(fields_def)

    limit = int(query.get('limit') or MAX_LIMIT)
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    checked = {
        'model': model,
        'mode': 'aggregate' if query.get('mode') == 'aggregate' else 'query',
        'condition': cond,
        'fields': fields,
        'limit': limit,
    }

    if checked['mode'] == 'aggregate':
        group_by = query.get('groupBy') or []
        bad_group = [g for g in group_by if g not in field_names]
        if not group_by or bad_group:
            raise GuardError(f'分组字段越界: {bad_group or "缺少groupBy"}')
        measures = query.get('measures') or []
        if not measures:
            raise GuardError('缺少聚合指标')
        norm_measures = []
        for m in measures:
            op = m.get('op')
            field = m.get('field')
            if op not in ALLOWED_MEASURES:
                raise GuardError(f'聚合算子越界: {op}')
            if op != 'count' and field not in field_names:
                raise GuardError(f'聚合字段越界: {field}')
            if op != 'count' and field and fields_def[field]['type'] not in NUMERIC_TYPES:
                raise GuardError(f'聚合目标非数值: {field}')
            norm_measures.append({'op': op, 'field': field})
        checked.update({'groupBy': group_by, 'measures': norm_measures})
        # 聚合模式排序键允许：分组字段 + 计算列 op_field（$project 后的字段）
        allowed_sort = set(group_by) | {measure_key(m) for m in norm_measures}
    else:
        allowed_sort = field_names

    sort = query.get('sort') or {}
    bad_sort = [k for k in sort if k not in allowed_sort]
    if bad_sort:
        raise GuardError(f'排序字段越界: {bad_sort}')
    checked['sort'] = sort
    checked['limit'] = limit

    return checked


def measure_key(m: dict) -> str:
    field = m.get('field') or 'all'
    return f"{m['op']}_{field}"
