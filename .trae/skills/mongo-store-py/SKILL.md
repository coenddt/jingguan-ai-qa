---
name: "mongo-store-py"
description: "mongo-store（Python 版 MongoDB 数据层公共包，pip 安装）使用规范：GQL 查询、schema 注册、CRUD/mutation、权限上下文。凡涉及 server 的 MongoDB 读写、schema 定义、数据查询/持久化，必须先调用本 skill 按规则使用。"
---

# mongo-store-py — Python 版 MongoDB 数据层使用规范

模块位置：公共 PyPI 包 `mongo-store`（https://pypi.org/project/mongo-store/），源码唯一事实源在 GitHub 仓库 https://github.com/coenddt/mongo-store（本地工作区不再保留源码副本，2026-09-09 已清理；要改包先 `git clone` 到临时工作目录）。包内模块：`src/mongo_store/` 下 `__init__.py` / `schema.py` / `crud.py` / `pipeline.py` / `computes.py` / `permission.py` / `types.py`。改包流程：clone 源码 → 改代码跑 `tests/` 单测 → 升 `pyproject.toml` 版本号 → 用 pypi-publisher skill 的 `release` 命令发版 → 各项目升级依赖。server 已改为 pip 依赖线上包（2026-09-09 抽包并开源 0.1.0）。

```python
from mongo_store import init, store

await init(db)          # 传入 PyMongo async 的 db 实例，自动幂等建索引
items = await store.query("Model($condition:@c0) { field1, field2 }", {'c0': {...}})
```

## 核心理念（先记住这四条）

1. **纯 JSON schema 定义，零代码**——表结构即字典。
2. **读取时**自动补默认值 + 执行 fn 计算列。
3. **写入时只存用户数据**，不补默认值（DB 存最少数据）。
4. **GQL 树形查询 → 一次 $lookup 聚合**，不要自己写 $lookup 拼关联。

## 一、Schema 注册（models/schema/ 按模型分文件定义，models/registry.py 统一注册）

```python
{
    'name': 'CommercialLedger',     # 模型名（GQL 用）
    'collection': 'commercial_ledger',  # 集合名，缺省=name
    'idPrefix': 'CL',               # _id 前缀，自动生成 前缀+时间戳36进制+随机4位（字符串，非 ObjectId）
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
        'children': {'model': 'ChildModel', 'type': 'many', 'localField': '_id', 'foreignField': 'parentId'},
    },
    'computes': {
        # fn：应用层同步计算，depends 声明依赖字段（投影优化依赖它，必须写全）
        'statusLabel': {'type': 'string', 'depends': ['status'], 'fn': lambda item: ...},
        # lookup：聚合层计算（表达式或独立 $lookup）
        'childCount': {'type': 'int', 'lookup': {'$size': {'$ifNull': ['$children', []]}}},
        # asyncFn：异步计算，只有 GQL 显式请求该字段才执行
    },
    'indexes': [
        {'keys': {'status': 1, 'createdAt': -1}},
        {'keys': {'code': 1}, 'options': {'unique': True}},   # unique 索引会被 mutation 的 upsert 条件用到
    ],
    'read': [...], 'write': [...],   # schema 级角色白名单；本项目业务模型用 common.py 的 _BIZ_RW/_SYS_RW
}
```

要点：
- **类型全集**：`string/int/long/float/double/boolean/array/object/date/any`。array/object 零值为每次新建实例（不会跨文档串引用）。
- **每个业务 schema 自动注册归档附表** `<name>Deleted` / `<collection>_deleted`，`remove()` 时先归档（附 `deletedAt` 毫秒）再物理删除。
- 注册统一走 `models/registry.py` 的 `register_all()`（main.py lifespan 调用，幂等），禁散落注册、禁业务代码内临时 register。
- 本项目 15 个模型定义在 `app/models/schema/`（每模型一个文件），`__init__.py` 汇总 `ALL_SCHEMAS`；公共权限位见 `app/models/schema/common.py`。
- `_id` 一律是 idPrefix 生成的字符串，**无需 ObjectId 包装**。

## 二、查询（GQL 语法，5 个参数）

```
Model($condition:@c0,$sort:@s1,$skip:@sk,$limit:@l1,$pipeline:@p1) {
  field1, field2, obj.sub,          ← object 子字段用点号
  Relation($condition:@c2,$sort:@s3,$limit:@l2) { f3, Nested { f4 } }
}
```

- 值用 `@key` 引用 params 字典：`{'c0': {'status': 'ingested'}, 's1': {'createdAt': -1}}`。
- relation 的 `$sort` 键可引用嵌套关联字段（如 `children.amount`）。

