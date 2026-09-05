"""JSON Schema 壳（结构校验前置层，纯函数，无 IO）

在唯一 LLM 出口（llm_client.invoke）做浅层挂载：
- 入口 attach_schema()：把场景输出 json schema 固化为一条恒定 system，追加到消息末尾
- 出口 validate()：对 LLM 产出的结构化对象做结构硬校验，失败抛 ShellError

与 query_guard 分层：本壳只管"结构"（必填 / 类型 / 枚举 / 未定义键），
不管"语义"（模型/字段/操作符白名单、limit 上限）——语义权威仍是 query_guard。

前缀缓存注意：schema 消息追加在庞大 system 模板之后，各调用共享该公共前缀，
不破坏 query_candidate 的前缀预热 / 前缀缓存（配置文件勿改 schema 加进可变文案）。
"""

import json
from typing import Any


class ShellError(Exception):
    """结构校验拒绝（结构层守卫）；路由层/调用方按需捕获并自动反馈"""


# 场景输出 schema（仅结构约束）。key = scenario_id；值 = 极简 JSON Schema 子集。
# 注意：变更 schema 会影响恒定前缀的缓存重建成本，需评估后再改。
OUTPUT_SCHEMAS: dict[str, dict] = {
    'query_gen': {
        'type': 'object',
        'required': ['mode', 'model'],
        'properties': {
            'mode': {'type': 'string', 'enum': ['query', 'aggregate']},
            'model': {'type': 'string'},
            'condition': {'type': 'object'},
            'fields': {'type': 'array', 'items': {'type': 'string'}},
            'sort': {'type': 'object'},
            'limit': {'type': 'integer'},
            'groupBy': {'type': 'array', 'items': {'type': 'string'}},
            'measures': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'required': ['op', 'field'],
                    'properties': {
                        'op': {'type': 'string'},
                        'field': {'type': 'string'},
                    },
                    'additionalProperties': False,
                },
            },
        },
        'additionalProperties': False,
    },
}

# 模块加载期把 schema 固化为恒定文本，保证前缀缓存稳定
_SCHEMA_MESSAGES: dict[str, str] = {
    sid: json.dumps(schema, ensure_ascii=False) for sid, schema in OUTPUT_SCHEMAS.items()
}

# JSON Schema 子集 → Python 类型
_TYPE_MAP = {'object': dict, 'array': list, 'string': str, 'integer': int}


def attach_schema(messages: list[dict], scenario_id: str) -> list[dict]:
    """入口挂载：有注册 schema 则追加一条恒定 system；无则原样返回（浅层挂载，不进 user 文案）"""
    text = _SCHEMA_MESSAGES.get(scenario_id)
    if text is None:
        return messages
    return [*messages, {'role': 'system', 'content': text}]


def _fail(path: str, reason: str) -> None:
    raise ShellError(f'查询结构校验失败 @ {path or "root"}：{reason}')


def _check(value: Any, spec: dict, path: str) -> None:
    """按 spec 递归校验单节点结构；任何不符抛 ShellError（结构层，非语义）"""
    spec_type = spec.get('type')
    want = _TYPE_MAP.get(spec_type if isinstance(spec_type, str) else '')
    enum = spec.get('enum')

    if want is not None:
        # integer 排除 bool（Python 中 bool 是 int 子类，需单独排除）
        if not isinstance(value, want) or (spec.get('type') == 'integer' and isinstance(value, bool)):
            _fail(path, f'应为 {spec.get("type")}，实为 {type(value).__name__}')
    if enum is not None and value not in enum:
        _fail(path, f'不在枚举内: {value!r}，可选 {enum}')

    if spec.get('type') == 'object':
        props = spec.get('properties') or {}
        required = spec.get('required') or []
        if spec.get('additionalProperties') is False:
            unknown = [k for k in value if k not in props]
            if unknown:
                _fail(path, f'含未定义键: {unknown}（仅允许 {",".join(props)}）')
        for k in required:
            if k not in value or value[k] is None:
                _fail(f'{path}.{k}', '缺失必填字段')
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f'{path}.{k}')
    elif spec.get('type') == 'array':
        items = spec.get('items') or {}
        for i, item in enumerate(value):
            _check(item, items, f'{path}[{i}]')


def validate(parsed: Any, scenario_id: str) -> Any:
    """出口硬校验：未注册场景直通；注册场景递归结构校验，失败抛 ShellError（允许被拦、禁止静默）"""
    schema = OUTPUT_SCHEMAS.get(scenario_id)
    if schema is None:
        return parsed
    if not isinstance(parsed, dict):
        raise ShellError(f'查询结构校验失败：应为 JSON 对象，实为 {type(parsed).__name__}')
    _check(parsed, schema, 'query')
    return parsed