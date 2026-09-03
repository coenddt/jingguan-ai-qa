"""
CRUD 操作

核心原则：
  - 写入时不补默认值（DB 存最少数据）
  - 读取时自动补默认值 + 执行简单计算列
  - lookup 计算列嵌入 aggregate 的 $addFields
  - asyncFn 计算列需显式请求
"""

import inspect
import math
import random
import string
import time

from pymongo import ReturnDocument

from .pipeline import build_pipeline, build_projection, flatten_object_fields, parse, parse_gql, tokenize
from .permission import (
    PermissionError,
    can_read_schema,
    can_write_schema,
    evaluate,
    filter_writable_data,
    get_context,
    get_readable_computes,
    get_readable_fields,
    get_readable_relations,
    merge_owner_condition,
)
from .schema import get as _get_schema, has as _has_schema
from .types import get_default

_db = None


def set_db(db):
    global _db
    _db = db


def _get_db():
    if _db is None:
        raise RuntimeError('MongoStore 未初始化，请先调用 init(db)')
    return _db


def _remove_undefined(obj):
    """剔除对象中的 None 值（原地修改），避免空值写入 DB"""
    for key in list(obj.keys()):
        if obj[key] is None:
            del obj[key]
    return obj


def _col(schema_name):
    s = _get_schema(schema_name)
    return _db[s['collection']]


# ─── 默认值 & 计算列（简单 CRUD 用，非递归） ──────────────


def _resolve_default(defn):
    """
    解析字段默认值。
    可变容器必须返回「新实例」，不能返回共享引用（避免跨文档串扰）。
    """
    if callable(defn):
        return defn()
    if isinstance(defn, list):
        return defn[:]
    if isinstance(defn, dict):
        return {**defn}
    return defn


def _fill_nested_defaults(obj, fields_def):
    if not isinstance(obj, dict):
        return
    for key, field in fields_def.items():
        if key not in obj or obj[key] is None:
            field_type = field if isinstance(field, str) else field.get('type')
            defn = field.get('default') if isinstance(field, dict) and field.get('default') is not None else get_default(field_type)
            if defn is not None:
                obj[key] = _resolve_default(defn)
        # 递归：object 内嵌 object
        if isinstance(field, dict) and field.get('type') == 'object' and field.get('fields') \
                and isinstance(obj.get(key), dict):
            _fill_nested_defaults(obj[key], field['fields'])


def apply_defaults_and_computes(doc, schema):
    """对单条记录应用字段默认值 + 简单计算列（仅根文档，不递归）"""
    if not doc:
        return doc
    result = {**doc}

    for key, field in schema['fields'].items():
        if key not in result or result[key] is None:
            field_type = field if isinstance(field, str) else field.get('type')
            defn = field.get('default') if isinstance(field, dict) and field.get('default') is not None else get_default(field_type)
            if defn is not None:
                result[key] = _resolve_default(defn)
        # 递归填充嵌套 object 子字段
        if isinstance(field, dict) and field.get('type') == 'object' and field.get('fields') \
                and isinstance(result.get(key), dict):
            _fill_nested_defaults(result[key], field['fields'])

    for key, comp in schema.get('computes', {}).items():
        if comp.get('fn'):
            result[key] = comp['fn'](result)

    return result


# ─── 默认值缓存 + 递归处理器（GQL 查询用） ────────────────

_defaults_cache = {}


def _ensure_cache(schema):
    if schema['name'] in _defaults_cache:
        return _defaults_cache[schema['name']]

    field_defaults = {}
    for key, field in schema['fields'].items():
        field_type = field if isinstance(field, str) else field.get('type')
        defn = field.get('default') if isinstance(field, dict) and field.get('default') is not None else get_default(field_type)
        if defn is not None:
            field_defaults[key] = defn

    compute_defaults = {}
    fn_list = []
    async_fn_list = []
    for key, comp in (schema.get('computes') or {}).items():
        if comp.get('type'):
            compute_defaults[key] = get_default(comp['type'])
        if comp.get('fn'):
            fn_list.append({'key': key, 'depends': comp.get('depends', []), 'fn': comp['fn']})
        if comp.get('asyncFn'):
            async_fn_list.append({'key': key, 'asyncFn': comp['asyncFn'], 'depends': comp.get('depends', [])})

    cache = {'field_defaults': field_defaults, 'compute_defaults': compute_defaults, 'fn_list': fn_list, 'async_fn_list': async_fn_list}
    _defaults_cache[schema['name']] = cache
    return cache