```python
items = await store.query("CommercialLedger($condition:@c0,$sort:@s1,$skip:@sk,$limit:@l) { title, status, statusLabel }", {...})
one   = await store.query_one("CommercialLedger($condition:@c0) { title }", {'c0': {'_id': aid}})
page  = await store.query_with_count("CommercialLedger($condition:@c0,$sort:@s) { title }", {'c0': {...}, 'page': 0, 'pageSize': 20})
# page → {'items', 'total', 'hasMore', 'page', 'pageSize'}；pageSize 上限 5000 防拖库
exists = await store.exists('CommercialLedger', {'code': no})
n      = await store.count('CommercialLedger', {'status': 'active'})
```

规则：
- **不要手写 $lookup**，关联一律走 schema.relations + GQL 嵌套；框架自动两阶段优化（先取分页 ID 再 join）。
- **`$pipeline` 模式**：传入原生 pipeline 时框架完全放权——不追加 compute 层、不补默认值、不裁剪、不做权限字段过滤，慎用；聚合高级需求（group/sum 等）优先用 `store.aggregate(schema_name, pipeline)`。
- 递归保护：查询深度 ≤10 层，分页链 ≤4 层，超限降级为空 lookup，不崩溃。
- 蛇形别名可用：`query_one / query_with_count / parse_gql / build_pipeline` 等。

## 三、写入

```python
doc  = await store.insert('CommercialLedger', {'title': 'x'})    # 自动生成 _id/createdAt/updatedAt
docs = await store.insert_many('CommercialLedger', [ {...}, {...} ])

# update：纯字段 → 自动包 $set；带 '$' 前缀 key → 原生操作符透传（$inc/$unset/$addToSet…）
await store.update('CommercialLedger', {'_id': aid}, {'status': 'active'})
await store.update('CommercialLedger', {'_id': aid}, {'$inc': {'viewCount': 1}})
ret  = await store.update_many('CommercialLedger', {'type': t}, {'status': 'active'})  # → {'modifiedCount'}

# remove：自动先归档到 <collection>_deleted 再物理删除
r = await store.remove('CommercialLedger', {'_id': aid})   # → {'deletedCount', 'archivedCount'}

# mutation：智能持久化（推荐）——按 _id + unique 索引自动判 upsert，并递归填充 relation 子文档
await store.mutation('CommercialLedger', {'code': 'C001', 'title': 'x', 'children': [{'amount': 100}]})

# upsert：显式条件 upsert（不处理父子关系）
await store.upsert('CommercialLedger', {'code': no}, {'title': 'x'})
```

规则：
- `update` 没有可更新字段会抛 `NO_FIELDS_TO_UPDATE`；`_id` 不可通过 update 修改。
- None 值一律剔除不入库（`_remove_undefined`）。
- **新建数据不必传默认值**，读取时自动补——这是"写入存最少数据"的铁律。
- 时间戳（createdAt/updatedAt）由框架维护，业务代码禁手工赋值/改写。

## 四、权限（ContextVar 请求上下文）

```python
# 每次请求入口设置一次（路由/依赖层做）
store.set_context({'userId': uid, 'roles': ['query']})

# 系统/定时任务等内部操作，绕过权限
await store.run_as_internal(lambda: store.remove('CommercialLedger', {'_id': aid}))
```

行为（`permission.py`）：
- 角色分三档：`super_admin/admin/internal` 放行一切；中间档角色按 schema read/write 白名单放行；`guest` 一律禁写、默认禁读。
- `creator` 是伪角色，按 `doc.createdBy === ctx.userId` 动态判定；配置了 creator 权限的表，查询自动注入 `createdBy: userId` 所有者条件，update/remove 自动校验归属。
- 无 read/write 配置 = 已登录角色默认可读写（guest 除外）；无上下文 = 权限检查禁用（向后兼容）。
- 字段级：field/compute/relation 均可配 `read`/`write` 白名单，读写时自动裁剪。
- 捕获 `store.PermissionError`（含 `status=403`）返回客户端。

## 五、本项目约定（必须遵守）

- **AI 查询必过守卫**：LLM 产出的查询一律先过 `services/query_guard.py`（只读角色 + 模型白名单 + 行数上限），禁裸 `$pipeline`/`aggregate` 直通底座。
- **AI 可查模型白名单**：`models/registry.py` 的 `BUSINESS_MODELS`（3 台账 + 5 统计报表）；系统模型（qa_session/ai_model 等）read 不含 `query` 角色，双重封死。
- 新增业务模型：`models/schema/` 加文件 → 加入 `ALL_SCHEMAS` → AI 可查的进 `BUSINESS_MODELS`。
- 服务端只在服务器上运行：本地只做 `python -m py_compile` / import 纯逻辑模块验证，接口验证走云端。
- 测试数据用完即删：`store.remove(...)`（有归档附表，可追溯）。
