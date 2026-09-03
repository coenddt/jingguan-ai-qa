---
name: "mongo-store-py"
description: "server-py/db/mongo_store（Python 版 MongoDB 数据层）使用规范：GQL 查询、schema 注册、CRUD/mutation、权限上下文。凡涉及 server-py 的 MongoDB 读写、schema 定义、数据查询/持久化，必须先调用本 skill 按规则使用。"
---

# mongo-store-py — Python 版 MongoDB 数据层使用规范

模块位置：`server-py/db/mongo_store/`（`__init__.py` / `schema.py` / `crud.py` / `pipeline.py` / `permission.py` / `types.py`）

```python
from db.mongo_store import init, store

await init(db)          # 传入 PyMongo async 的 db 实例，自动幂等建索引
items = await store.query("Model($condition:@c0) { field1, field2 }", {'c0': {...}})
```

## 核心理念（先记住这四条）

1. **纯 JSON schema 定义，零代码**——表结构即字典。
2. **读取时**自动补默认值 + 执行 fn 计算列。
3. **写入时只存用户数据**，不补默认值（DB 存最少数据）。
4. **GQL 树形查询 → 一次 $lookup 聚合**，不要自己写 $lookup 拼关联。

## 一、Schema 注册（在 server-py/schema/ 定义，db/store.py 统一注册）

```python
ARTWORK_SCHEMA = {
    'name': 'Artwork',              # 模型名（GQL 用）
    'collection': 'artworks',       # 集合名，缺省=name
    'idPrefix': 'ART',              # _id 前缀，自动生成 ART+时间戳36进制+随机4位（字符串，非 ObjectId）
    'timestamps': True,             # 默认 True，框架自动维护 createdAt/updatedAt（毫秒），禁手工改写
    'fields': {
        '_id': 'string',                                  # 简写
        'title': {'type': 'string', 'default': ''},
        'status': {'type': 'string', 'default': 'ingested', 'read': ..., 'write': ...},  # read/write 为角色白名单
        'tags': {'type': 'array', 'default': []},
        'images': {'type': 'object', 'default': {}, 'fields': {...}},  # 内嵌 object 可定义子字段
    },
    'relations': {
        # many：一对多；one：一对一（查询自动 $unwind）
        'bidders': {'model': 'BidRecord', 'type': 'many', 'localField': '_id', 'foreignField': 'itemId'},
    },
    'computes': {
        # fn：应用层同步计算，depends 声明依赖字段（投影优化依赖它，必须写全）
        'statusLabel': {'type': 'string', 'depends': ['status'], 'fn': lambda item: ...},
        # lookup：聚合层计算（表达式或独立 $lookup）
        'bidCount': {'type': 'int', 'lookup': {'$size': {'$ifNull': ['$bidders', []]}}},
        # asyncFn：异步计算，只有 GQL 显式请求该字段才执行
    },
    'indexes': [
        {'keys': {'status': 1, 'startTime': -1}},
        {'keys': {'email': 1}, 'options': {'unique': True}},   # unique 索引会被 mutation 的 upsert 条件用到
    ],
    'read': [...], 'write': [...],   # schema 级角色白名单，含 'creator' 伪角色 = doc.createdBy === ctx.userId
}
```

要点：
- **类型全集**：`string/int/long/float/double/boolean/array/object/date/any`。array/object 零值为每次新建实例（不会跨文档串引用）。
- **每个业务 schema 自动注册归档附表** `<name>Deleted` / `<collection>_deleted`，`remove()` 时先归档（附 `deletedAt` 毫秒）再物理删除。
- 注册统一在 `server-py/db/store.py` 里 `store.register(...)`，不要散落各处。
- 本项目库为全新库，`_id` 一律是 idPrefix 生成的字符串，**无需 ObjectId 包装**。

## 二、查询（GQL 语法，5 个参数）

```
Model($condition:@c0,$sort:@s1,$skip:@sk,$limit:@l1,$pipeline:@p1) {
  field1, field2, obj.sub,          ← object 子字段用点号
  Relation($condition:@c2,$sort:@s3,$limit:@l2) { f3, Nested { f4 } }
}
```

- 值用 `@key` 引用 params 字典：`{'c0': {'status': 'ingested'}, 's1': {'createdAt': -1}}`。
- relation 的 `$sort` 键可引用嵌套关联字段（如 `bidders.amount`）。