async def _run_async_fns(items, schema, ctx):
    """执行 asyncFn 计算列（批量），带权限裁剪"""
    if not items:
        return
    cache = _ensure_cache(schema)
    if not cache['async_fn_list']:
        return

    readonly_async_fns = cache['async_fn_list']
    if ctx:
        readonly_async_fns = []
        for entry in cache['async_fn_list']:
            comp = schema.get('computes', {}).get(entry['key'])
            if comp and comp.get('read'):
                if evaluate(ctx, comp['read']):
                    readonly_async_fns.append(entry)
            else:
                readonly_async_fns.append(entry)

    for entry in readonly_async_fns:
        result = entry['asyncFn'](items, ctx)
        if inspect.iscoroutine(result):
            await result


def _merge_depends_into_ast(ast, schema):
    """收集所有 asyncFn 计算列的 depends GQL 片段，合并注入到查询 AST 中"""
    cache = _ensure_cache(schema)
    if not cache['async_fn_list']:
        return {'relations': {}}

    # rel_deps: { rel_name → set(fields) }，空 set = 整条文档
    rel_deps = {}

    for entry in cache['async_fn_list']:
        for dep in entry['depends'] or []:
            trimmed = (dep or '').strip()
            if not trimmed or trimmed == '_id':
                continue
            if '{' in trimmed:
                parsed = parse(tokenize(trimmed))
                rel_name = parsed['model']
                if rel_name not in schema['relations']:
                    continue
                rel_deps.setdefault(rel_name, set())
                for f in parsed['fields']:
                    if f != '_id':
                        rel_deps[rel_name].add(f)
            else:
                if trimmed not in schema['relations']:
                    continue
                rel_deps.setdefault(trimmed, set())

    if not rel_deps:
        return {'relations': {}}

    # ── 合并到 AST ──
    if 'relations' not in ast:
        ast['relations'] = {}
    inject_info = {'relations': {}}

    for rel_name, dep_fields in rel_deps.items():
        existing = ast['relations'].get(rel_name)
        if existing:
            existing_fields = set(existing.get('fields') or [])
            added = []
            for f in dep_fields:
                if f not in existing_fields:
                    existing.setdefault('fields', []).append(f)
                    added.append(f)
            if added:
                inject_info['relations'][rel_name] = set(added)
        else:
            ast['relations'][rel_name] = {'fields': list(dep_fields), 'relations': {}, 'params': {}}
            inject_info['relations'][rel_name] = '__all__'

    return inject_info


def _strip_dep_injected(items, inject_info, schema):
    """从结果中裁剪依赖注入的字段（不返回客户端）"""
    if not inject_info or not inject_info['relations']:
        return
    for item in items:
        for rel_name, injected in inject_info['relations'].items():
            rel_val = item.get(rel_name)
            if injected == '__all__':
                item.pop(rel_name, None)
            elif isinstance(rel_val, list):
                for sub in rel_val:
                    if isinstance(sub, dict):
                        for f in injected:
                            sub.pop(f, None)
            elif isinstance(rel_val, dict):
                for f in injected:
                    rel_val.pop(f, None)


