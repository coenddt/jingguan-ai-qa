"""AI 查询只读守卫（纯校验，无副作用）：模型/字段/操作符/聚合白名单 + 行数上限"""

from app.config import (
    ALLOWED_MEASURES,
    ALLOWED_OPS,
    DENIED_OPS,
    MAX_LIMIT,
    NUMERIC_TYPES,
)
from app.models.registry import BUSINESS_MODELS, MODEL_TABLE


class GuardError(Exception):
    """守卫拒绝（路由层映射 403）"""


def _reject_op(k: str, path: str) -> None:
    """拒绝非法操作符：危险/扩展操作符给明确信息，其余不在白名单一律 403"""
    if k in DENIED_OPS:
        raise GuardError(f'条件操作符被禁用: {k}' + (f' @ {path}' if path else ''))
    if k not in ALLOWED_OPS:
        raise GuardError(f'条件操作符越界: {k}' + (f' @ {path}' if path else ''))


def _check_key(k, fields: set, path: str) -> None:
    """校验单节点键：$ 前缀走操作符白名单，普通键走字段白名单"""
    if not isinstance(k, str):
        raise GuardError(f'条件键类型错误: {k!r}')
    if k.startswith('$'):
        _reject_op(k, path)
    elif k not in fields:
        raise GuardError(f'未知字段: {k}' + (f' @ {path}' if path else ''))


def _walk_condition(cond, fields: set, path: str = '') -> None:
    """全递归校验条件树：任意深度节点，$ 键限 ALLOWED_OPS 白名单、普通键限 schema 字段白名单。

    默认拒绝——所有命中危险/未知操作符（$where/$lookup/$unionWith/$expr/$function 等）
    与未知字段的深层写法都会被拦下，杜绝藏在嵌套值里的托管直通。
    """
    if not isinstance(cond, dict):
        raise GuardError(f'条件格式错误: {path or "root"}')
    for k, v in cond.items():
        _check_key(k, fields, path)
        _descend_value(v, fields, f'{path}.{k}')


def _descend_value(v, fields: set, path: str) -> None:
    """递归下沉到键值：字典 / 字典数组（覆盖操作符值里再藏操作符的嵌套写法）"""
    if isinstance(v, dict):
        _walk_condition(v, fields, path)
    elif isinstance(v, list):
        for i, item in enumerate(v):
            if isinstance(item, dict):
                _walk_condition(item, fields, f'{path}[{i}]')


def _load_model(query: dict) -> tuple:
    """解析并校验模型白名单；返回 (model, fields_def, 字段名集合)"""
    model = query.get('model')
    schema = MODEL_TABLE.get(model or '')
    if not schema or model not in BUSINESS_MODELS:
        raise GuardError(f'模型不在白名单: {model}')
    fields_def = schema['fields']
    return model, fields_def, set(fields_def)


def _resolve_fields(query: dict, field_names: set) -> list:
    """校验请求字段 ∈ 白名单；未指定时默认取全字段"""
    fields = query.get('fields') or []
    unknown = [f for f in fields if f not in field_names]
    if unknown:
        raise GuardError(f'未知字段: {unknown}')
    return fields or list(field_names)


def _clamp_limit(query: dict) -> int:
    """逐行数上限：缺省取 MAX_LIMIT，超限截断（宁可截断不可裸放行）"""
    return min(int(query.get('limit') or MAX_LIMIT), MAX_LIMIT)


def _sort_checked(sort: dict, allowed_sort) -> dict:
    """校验排序键 ∈ 允许集（普通模式=字段；聚合=分组+聚合键）"""
    bad_sort = [k for k in sort if k not in allowed_sort]
    if bad_sort:
        raise GuardError(f'排序字段越界: {bad_sort}')
    return sort


def verify(query: dict) -> dict:
    """校验 LLM 产出的查询形态，通过返回规范化 query；任何越界抛 GuardError"""
    model, fields_def, field_names = _load_model(query)
    cond = query.get('condition') or {}
    _walk_condition(cond, field_names)

    fields = _resolve_fields(query, field_names)
    limit = _clamp_limit(query)
    mode = 'aggregate' if query.get('mode') == 'aggregate' else 'query'

    checked = {
        'model': model,
        'mode': mode,
        'condition': cond,
        'fields': fields,
        'limit': limit,
    }
    if mode == 'aggregate':
        group_by, norm_measures, allowed_sort = _verify_aggregate(query, fields_def, field_names)
        checked.update({'groupBy': group_by, 'measures': norm_measures})
    else:
        allowed_sort = field_names

    checked['sort'] = _sort_checked(query.get('sort') or {}, allowed_sort)
    return checked


def _group_by_checked(query: dict, field_names: set) -> list:
    """校验并返回聚合分组字段 ∈ 白名单"""
    group_by = query.get('groupBy') or []
    bad_group = [g for g in group_by if g not in field_names]
    if not group_by or bad_group:
        raise GuardError(f'分组字段越界: {bad_group or "缺少groupBy"}')
    return group_by


def _verify_aggregate(query: dict, fields_def: dict, field_names: set):
    """校验聚合查询：分组、指标白名单；返回 (group_by, 规范化指标, 排序键允许集)"""
    group_by = _group_by_checked(query, field_names)
    measures = query.get('measures') or []
    norm_measures = [_normalize_measure(m, fields_def, field_names) for m in measures]
    if not norm_measures:
        raise GuardError('缺少聚合指标')
    allowed_sort = set(group_by) | {measure_key(m) for m in norm_measures}
    return group_by, norm_measures, allowed_sort


def _normalize_measure(m: dict, fields_def: dict, field_names: set) -> dict:
    """规整单个聚合指标：算子/字段白名单 + 数值类型校验"""
    op = m.get('op')
    field = m.get('field')
    if op not in ALLOWED_MEASURES:
        raise GuardError(f'聚合算子越界: {op}')
    if op != 'count' and field not in field_names:
        raise GuardError(f'聚合字段越界: {field}')
    if op != 'count' and field and fields_def[field]['type'] not in NUMERIC_TYPES:
        raise GuardError(f'聚合目标非数值: {field}')
    return {'op': op, 'field': field}


def measure_key(m: dict) -> str:
    """聚合键命名：op_field（$project 后透出字段，供排序/图表引用）"""
    field = m.get('field') or 'all'
    return f"{m['op']}_{field}"