```python
items = await store.query("Artwork($condition:@c0,$sort:@s1,$skip:@sk,$limit:@l) { title, status, statusLabel, images { thumb } }", {...})
one   = await store.query_one("Artwork($condition:@c0) { title }", {'c0': {'_id': aid}})
page  = await store.query_with_count("Artwork($condition:@c0,$sort:@s) { title }", {'c0': {...}, 'page': 0, 'pageSize': 20})
# page → {'items', 'total', 'hasMore', 'page', 'pageSize'}；pageSize 上限 5000 防拖库
exists = await store.exists('Artwork', {'artworkNo': no})
n      = await store.count('Artwork', {'status': 'published'})
```

规则：
- **不要手写 $lookup**，关联一律走 schema.relations + GQL 嵌套；框架自动两阶段优化（先取分页 ID 再 join）。
- **`$pipeline` 模式**：传入原生 pipeline 时框架完全放权——不追加 compute 层、不补默认值、不裁剪、不做权限字段过滤，慎用；聚合高级需求（group/sum 等）优先用 `store.aggregate(schema_name, pipeline)`。
- 递归保护：查询深度 ≤10 层，分页链 ≤4 层，超限降级为空 lookup，不崩溃。
- 蛇形别名可用：`query_one / query_with_count / parse_gql / build_pipeline` 等。

## 三、写入

```python
doc  = await store.insert('Artwork', {'title': '晨'})              # 自动生成 _id/createdAt/updatedAt
docs = await store.insert_many('Artwork', [ {...}, {...} ])

# update：纯字段 → 自动包 $set；带 '$' 前缀 key → 原生操作符透传（$inc/$unset/$addToSet…）
await store.update('Artwork', {'_id': aid}, {'status': 'published'})
await store.update('Artwork', {'_id': aid}, {'$inc': {'viewCount': 1}})
ret  = await store.update_many('Artwork', {'seriesId': sid}, {'status': 'published'})  # → {'modifiedCount'}

# remove：自动先归档到 <collection>_deleted 再物理删除
r = await store.remove('Artwork', {'_id': aid})   # → {'deletedCount', 'archivedCount'}

# mutation：智能持久化（推荐）——按 _id + unique 索引自动判 upsert，并递归填充 relation 子文档
await store.mutation('Artwork', {'artworkNo': 'GYY-01-001', 'title': 'x', 'bidders': [{'amount': 100}]})

# upsert：显式条件 upsert（不处理父子关系）
await store.upsert('Artwork', {'artworkNo': no}, {'title': 'x'})
```

规则：
- `update` 没有可更新字段会抛 `NO_FIELDS_TO_UPDATE`；`_id` 不可通过 update 修改。
- None 值一律剔除不入库（`_remove_undefined`）。
- **新建数据不必传默认值**，读取时自动补——这是"写入存最少数据"的铁律。
- 时间戳（createdAt/updatedAt）由框架维护，业务代码禁手工赋值/改写。

## 四、权限（ContextVar 请求上下文）

```python
# 每次请求入口设置一次（handler/middleware 层做）
store.set_context({'userId': uid, 'roles': ['user']})

# 系统/定时任务等内部操作，绕过权限
await store.run_as_internal(lambda: store.remove('Artwork', {'_id': aid}))
```

行为（`permission.py`）：
- 角色分三档：`super_admin/admin/internal` 放行一切；`seller/user/verified/buyer` 默认可读写公共模型；`guest` 一律禁写、默认禁读。
- `creator` 是伪角色，按 `doc.createdBy === ctx.userId` 动态判定；配置了 creator 权限的表，查询自动注入 `createdBy: userId` 所有者条件，update/remove 自动校验归属。
- 无 read/write 配置 = 已登录角色默认可读写（guest 除外）；无上下文 = 权限检查禁用（向后兼容）。
- 字段级：field/compute/relation 均可配 `read`/`write` 白名单，读写时自动裁剪。
- 捕获 `store.PermissionError`（含 `status=403`）返回客户端。

## 五、本项目约定（必须遵守）

- **storyText 铁律**：她的文字是唯一作者，`storyText` 一律原文照录，禁改写禁润色。
- 新增业务表：schema 文件放 `server-py/schema/<name>.py`，在 `server-py/db/store.py` 注册。
- 服务端只在服务器上运行：本地只做 `python -m py_compile` / import 纯逻辑模块验证，接口验证走云端。
- 测试数据用完即删：DB 里的测试作品/系列跑完 `store.remove(...)`（有归档附表，可追溯）。
- 常用表参考：`Artwork/artworks`、`Series`、`PostRecord`、`OrderRecord`、`AgentKey`、`AgentAudit`（见 `server-py/schema/`）。