def process_node(doc, ast_node, schema, ctx):
    """
    递归处理单条文档：补默认值 → 跑 fn 计算列 → 补计算列默认值 → 递归下钻 → 裁剪

    时序严格：
      1. 补字段默认值（计算列依赖的字段必须先有值）
      2. 跑 fn 计算列
      3. 补计算列默认值
      4. 递归处理嵌套关系文档
      5. 裁剪到 GQL 请求字段
      6. 权限裁剪
    """
    if not doc:
        return

    cache = _ensure_cache(schema)

    # 展平 object 子字段花括号语法 → dot-notation
    flatten_object_fields(ast_node, schema)

    # ── 计算 needed fields（请求字段 + fn 依赖字段，去重） ──
    needed_arr = []
    seen = set()
    for f in ast_node['fields']:
        seen.add(f)
        needed_arr.append(f)
    for entry in cache['fn_list']:
        for dep in entry['depends']:
            if dep not in seen:
                seen.add(dep)
                needed_arr.append(dep)

    # 收集点号嵌套字段信息 { root → [subPath, ...] }
    dot_fields = {}
    for f in ast_node['fields']:
        if '.' in f:
            root, sub = f.split('.', 1)
            dot_fields.setdefault(root, []).append(sub)

    # ① 补默认值（含点号字段的根字段）
    for key in needed_arr:
        if key not in doc or doc[key] is None:
            defn = cache['field_defaults'].get(key)
            if defn is not None:
                doc[key] = _resolve_default(defn)
    for root in dot_fields:
        if root not in doc or doc[root] is None:
            defn = cache['field_defaults'].get(root)
            if defn is not None:
                doc[root] = _resolve_default(defn)

    # ①.5 递归填充嵌套 object 子字段（含点号精确子字段）
    for key in needed_arr:
        if '.' in key:
            root, sub_path = key.split('.', 1)
            field = schema['fields'].get(root)
            if isinstance(field, dict) and field.get('type') == 'object' and field.get('fields') \
                    and isinstance(doc.get(root), dict):
                sub_field_def = field['fields'].get(sub_path)
                if sub_field_def and (sub_path not in doc[root] or doc[root][sub_path] is None):
                    sub_type = sub_field_def if isinstance(sub_field_def, str) else sub_field_def.get('type')
                    defn = sub_field_def.get('default') if isinstance(sub_field_def, dict) and sub_field_def.get('default') is not None else get_default(sub_type)
                    if defn is not None:
                        doc[root][sub_path] = _resolve_default(defn)
        else:
            field = schema['fields'].get(key)
            if isinstance(field, dict) and field.get('type') == 'object' and field.get('fields') \
                    and isinstance(doc.get(key), dict):
                _fill_nested_defaults(doc[key], field['fields'])

    # ② 跑 fn 计算列
    for entry in cache['fn_list']:
        doc[entry['key']] = entry['fn'](doc)

    # ③ 补计算列默认值
    for entry in cache['fn_list']:
        key = entry['key']
        if key not in doc or doc[key] is None:
            defn = cache['compute_defaults'].get(key)
            if defn is not None:
                doc[key] = _resolve_default(defn)

    # ④ 递归下钻（跳过不可读的关系）
    rel_names = list(ast_node['relations'].keys())
    readable_relations = get_readable_relations(schema, ctx) if ctx else None
    for rel_name in rel_names:
        if readable_relations is not None and rel_name not in readable_relations:
            continue
        rel_ast = ast_node['relations'][rel_name]
        rel_def = schema['relations'].get(rel_name)
        if not rel_def:
            continue
        rel_schema = _get_schema(rel_def['model'])
        rel_val = doc.get(rel_name)
        if isinstance(rel_val, list):
            for rel_doc in rel_val:
                process_node(rel_doc, rel_ast, rel_schema, ctx)
        elif isinstance(rel_val, dict):
            process_node(rel_val, rel_ast, rel_schema, ctx)

    # ⑤ 裁剪 — 只保留 GQL 字段 + 关系名（_id 始终保留）
    keep = set(ast_node['fields'])
    for root in dot_fields:
        keep.add(root)
    for rel_name in rel_names:
        keep.add(rel_name)
    keep.add('_id')

    # ⑥ 权限裁剪 — 从 keep 中移除当前用户不可读的字段/计算列/关系
    if ctx:
        readable_fields = get_readable_fields(schema, ctx)
        readable_computes = get_readable_computes(schema, ctx)

        for key in ast_node['fields']:
            if key == '_id':
                continue
            if key in schema['fields'] and readable_fields is not None and key not in readable_fields:
                keep.discard(key)
            elif key in schema.get('computes', {}) and readable_computes is not None and key not in readable_computes:
                keep.discard(key)
        # 关系中不可读的也从 keep 中移除
        for rel_name in rel_names:
            if readable_relations is not None and rel_name not in readable_relations:
                keep.discard(rel_name)

        # ⑥.5 Owner-based 字段级权限 — 对每个字段单独传入 doc 做 creator 检查
        for key in ast_node['fields']:
            if key == '_id':
                continue
            if key not in keep:
                continue
            field = schema['fields'].get(key)
            if field and field.get('read') and evaluate(ctx, field['read'], doc) is False:
                keep.discard(key)
        # 计算列同理
        for key, comp in (schema.get('computes') or {}).items():
            if key not in keep:
                continue
            if comp and comp.get('read') and evaluate(ctx, comp['read'], doc) is False:
                keep.discard(key)
        # 关系同理
        for rel_name in rel_names:
            if rel_name not in keep:
                continue
            rel = schema['relations'].get(rel_name)
            if rel and rel.get('read') and evaluate(ctx, rel['read'], doc) is False:
                keep.discard(rel_name)

    for key in list(doc.keys()):
        if key not in keep:
            del doc[key]

    # 裁剪点号字段父对象中未请求的子字段
    for root, subs in dot_fields.items():
        obj = doc.get(root)
        if isinstance(obj, dict):
            sub_keep = set(subs)
            for sub_key in list(obj.keys()):
                if sub_key not in sub_keep:
                    del obj[sub_key]


# ─── GQL 查询 ──────────────────────────────────────────────


async def query(gql, params=None):
    """
    GQL 查询（返回数组）

    支持的 params 键（通过 GQL 的 @key 引用）:
      $condition / $sort / $skip / $limit / $pipeline
    使用 $pipeline 时，框架不追加 compute 层、不补默认值、不裁剪，完全由用户控制。
    """
    params = params if params is not None else {}
    ctx = get_context()
    ast = parse_gql(gql)
    schema = _get_schema(ast['model'])

    # Schema 级读权限检查
    if ctx and not can_read_schema(schema, ctx):
        raise PermissionError('无访问权限')

    # 所有者条件注入（非 admin 用户只看自己的数据）
    cond_ref = ast['params'].get('condition')
    if ctx and cond_ref:
        cond_key = cond_ref[1:]
        params[cond_key] = merge_owner_condition(schema, ctx, params.get(cond_key))

    # $pipeline 模式 → 用户全权控制
    pipeline_ref = ast['params'].get('pipeline')
    has_pipeline = bool(pipeline_ref) and params.get(pipeline_ref[1:]) is not None

    # 注入 asyncFn 计算列的关系依赖
    if has_pipeline:
        inject_info = {'relations': {}}
    else:
        inject_info = _merge_depends_into_ast(ast, schema)
    has_inject = len(inject_info['relations']) > 0

    pipeline = build_pipeline(ast, params)

    # 由 GQL 根字段 + fn 计算列 depends 驱动的投影，避免拉取整文档
    projection = None if has_pipeline else build_projection(ast, schema, ctx)

    coll = _col(ast['model'])

    # 纯 $match 无关联 → 用 find 性能更好
    if not has_pipeline and len(pipeline) == 1 and '$match' in pipeline[0]:
        cursor = coll.find(pipeline[0]['$match'], projection) if projection else coll.find(pipeline[0]['$match'])
        items = await cursor.to_list(length=None)
        for item in items:
            process_node(item, ast, schema, ctx)
        await _run_async_fns(items, schema, ctx)
        if has_inject:
            _strip_dep_injected(items, inject_info, schema)
        return items

    # ── 自动两阶段优化（根级别） ──
    # 当 pipeline 同时有 $lookup 和 $skip/$limit 时，先用轻量 pipeline 取分页 ID，
    # 再对少量 ID 做关联查询，避免全量 join 后被 $skip 丢弃。
    first_lookup_idx = next((i for i, st in enumerate(pipeline) if '$lookup' in st), -1)
    has_skip_limit = (not has_pipeline) and any('$skip' in st or '$limit' in st for st in pipeline)

    if first_lookup_idx >= 0 and has_skip_limit:
        # 检查 sort 是否引用关联表字段（如 'bidders.amount'）
        sort_stage = next((st for st in pipeline if '$sort' in st), None)
        sorts_by_relation = bool(sort_stage) and any('.' in k for k in sort_stage['$sort'])

        if not sorts_by_relation:
            # 阶段一：仅取分页后的 ID（无 $lookup，利用索引）
            id_pipeline = list(pipeline[:first_lookup_idx])
            pl_sort = next((st for st in pipeline if '$sort' in st), None)
            pl_skip = next((st for st in pipeline if '$skip' in st), None)
            pl_limit = next((st for st in pipeline if '$limit' in st), None)
            if pl_sort:
                id_pipeline.append(pl_sort)
            if pl_skip:
                id_pipeline.append(pl_skip)
            if pl_limit:
                id_pipeline.append(pl_limit)
            id_pipeline.append({'$project': {'_id': 1}})

            id_docs = await (await coll.aggregate(id_pipeline)).to_list(length=None)
            if not id_docs:
                return []

            ids = [d['_id'] for d in id_docs]

            # 阶段二：仅对分页后的少量 ID 执行关联查询
            full_pipeline = [
                st for st in pipeline[first_lookup_idx:]
                if '$sort' not in st and '$skip' not in st and '$limit' not in st
            ]
            full_pipeline.insert(0, {'$match': {'_id': {'$in': ids}}})

            if projection:
                full_pipeline.append({'$project': projection})
            items = await (await coll.aggregate(full_pipeline)).to_list(length=None)

            # $in 查询不保证返回顺序，按阶段一 ids 的顺序重排，恢复正确排序
            if pl_sort and len(ids) > 1:
                id_order = {str(_id): i for i, _id in enumerate(ids)}
                items.sort(key=lambda d: id_order.get(str(d['_id']), len(id_order)))

            for item in items:
                process_node(item, ast, schema, ctx)
            await _run_async_fns(items, schema, ctx)
            if has_inject:
                _strip_dep_injected(items, inject_info, schema)
            return items

    # ── 标准单阶段聚合 ──
    if not has_pipeline and projection:
        pipeline.append({'$project': projection})
    items = await (await coll.aggregate(pipeline)).to_list(length=None)

    # $pipeline 模式：直接返回原始结果
    if has_pipeline:
        return items

    # 标准 GQL 模式：递归处理每一条
    for item in items:
        process_node(item, ast, schema, ctx)
    await _run_async_fns(items, schema, ctx)
    if has_inject:
        _strip_dep_injected(items, inject_info, schema)
    return items


async def query_one(gql, params=None):
    """GQL 查询（返回单条）"""
    items = await query(gql, params)
    return items[0] if items else None


async def query_with_count(gql, params=None):
    """
    GQL 查询（返回 items + total + 分页元数据）

    支持两种分页参数方式：
      1. page/pageSize（推荐）— 自动计算 skip/limit，page 默认 0，pageSize 默认 50
      2. 传统 $skip/$limit — 从 GQL 参数推导 page/pageSize
    pageSize 上限 5000，防止拖库。
    """
    params = params if params is not None else {}
    ast = parse_gql(gql)
    schema = _get_schema(ast['model'])
    coll = _col(ast['model'])

    # ── 分页参数解析 ──
    if 'page' in params or 'pageSize' in params:
        page = max(0, math.floor(Number(params['page']))) if params.get('page') is not None else 0
        page_size = Number(params['pageSize']) if params.get('pageSize') is not None else 50
    else:
        skip_ref = ast['params'].get('skip')
        limit_ref = ast['params'].get('limit')
        skip_val = params.get(skip_ref[1:]) if skip_ref else None
        limit_val = params.get(limit_ref[1:]) if limit_ref else None
        page = math.floor(Number(skip_val) / Number(limit_val)) if (skip_val is not None and limit_val) else 0
        page_size = Number(limit_val) if limit_val is not None else 50

    # 防止拖库：pageSize 上限 5000
    page_size = min(page_size, 5000)

    # 确保 GQL 实际使用上述分页值
    if ast['params'].get('skip'):
        params[ast['params']['skip'][1:]] = page * page_size
    if ast['params'].get('limit'):
        params[ast['params']['limit'][1:]] = page_size

    items = await query(gql, params)

    # ── 统计 total（忽略 skip/limit） ──
    count_filter = {}
    cond_ref = ast['params'].get('condition')
    if cond_ref:
        count_filter = params.get(cond_ref[1:]) or {}

    # 权限：total 也应反映所有者条件
    ctx = get_context()
    if ctx:
        count_filter = merge_owner_condition(schema, ctx, count_filter)

    total = await coll.count_documents(count_filter)
    has_more = (page + 1) * page_size < total

    return {'items': items, 'total': total, 'hasMore': has_more, 'page': page, 'pageSize': page_size}


def Number(val):
    """对齐 JS Number()：无法转换时返回 0（NaN→0 由调用处 || 兜底）"""
    try:
        return int(val)
    except (TypeError, ValueError):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0


# ─── 简单 CRUD ─────────────────────────────────────────────


def _generate_id(schema):
    """按 schema.idPrefix 生成唯一 ID（时间戳36进制 + 随机4位）"""
    ts = _to_base36(int(time.time() * 1000)).upper()
    rnd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4)).upper()
    return schema['idPrefix'] + ts + rnd


def _to_base36(n):
    digits = string.digits + string.ascii_lowercase
    if n == 0:
        return '0'
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return ''.join(reversed(out))


def _has_creator_permission(s):
    return 'creator' in (s.get('read') or []) or 'creator' in (s.get('write') or [])


async def insert(schema_name, data):
    """插入一条"""
    ctx = get_context()
    s = _get_schema(schema_name)

    # Schema 级写权限检查
    if not can_write_schema(s, ctx):
        raise PermissionError('无写入权限')

    # 字段级写权限过滤
    filtered = filter_writable_data(s, ctx, data) if ctx else data

    coll = _col(schema_name)
    doc = _remove_undefined({**filtered})

    # 自动生成 ID
    if not doc.get('_id') and s['idPrefix']:
        doc['_id'] = s['idPrefix'] + _to_base36(int(time.time() * 1000)).upper() + ''.join(
            random.choices(string.ascii_lowercase + string.digits, k=4)).upper()

    # 自动设置 createdBy（creator 权限场景）
    if _has_creator_permission(s) and not doc.get('createdBy') and ctx and ctx.get('userId'):
        doc['createdBy'] = ctx['userId']

    # 自动时间戳
    if s['timestamps']:
        now = int(time.time() * 1000)
        if not doc.get('createdAt'):
            doc['createdAt'] = now
        doc['updatedAt'] = now

    await coll.insert_one(doc)
    return apply_defaults_and_computes(doc, s)


async def insert_many(schema_name, docs):
    """批量插入（带权限检查，自动生成 _id 和时间戳）"""
    if not isinstance(docs, list) or not docs:
        return []

    ctx = get_context()
    s = _get_schema(schema_name)
    coll = _col(schema_name)

    if not can_write_schema(s, ctx):
        raise PermissionError('无写入权限')

    processed_docs = []
    for data in docs:
        filtered = filter_writable_data(s, ctx, data) if ctx else data
        doc = _remove_undefined({**filtered})

        if not doc.get('_id') and s['idPrefix']:
            doc['_id'] = _generate_id(s)

        if _has_creator_permission(s) and not doc.get('createdBy') and ctx and ctx.get('userId'):
            doc['createdBy'] = ctx['userId']

        if s['timestamps']:
            now = int(time.time() * 1000)
            if not doc.get('createdAt'):
                doc['createdAt'] = now
            doc['updatedAt'] = now

        processed_docs.append(doc)

    await coll.insert_many(processed_docs)
    return [apply_defaults_and_computes(doc, s) for doc in processed_docs]


async def update(schema_name, condition, data, options=None):
    """
    更新一条（支持原生操作符，不触发默认值）

    data 的 key 以 '$' 开头 → 原生 MongoDB 操作符（$set/$inc/$unset 等）直接透传。
    否则自动包装为 $set 模式。
    """
    options = options or {}
    ctx = get_context()
    s = _get_schema(schema_name)
    coll = _col(schema_name)

    # Schema 级写权限检查
    if ctx:
        if 'guest' in (ctx.get('roles') or []):
            raise PermissionError('无写入权限')
        if not can_write_schema(s, ctx):
            if s.get('write') and 'creator' in s['write'] and condition:
                existing = await coll.find_one(condition, {'_id': 1, 'createdBy': 1})
                if not existing or evaluate(ctx, s['write'], existing) is False:
                    raise PermissionError('无写入权限')
            else:
                raise PermissionError('无写入权限')

    has_raw_operators = bool(data) and any(k.startswith('$') for k in data)

    if has_raw_operators:
        # 原生操作符模式（透传 $inc/$unset/$addToSet 等）
        if ctx and data.get('$set') is not None:
            data['$set'] = _remove_undefined(filter_writable_data(s, ctx, data['$set']))
        if s['timestamps']:
            set_part = data.get('$set') or {}
            data['$set'] = {**set_part, 'updatedAt': int(time.time() * 1000)}
        result = await coll.find_one_and_update(
            condition, data,
            return_document=ReturnDocument.AFTER,
            **options,
        )
        return apply_defaults_and_computes(result, s) if result else None

    # $set 模式
    set_data = _remove_undefined(filter_writable_data(s, ctx, data) if ctx else {**data})
    set_data.pop('_id', None)

    if not set_data:
        err = ValueError('没有提供要更新的字段')
        err.code = 'NO_FIELDS_TO_UPDATE'
        raise err

    if s['timestamps']:
        set_data['updatedAt'] = int(time.time() * 1000)

    result = await coll.find_one_and_update(
        condition,
        {'$set': set_data},
        return_document=ReturnDocument.AFTER,
        **options,
    )
    return apply_defaults_and_computes(result, s) if result else None


async def update_many(schema_name, condition, data):
    """批量更新（支持原生操作符）"""
    ctx = get_context()
    s = _get_schema(schema_name)
    coll = _col(schema_name)

    # Schema 级写权限检查
    if ctx:
        if 'guest' in (ctx.get('roles') or []):
            raise PermissionError('无批量写入权限')
        if not can_write_schema(s, ctx):
            raise PermissionError('无批量写入权限')

    has_raw_operators = bool(data) and any(k.startswith('$') for k in data)

    if has_raw_operators:
        if ctx and data.get('$set') is not None:
            data['$set'] = _remove_undefined(filter_writable_data(s, ctx, data['$set']))
        if s['timestamps']:
            set_part = data.get('$set') or {}
            data['$set'] = {**set_part, 'updatedAt': int(time.time() * 1000)}
    else:
        set_data = _remove_undefined(filter_writable_data(s, ctx, data) if ctx else {**data})
        set_data.pop('_id', None)
        if s['timestamps']:
            set_data['updatedAt'] = int(time.time() * 1000)
        data = {'$set': set_data}

    result = await coll.update_many(condition, data)
    return {'modifiedCount': result.modified_count}


async def remove(schema_name, condition):
    """删除 —— 原表数据先归档到对应 `_deleted` 附表（附 deletedAt），再物理删除原表数据"""
    ctx = get_context()
    s = _get_schema(schema_name)
    coll = _col(schema_name)

    if ctx:
        if 'guest' in (ctx.get('roles') or []):
            raise PermissionError('无删除权限')
        if not can_write_schema(s, ctx):
            if s.get('write') and 'creator' in s['write'] and condition:
                existing = await coll.find_one(condition, {'_id': 1, 'createdBy': 1})
                if not existing or evaluate(ctx, s['write'], existing) is False:
                    raise PermissionError('无删除权限')
            else:
                raise PermissionError('无删除权限')

    # 归档：完整拷贝到删除附表（保留原字段与时间戳，附 deletedAt）
    archived_count = 0
    archive_name = f"{schema_name}Deleted"
    if _has_schema(archive_name):
        archive_coll = _col(archive_name)
        docs = await coll.find(condition).to_list(length=None)
        if docs:
            now = int(time.time() * 1000)
            for d in docs:
                d['deletedAt'] = now
            await archive_coll.insert_many(docs)
            archived_count = len(docs)

    result = await coll.delete_many(condition)
    return {'deletedCount': result.deleted_count, 'archivedCount': archived_count}


async def exists(schema_name, condition):
    """判断是否存在"""
    coll = _col(schema_name)
    doc = await coll.find_one(condition, {'_id': 1})
    return doc is not None


async def count(schema_name, filter=None):
    """统计符合条件的文档数量"""
    coll = _col(schema_name)
    return await coll.count_documents(filter or {})


# ─── Mutation ──────────────────────────────────────────────


def _build_upsert_conditions(schema, data):
    """
    构建 upsert 条件组（$or 数组）

    规则：
      1. data._id 非空 → 加入 { _id: data._id }
      2. unique 索引的 keys 在 data 中均非空 → 整组作为一条条件加入 $or
    """
    conditions = []

    if data.get('_id') and str(data['_id']).strip():
        conditions.append({'_id': data['_id']})

    for idx in schema.get('indexes') or []:
        options = idx.get('options')
        if not options or not options.get('unique'):
            continue
        keys = list(idx['keys'].keys())
        all_present = all(
            data.get(k) is not None and not (isinstance(data.get(k), str) and not data[k].strip())
            for k in keys
        )
        if all_present:
            conditions.append({k: data[k] for k in keys})

    return conditions


async def _upsert_one(schema, data, foreign_field):
    """type: 'one' 子文档强制按 foreignKey upsert"""
    db = _get_db()
    coll = db[schema['collection']]

    set_data = _remove_undefined({**data})
    set_on_insert = {}

    # _id：有则 $setOnInsert（不 $set，避免修改已有文档的 _id）
    if set_data.get('_id') and str(set_data['_id']).strip():
        set_on_insert['_id'] = set_data['_id']
    elif schema['idPrefix']:
        set_on_insert['_id'] = _generate_id(schema)
    set_data.pop('_id', None)

    # 时间戳
    if schema['timestamps']:
        now = int(time.time() * 1000)
        set_data['updatedAt'] = now
        set_on_insert['createdAt'] = data.get('createdAt', now)
    set_data.pop('createdAt', None)

    update_doc = {'$set': set_data}
    if set_on_insert:
        update_doc['$setOnInsert'] = set_on_insert

    result = await coll.find_one_and_update(
        {foreign_field: data[foreign_field]},
        update_doc,
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result


async def _mutation_one(schema, data):
    """单条 mutation 核心逻辑"""
    ctx = get_context()

    if not can_write_schema(schema, ctx):
        raise PermissionError('无写入权限')

    # ── 1. 按 schema.relations 拆分 fieldData + relationData ──
    field_data = {}
    relation_data = {}
    rel_keys = set(schema['relations'].keys())

    for key, val in data.items():
        if key in rel_keys:
            if ctx:
                rel_def = schema['relations'][key]
                if rel_def.get('read') and not evaluate(ctx, rel_def['read']):
                    continue
            relation_data[key] = val
        else:
            field_data[key] = val

    filtered_field_data = filter_writable_data(schema, ctx, field_data) if ctx else field_data

    db = _get_db()
    coll = db[schema['collection']]

    # ── 2. 构建 upsert 条件 ──
    or_conditions = _build_upsert_conditions(schema, filtered_field_data)

    # ── 3. 写入 parent ──
    if or_conditions:
        # ── Upsert 路径 ──
        set_data = _remove_undefined({**filtered_field_data})
        set_on_insert = {}

        if set_data.get('_id') and str(set_data['_id']).strip():
            set_on_insert['_id'] = set_data['_id']
        elif schema['idPrefix']:
            set_on_insert['_id'] = _generate_id(schema)
        set_data.pop('_id', None)

        if schema['timestamps']:
            now = int(time.time() * 1000)
            set_data['updatedAt'] = now
            set_on_insert['createdAt'] = filtered_field_data.get('createdAt', now)
        set_data.pop('createdAt', None)

        # 自动设置 createdBy（upsert 新文档时）
        if _has_creator_permission(schema) and not set_on_insert.get('createdBy'):
            set_on_insert['createdBy'] = set_on_insert.get('_id')

        update_doc = {'$set': set_data}
        if set_on_insert:
            update_doc['$setOnInsert'] = set_on_insert

        parent_doc = await coll.find_one_and_update(
            {'$or': or_conditions},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    else:
        # ── Insert 路径（复用现有 insert 逻辑） ──
        parent_doc = await insert(schema['name'], filtered_field_data)

    # ── 4. 处理 relation 子文档 ──
    for rel_name, rel_val in relation_data.items():
        if rel_val is None:
            continue
        rel_def = schema['relations'].get(rel_name)
        if not rel_def:
            continue

        parent_id = parent_doc['_id']
        rel_schema = _get_schema(rel_def['model'])

        if rel_def['type'] == 'one':
            child_data = {**rel_val}
            child_data[rel_def['foreignField']] = parent_id
            await _upsert_one(rel_schema, child_data, rel_def['foreignField'])
        elif rel_def['type'] == 'many':
            arr = rel_val if isinstance(rel_val, list) else [rel_val]
            for child_item in arr:
                if child_item is None:
                    continue
                child_item[rel_def['foreignField']] = parent_id
                await _mutation_one(rel_schema, child_item)

    # ── 5. 补默认值后返回 ──
    return apply_defaults_and_computes(parent_doc, schema)


async def mutation(schema_name, data):
    """
    mutation — 智能持久化

    自动判断 upsert/insert，支持父子文档关联填充。
    """
    s = _get_schema(schema_name)
    is_array = isinstance(data, list)
    items = data if is_array else [data]

    if not items:
        return [] if is_array else None

    results = []
    for item in items:
        results.append(await _mutation_one(s, item))

    return results if is_array else results[0]


async def upsert(schema_name, condition, data, options=None):
    """
    upsert — 显式条件 upsert

    与 mutation 不同，upsert 需要调用方显式提供 match 条件，不处理父子关系。
    """
    options = options or {}
    ctx = get_context()
    s = _get_schema(schema_name)
    coll = _col(schema_name)

    if not can_write_schema(s, ctx):
        raise PermissionError('无写入权限')

    filtered_data = filter_writable_data(s, ctx, data) if ctx else data

    return_new = options.get('returnNew', True)
    set_data = _remove_undefined({**filtered_data})
    set_on_insert = {}

    # _id：从 data 移到 $setOnInsert（不 $set，避免修改已有文档的 _id）
    if set_data.get('_id') and str(set_data['_id']).strip():
        set_on_insert['_id'] = set_data['_id']
    elif s['idPrefix'] and not condition.get('_id'):
        set_on_insert['_id'] = _generate_id(s)
    set_data.pop('_id', None)

    # 时间戳
    if s['timestamps']:
        now = int(time.time() * 1000)
        set_data['updatedAt'] = now
        set_on_insert['createdAt'] = filtered_data.get('createdAt', now)
    set_data.pop('createdAt', None)

    # 自动设置 createdBy
    if _has_creator_permission(s) and not set_on_insert.get('createdBy'):
        set_on_insert['createdBy'] = set_on_insert.get('_id') or condition.get('_id')

    update_doc = {'$set': set_data}
    if set_on_insert:
        update_doc['$setOnInsert'] = set_on_insert

    result = await coll.find_one_and_update(
        condition,
        update_doc,
        upsert=True,
        return_document=ReturnDocument.AFTER if return_new else ReturnDocument.BEFORE,
    )

    return apply_defaults_and_computes(result, s) if result else None


async def aggregate(schema_name, pipeline):
    """对指定 schema 执行 MongoDB 原生聚合查询"""
    s = _get_schema(schema_name)
    coll = _get_db()[s['collection']]
    return await (await coll.aggregate(pipeline)).to_list(length=None)
