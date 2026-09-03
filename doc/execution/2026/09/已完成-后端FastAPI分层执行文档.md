# 经管之星·AI问数助手 后端 FastAPI 分层执行文档（mongo-store + MongoDB 适配版）

> 日期：2026-09-03 ｜ 版本：v2.0（由 v1.0 PostgreSQL/SQLAlchemy 版改写）
> 设计依据：`doc/solution/2026/09/已完成-经管之星AI问数助手需求文档.md`
> 数据层变更：**ORM(SQLAlchemy) + PostgreSQL → mongo-store + MongoDB**
> 性质：代码执行文档（AI 照此执行后端落地；本文件为执行级设计，改码前需审阅本文件）
> 底座来源：`server-py/db/mongo_store` + `.trae/skills/mongo-store-py`（复制自个人绘画集，按本项目改造）

## 0. 变更动因与影响（相对 v1.0）

**为什么改**：需求文档 §5.3/§6 的"只读账号 + SQL 白名单"依赖 PG 角色体系；本项目现有底座是 mongo-store。换用 MongoDB 后，AI 生成的查询防护由 **query\_guard（操作符/字段白名单）+ mongo-store 权限上下文** 承担，不再依赖数据库 ROI 角色。

**受影响章节（已在本文件的落地内容体现）**：

| 章节            | v1.0（PG）                    | v2.0（Mongo）                                                                |
| ------------- | --------------------------- | -------------------------------------------------------------------------- |
| §3.1 新增清单     | SQLAlchemy/psycopg2/PG\_DDL | 删掉 ORM 相关；数据层改用 `mongo_store`                                              |
| §4.2 配置       | `PG_MAIN_URL/PG_READ_URL`   | 换成 `MONGO_URI/MONGO_DB`                                                    |
| §4.3 数据库契约    | `init_ddl.sql` + 只读角色       | **mongo-store JSON schema 注册（14 核心模型；P1 步骤 7.5 加 QueryExample 后共 15）**  |
| §4.4 text2sql | LLM→SQL→sql\_guard→只读执行     | **LLM→{model, condition, fields, aggregate?}→query\_guard→mongo-store 查询** |
| §4.8 种子数据     | SQL 建表+数据                   | `store.mutation / insert` 灌库                                               |
| §7 禁止事项       | "只读连接执行"                    | 改为"非白名单聚合/危险操作符 拒绝"                                                        |

**语义口径**：对外仍叫"AI 问数"，但 AI 产出的是**对 mongo-store 模型的结构化查询**（模型名 + 条件 JSON + 聚合模板），不再是 SQL 文本。评审演示点时，"AI 生成 SQL 审计"改为"AI 生成查询 + query\_guard 审计"。需求文档 §6 的"仅 SELECT/表白名单"对应改为"仅在注册模型上查询 + 字段/操作符白名单"。

***

## 1. 目标（验收标准）

1. 后端以 FastAPI 实现，`uvicorn app.main:app` 可正常启动，`/docs` 可访问
2. 问数链路端到端打通：提问 → LLM 生成查询 → 守卫校验 → mongo-store 执行 → 结果摘要 → LLM 结论 → 结构化响应，常规问题耗时 ≤ 10s
3. AI 生成的查询 100% 只读：目标模型在注册白名单内、字段/操作符全部命中白名单、聚合仅限 `$match/$group/$sort/$limit/$project`、行数上限 200；任何越界（危险操作符/未知模型/未知字段）/错误一律拒绝
4. 需求文档 §3.1.7 的 7 个原型示例问题全部可由自制 Mongo 数据正确回答
5. 应用配置 / 模型配置 / 反馈 / 导入 / 日志 / nginx 登录校验（24h Cookie）接口可用且符合需求文档契约

## 2. 涉及端 × 角色

| 端                 | 是否涉及 | 角色   | 说明                                          |
| ----------------- | ---- | ---- | ------------------------------------------- |
| server（Python 后端） | 是    | 核心交付 | 本次执行文档全部内容                                  |
| 前端・nginx          | 部分   | 联调对象 | 接口契约在此定义，前端/nginx 另立执行文档（§4.5 给 nginx 配置参考） |
| miniapp / 其他      | 否    | -    | 不涉及                                         |

## 3. 迁移与移除清单（动手清单）

### 3.1 新增清单

| 新增项           | 路径                                                   | 说明                                                                                                 |
| ------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 依赖            | `server/requirements.txt`                            | Python 固定 3.11；`fastapi/uvicorn/pymongo[async]/pydantic/pydantic-settings/openpyxl/httpx`（去掉 SQLAlchemy/psycopg2） |
| 环境模板          | `server/.env.example`                                | `MONGO_URI/MONGO_DB`、管理员账号、SECRET\_KEY、火山 key 等（**一律占位符，不含真实值**）                                   |
| 应用入口          | `server/app/__init__.py`                             | 包标记                                                                                                |
| 启动入口          | `server/app/main.py`                                 | FastAPI 实例、CORS、路由注册、启动时 `init(db)` + 注册 schema + 种子                                               |
| 配置            | `server/app/config.py`                               | `pydantic-settings` 读 `.env`                                                                       |
| 数据层入口         | `server/app/database.py`                             | `AsyncIOMotorClient` 建连 + `mongo_store.init(db)`；提供 `get_db()`                                     |
| **schema 定义** | `server/app/models/schema_defs.py`                   | 14 个核心模型的 mongo-store JSON schema（§4.3；P1 步骤 7.5 增加 QueryExample 后共 15），业务 schema 集中定义              |
| **schema 注册** | `server/app/models/registry.py`                      | `store.register(...)` 注册全部业务+系统模型；`MODEL_TABLE` 白名单导出                                              |
| Pydantic 模型   | `server/app/schemas.py`                              | 全部请求/响应 DTO                                                                                        |
| 认证路由/服务       | `server/app/auth/router.py` `service.py`             | nginx auth\_request + HMAC Cookie 24h（同 v1.0）                                                      |
| 问数路由          | `server/app/routers/qa.py`                           | 会话/消息/日志/数据源                                                                                       |
| 配置路由          | `server/app/routers/config.py`                       | 应用配置 GET/PUT                                                                                       |
| 模型路由          | `server/app/routers/models_mgr.py`                   | 模型 CRUD/保存                                                                                         |
| 反馈路由          | `server/app/routers/feedback.py`                     | 用户提交 + 管理端列表/处理                                                                                    |
| 导入路由          | `server/app/routers/import_data.py`                  | xlsx 导入 + 导入记录                                                                                     |
| TTS 路由/服务     | `server/app/routers/tts.py` `services/tt_service.py` | 火山 TTS 代理                                                                                          |
| 问数编排          | `server/app/services/qa_service.py`                  | 会话→查询→执行→结论编排                                                                                      |
| LLM 客户端       | `server/app/services/llm_client.py`                  | httpx 封装 OpenAI 兼容协议                                                                               |
| **查询安全**      | `server/app/services/query_guard.py`                 | AI 查询只读/白名单校验（替代 sql\_guard）                                                                       |
| **查询执行**      | `server/app/services/query_executor.py`              | GQL 查询 + 受限聚合的封装执行，set\_context 注入只读角色                                                             |
| schema 注入     | `server/app/agent/schema_registry.py`                | 模型清单 + 字段注释 + 维度枚举（text-to-query 注入源）                                                              |
| prompt 组装     | `server/app/agent/prompt_builder.py`                 | system prompt 拼接                                                                                   |
| 步骤跟踪          | `server/app/agent/step_tracker.py`                   | 分析过程 5 步中间产物收集                                                                                     |
| **问法缓存**      | `server/app/services/query_cache.py`                 | 保守形态问法缓存/示例检索（§4.6.1）：精确热缓存 + 模糊 few-shot + 保守自学习                                                  |
| **prompt 增强** | `server/app/agent/prompt_builder.py`（增）              | 可选注入 query\_cache.top\_k\_fuzzy 的 few-shot 示例（阈值不达标不注入）                                            |
| 种子数据          | `server/app/seed/generate_data.py`                   | 固定种子生成自制数据（store 写入）                                                                               |

### 3.2 修改清单

| 修改项      | 文件                           | 由 → 到                                                      |
| -------- | ---------------------------- | ---------------------------------------------------------- |
| 底座库      | `server/app/db/mongo_store/` | 由 `server-py/db/mongo_store` 复制进项目，随本项目改造（权限角色、schema 重定义） |
| 需求文档     | 无                            | 不改，后端按其契约实现                                                |
| 前端/nginx | 另文档                          | 联调时对接                                                      |

> 说明：mongo-store 库本文件统一放 `server/app/db/`（跟随后端工程），便于打包部署；skill 已落地到 `.trae/skills/mongo-store-py`，二者为同一底座的两份载体。

### 3.3 删除清单

| 删除项                      | 位置      | 原因               | 替代                                |
| ------------------------ | ------- | ---------------- | --------------------------------- |
| `init_ddl.sql`           | v1.0 计划 | 不再建 PG 表         | mongo-store schema 注册             |
| SQLAlchemy/psycopg2      | v1.0 计划 | 数据层换 mongo-store | PyMongo async                     |
| `sql_guard.py`/只读 engine | v1.0 计划 | SQL 守卫换          | `query_guard.py` + mongo-store 权限 |

## 4. 详细执行契约（代码优先）

### 4.1 后端目录结构

```
server/
├── requirements.txt
├── .env.example
└── app/
    ├── main.py  config.py  database.py  schemas.py
    ├── db/mongo_store/            # 复制自 server-py/db/mongo_store（按本项目改造）
    ├── models/  schema_defs.py  registry.py
    ├── auth/  router.py  service.py
    ├── routers/  qa.py  config.py  models_mgr.py  feedback.py  import_data.py  tts.py
    ├── services/  qa_service.py  llm_client.py  query_guard.py  query_executor.py  tt_service.py
    ├── agent/  schema_registry.py  prompt_builder.py  step_tracker.py
    └── seed/  generate_data.py
```

### 4.2 配置 `.env`（`config.py` 读取）

```dotenv
# .env.example（真实值仅存服务器侧 .env，不入 git）
APP_SECRET_KEY=<随机64位hex>          # Cookie 签名
ADMIN_USER=admin
ADMIN_PASS=***REMOVED***

MONGO_URI=mongodb://127.0.0.1:27018    # 弱机本地常驻；**27017 已被同机生活助手项目 mongod 占用（deploy-rules），必须用 27018**
MONGO_DB=jingguan

VOICE_APP_ID=<火山TTS应用ID>
VOICE_ACCESS_TOKEN=<火山TTS密钥>                             # 火山 TTS
SYS_HOT_THRESHOLD=3

LLM_BASE_URL=https://api.deepseek.com/v1   # 默认模型（OpenAI 兼容），种子灌入 AiModel
LLM_API_KEY=<DeepSeek API Key>             # 真实值仅存服务器侧 .env
LLM_MODEL=deepseek-chat
```

`config.py` 用 `pydantic-settings`，字段即上表，`model_config=SettingsConfigDict(env_file=".env")`。

### 4.3 数据契约（mongo-store schema，14 核心模型；P1 步骤 7.5 加 QueryExample 后共 15）

> 统一在 `models/schema_defs.py` 定义、`models/registry.py` 注册；`_id` 字符串由 `idPrefix` 自动生成（如 `QS0001`），无 ObjectId 包装（遵循 mongo-store-py skill）。**API 出入参中所有 `id`/`session_id`/`sessionId` 字段类型均为 `string`**。
> 角色：本应用无业务登录（nginx 登录）。问数/导入走**写角色**（`internal`），AI 生成查询走**只读角色**（`query`），由 mongo-store 权限上下文区分。**权限收敛**：仅 8 个业务模型 `read` 含 `query`；所有系统模型（QaSession/QaMessage/AppConfig/AiModel/Feedback/ImportLog/QueryExample）`read` 仅 `internal`——从 schema 层面封死 AI 查询触达 API Key/配置/会话的路径（纵深防御，query\_guard 之外的第二道闸）。

**业务模型（8）**：

```python
COMMERCIAL_LEDGER_SCHEMA = {
  'name': 'CommercialLedger', 'collection': 'commercial_ledger',
  'idPrefix': 'CL', 'timestamps': True,
  'fields': {
    'signDate': {'type': 'string', 'default': ''},   # YYYY-MM-DD
    'year': 'int', 'quarter': 'int', 'month': 'int',
    'unit': {'type': 'string', 'default': ''}, 'industry': {'type': 'string', 'default': ''},
    'productLine': {'type': 'string', 'default': ''}, 'productModel': {'type': 'string', 'default': ''},
    'contractAmt': {'type': 'float', 'default': 0.0},   # 合同金额(万元)
    'income': {'type': 'float', 'default': 0.0},        # 收入额(万元)
    'customer': {'type': 'string', 'default': ''},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [
    {'keys': {'year': 1, 'unit': 1}},
    {'keys': {'year': 1, 'industry': 1}},
    {'keys': {'year': 1, 'productLine': 1}},
    {'keys': {'year': 1, 'month': 1}},
  ],
}

PPL_LEDGER_SCHEMA = {
  'name': 'PplLedger', 'collection': 'ppl_ledger',
  'idPrefix': 'PPL', 'timestamps': True,
  'fields': {
    'year': 'int', 'projectName': {'type': 'string', 'default': ''},
    'unit': {'type': 'string', 'default': ''}, 'industry': {'type': 'string', 'default': ''},
    'contractAmt': {'type': 'float', 'default': 0.0},
    'stage': {'type': 'string', 'default': ''}, 'riskLevel': {'type': 'string', 'default': '中'},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'riskLevel': 1}}],
}

GOAL_LEDGER_SCHEMA = {
  'name': 'GoalLedger', 'collection': 'goal_ledger',
  'idPrefix': 'GL', 'timestamps': True,
  'fields': {
    'year': 'int',
    'unit': {'type': 'string', 'default': ''},
    'commercialGoal': {'type': 'float', 'default': 0.0},  # 商业目标(万)
    'solutionGoal': {'type': 'float', 'default': 0.0},    # 商解目标(万)
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
}

REPORT_OVERALL_SCHEMA = {
  'name': 'ReportOverall', 'collection': 'report_overall',
  'idPrefix': 'RO', 'timestamps': True,
  'fields': {
    'year': 'int', 'unit': {'type': 'string', 'default': ''},
    'income': {'type': 'float', 'default': 0.0},
    'gcIncome': {'type': 'float', 'default': 0.0},
    'znIncome': {'type': 'float', 'default': 0.0},
    'bsIncome': {'type': 'float', 'default': 0.0},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
  # 完成率 = income/goal：应用层 join GoalLedger 计算，不落冗余列（见说明）
}

REPORT_PRODUCT_SCHEMA = {
  'name': 'ReportProduct', 'collection': 'report_product',
  'idPrefix': 'RP', 'timestamps': True,
  'fields': {
    'year': 'int', 'productLine': {'type': 'string', 'default': ''},
    'income': {'type': 'float', 'default': 0.0}, 'yoy': {'type': 'float', 'default': 0.0},  # 同比(%)
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'productLine': 1}, 'options': {'unique': True}}],
}

REPORT_SOLUTION_SCHEMA = {
  'name': 'ReportSolution', 'collection': 'report_solution',
  'idPrefix': 'RS2', 'timestamps': True,
  'fields': {
    'year': 'int', 'unit': {'type': 'string', 'default': ''},
    'solutionIncome': {'type': 'float', 'default': 0.0}, 'solutionGoal': {'type': 'float', 'default': 0.0},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
}

REPORT_INDUSTRY_SCHEMA = {
  'name': 'ReportIndustry', 'collection': 'report_industry',
  'idPrefix': 'RI', 'timestamps': True,
  'fields': {
    'year': 'int', 'industry': {'type': 'string', 'default': ''},
    'income': {'type': 'float', 'default': 0.0},
    'gcIncome': {'type': 'float', 'default': 0.0},
    'znIncome': {'type': 'float', 'default': 0.0},
    'bsIncome': {'type': 'float', 'default': 0.0},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'industry': 1}, 'options': {'unique': True}}],
}

REPORT_KEY_UNIT_SCHEMA = {
  'name': 'ReportKeyUnit', 'collection': 'report_key_unit',
  'idPrefix': 'RKU', 'timestamps': True,
  'fields': {
    'year': 'int', 'unit': {'type': 'string', 'default': ''},
    'orderAmt': {'type': 'float', 'default': 0.0}, 'notRecvAmt': {'type': 'float', 'default': 0.0},
    'riskCount': {'type': 'int', 'default': 0},
  },
  'read': ['internal', 'query'], 'write': ['internal'],
  'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
}
```

**系统模型（6）**：

```python
QA_SESSION_SCHEMA = {
  'name': 'QaSession', 'collection': 'qa_session',
  'idPrefix': 'QS', 'timestamps': True,
  'fields': {
    'title': {'type': 'string', 'default': ''},
    'pinned': {'type': 'boolean', 'default': False},
    'userName': {'type': 'string', 'default': '管理员'},
    'msgCount': {'type': 'int', 'default': 0},
  },
  'read': ['internal'], 'write': ['internal'],
  'indexes': [{'keys': {'updatedAt': -1}}, {'keys': {'pinned': -1, 'updatedAt': -1}}],
}

QA_MESSAGE_SCHEMA = {
  'name': 'QaMessage', 'collection': 'qa_message',
  'idPrefix': 'QM', 'timestamps': True,
  'fields': {
    'sessionId': {'type': 'string', 'default': ''},
    'role': {'type': 'string', 'default': 'user'},     # user / ai
    'content': {'type': 'string', 'default': ''},
    'aiMeta': {'type': 'object', 'default': {}},       # ai 回复的结构化 JSON
  },
  'relations': {
    'session': {'model': 'QaSession', 'type': 'one', 'localField': 'sessionId', 'foreignField': '_id'},
  },
  'read': ['internal'], 'write': ['internal'],
  'indexes': [{'keys': {'sessionId': 1}}, {'keys': {'createdAt': -1}}],
}

APP_CONFIG_SCHEMA = {
  'name': 'AppConfig', 'collection': 'app_config',
  'idPrefix': 'CFG', 'timestamps': True,
  'fields': {'key': {'type': 'string', 'default': ''}, 'value': {'type': 'any'}},
  'read': ['internal'], 'write': ['internal'],
  'indexes': [{'keys': {'key': 1}, 'options': {'unique': True}}],
}

AI_MODEL_SCHEMA = {
  'name': 'AiModel', 'collection': 'ai_model',
  'idPrefix': 'M', 'timestamps': True,
  'fields': {
    'name': {'type': 'string', 'default': ''},   # 展示名自动生成=modelName，同名追加 host 前缀（对齐原型 mcAddModel）
    'baseUrl': {'type': 'string', 'default': ''},
    'apiKey': {'type': 'string', 'default': ''},       # 仅后端使用，出参脱敏
    'modelName': {'type': 'string', 'default': ''},
    'enabled': {'type': 'boolean', 'default': True},
  },
  'read': ['internal'], 'write': ['internal'],
}

FEEDBACK_SCHEMA = {
  'name': 'Feedback', 'collection': 'feedback',
  'idPrefix': 'FB', 'timestamps': True,
  'fields': {
    'sessionId': {'type': 'string', 'default': ''},
    'userName': {'type': 'string', 'default': '管理员'},
    'question': {'type': 'string', 'default': ''},
    'aiReply': {'type': 'string', 'default': ''},
    'description': {'type': 'string', 'default': ''},
    'status': {'type': 'string', 'default': '待处理'},   # 待处理 / 已处理
    'remark': {'type': 'string', 'default': ''},
  },
  'read': ['internal'], 'write': ['internal'],
  'indexes': [{'keys': {'status': 1}}, {'keys': {'createdAt': -1}}],
}

IMPORT_LOG_SCHEMA = {
  'name': 'ImportLog', 'collection': 'import_log',
  'idPrefix': 'IL', 'timestamps': True,
  'fields': {
    'type': {'type': 'string', 'default': ''},          # commercial / ppl / goal
    'filename': {'type': 'string', 'default': ''},
    'operator': {'type': 'string', 'default': '管理员'},
    'year': 'int',
    'statDeadline': {'type': 'string', 'default': ''},  # YYYY-MM-DD
    'status': {'type': 'string', 'default': ''},
    'errorMsg': {'type': 'string', 'default': ''},
  },
  'read': ['internal'], 'write': ['internal'],
  'indexes': [{'keys': {'type': 1}}, {'keys': {'createdAt': -1}}],
}

# ---- 问法缓存/示例检索（保守形态，见 §4.6.1，P1）----
QUERY_EXAMPLE_SCHEMA = {
  'name': 'QueryExample', 'collection': 'query_example',
  'idPrefix': 'QE', 'timestamps': True,
  'fields': {
    'qnorm': {'type': 'string', 'default': ''},       # 归一化问法（去空白/标点/全半角），唯一键
    'question': {'type': 'string', 'default': ''},    # 原始问法（展示用）
    'template': {'type': 'object', 'default': {}},    # 已验证查询模板：{model,mode,condition,fields,sort,aggregate?,chart_type?}
    'hit': {'type': 'int', 'default': 0},             # 命中次数（常问统计）
    'favor': {'type': 'int', 'default': 1},           # 置信度（自学习权重，保守升降）
    'schemaVer': {'type': 'string', 'default': '1'},  # schema 版本（变更时失效）
  },
  'read': ['internal'], 'write': ['internal'],
  'indexes': [
    {'keys': {'qnorm': 1}, 'options': {'unique': True}},
    {'keys': {'hit': -1}},
    {'keys': {'favor': -1}},
  ],
}
```

`registry.py` 关键导出：`REGISTERED = [所有 schema]`；`MODEL_TABLE = {schema.name: schema}`（query\_guard 白名单来源）。

**完成率/占比/同比等派生指标**：应用层用两次 GQL 查询结果在内存小表 join 计算，**不落冗余列**（同 v1.0 语义，数据量 21×2 级，安全且简单）。

### 4.4 text-to-query 智能问数契约

**Schema 注入**（`agent/schema_registry.py`）：`DATA_SOURCES` 结构 `[{key,name,label?,group,model,fields:[{name,comment}],enum:{col:[...]}}]`，对应需求文档 §3.1.5 的 8 个数据源（`label` 为展示副标题，如"整体达成"→"中国区整体及各经营单元达成"，随 `GET /qa/sources` 返回）；`dimension_enums` 取需求 §4.4（21 单元/14 行业/3 产品线/2025·2026，**外加 riskLevel: 高/中/低**——PplLedger 的风险等级枚举必须注入，否则示例问题 6 的 LLM 可能生成"高风险"匹配不到库内值"高"）；**业务口径表 `business_glossary` 一并注入 prompt**（如"政企行业"→[数字政府, 泛政府系统部]，支撑示例问题 2 的口径映射）。注入源 = 注册模型字段 + 枚举值 + 口径表。

**提问请求**（`POST /api/qa/ask`）：

```python
class QaAskReq(BaseModel):
    question: str
    source_keys: list[str]      # 选中的数据源 key，default 全选
    chart_type: str | None = None   # 用户指定图表，null 由 LLM 选
```

**响应**（一次性 JSON，供前端渲染 AI 卡片，结构同 v1.0）：

```python
class QaAskResp(BaseModel):
    session_id: str              # mongo-store idPrefix 字符串 ID（如 QS0001），全项目 id 一律 string
    steps: list[Step]            # 分析过程 5 步：title/desc/done
    findings: list[str]          # 模块1 数据发现
    columns: list[str]; rows: list[list]     # 模块2 表格
    stats: dict                  # 模块3: {"count","avg","max","max_of","min","min_of"}
    chart: Chart | None          # 模块4: {"type","title","unit","series","x"}
    text: str                    # AI 结论文本
    follow_ups: list[str]        # 追问建议 3 条
    meta: dict                   # {"elapsed_s","tokens"}

class Step(BaseModel):
    title: str; desc: str; done: bool
```

**AI 查询输出格式（LLM 第一段）**：

```json
{
  "reasoning": "问题拆解说明",
  "model": "CommercialLedger",           // 必须命中 MODEL_TABLE 白名单
  "mode": "query" | "aggregate",         // query=简单GQL；aggregate=受限聚合
  "condition": {"year": 2026, "industry": {"$in": ["数字政府","泛政府系统部"]}, "income": {"$gte":3000,"$lte":5000}},
  "fields": ["unit","income"],           // ⊆ schema.fields
  "sort": {"income": -1},
  "aggregate": {                          // mode=aggregate 时
    "groupBy": ["productModel"],
    "measures": {"income": "sum"},        // sum/avg/count/min/max
    "op": "let"
  },
  "chart_type": "pie"          # 枚举固定: bar|bar_h|pie|line（prompt 硬约束，前端仅渲染这四种）
}
```

**编排**（`qa_service.py`，与 `step_tracker.py` 联动，5 步）：

1. `prompt_builder.build()`：注入所选数据源模型字段 + 维度枚举 + 输出 JSON 要求 + "只在给定模型查询"约束 + 图表类型建议（**枚举固定 bar/bar\_h/pie/line**；并约定：问题与经营数据无关时输出 `{"model": null, "chitchat": true, "reply_hint": "..."}`）
2. `llm_client.chat_json(...)` 第一次调用 → 解析上述 JSON
3. **无关问题分支**：解析失败 / `model: null`（chitchat）→ 跳过取数，直接生成友好文本回复（text 填引导话术，steps 5 步标记 done、columns/rows/chart/stats 为空），**不报 403 不裸抛异常**；维度不存在（如 2008 年）→ 正常执行返回空结果，结论明确提示"未查询到该维度数据"
4. `query_guard.verify(query, allowed_models)`（§4.6 契约）通过后 → `query_executor.run(...)`；**拒绝时区分原因**：目标模型不在 `source_keys` 所选数据源内 → 返回友好提示"当前所选数据源不含所需数据，请在数据源选择中勾选对应分组"，而非笼统 403：

   - `mode=query`：组装 GQL（model + condition + fields + sort + limit≤200）→ `store.query`

   - `mode=aggregate`：由 groupBy/measures 生成受限 pipeline → `query_executor` 校验后执行

   - 注入只读上下文 `store.set_context({'roles':['query']})`，行数上限 200，超出提示"共 N 条已截断"，耗时 10s 中止

   - relations 关联（如需 ReportOverall×GoalLedger）用两次查询内存 join
5. 计算 stats（数值列记录数/均值/max/min+归属，应用层）
6. `llm_client.chat_json(...)` 第二次调用（输入含**真实结果行**）→ `{conclusion, follow_ups}`
7. 组装 `QaAskResp`（steps 各步 desc 填真实查询/取数说明）
8. 落库：新建/更新 `QaSession` + 写 `QaMessage`（user 存 content、ai 存 aiMeta）

**LLM 客户端**：`httpx.AsyncClient`，`POST {base}/chat/completions`，模型取 `AiModel` 当前启用项（默认内置 DeepSeek），采集 `usage` 与耗时。

### 4.5 认证契约（nginx auth\_request + 24h Cookie）——不变（同 v1.0）

`auth/service.py`：`issue_token`/`verify_token`（payload `{usr,exp:now+86400}` + HMAC\_SHA256）。
`auth/router.py`：`POST /api/auth/login`、`GET /api/auth/check`（auth\_request 回调）、`POST /api/auth/logout`。
nginx 参考配置同 v1.0 §4.5（auth\_request 指向 `/api/auth/check`）。

### 4.6 查询安全契约（`query_guard.py` + `query_executor.py`）

**query\_guard.verify(query, allowed\_models) → 校验列表**：

| 检查       | 约束                                                                                                                                       | 违反时                    |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| 模型白名单    | `query.model in allowed_models`（allowname ⇒ MODEL\_TABLE 交集）                                                                             | 拒绝 403                 |
| 字段白名单    | `fields ⊆ schema.fields`，**`sort` 键同样 ⊆ schema.fields**；`fields` 为空 → 返回该模型全部字段（等同白名单全量）                                                      | 拒绝                     |
| 条件操作符白名单 | condition 仅允许比较类 `$eq/$gt/$gte/$lt/$lte/$in/$nin/$ne/$exists/$regex`；**禁** **`$where/$function/$accumulator/$expr/$eval/mapReduce`** | 拒绝                     |
| 聚合白名单    | 仅 `$match/$group/$sort/$limit/$project`；groupBy ⊆ schema 字段；measures ∈ {sum,avg,count,min,max} 且目标字段为数值类型                                | 拒绝                     |
| 结果上限     | 强制 `limit ≤ 200`                                                                                                                         | 截断并提示                  |
| 超时       | 执行 10s 超时中止                                                                                                                              | 走失败重试（最多 2 次，错误回传 LLM） |

**query\_executor.run(query)**：

- 进函数即 `store.set_context({'roles':['query']})`（只读角色，mongo-store 按 schema.read 拦截一切写模型不见于白名单）

- `mode=query` → `store.query(gql, {cond: query.condition, sort, skip, limit})`

- `mode=aggregate` → 对 groupBy/measures 组装受限 pipeline → **再经 query\_guard 过一遍** → 走 mongo-store 白名单内聚合执行（`store.aggregate(model, pipeline)` 前强制满足白名单，`$where/$function` 等在第一道已拒绝）

- 能通过则执行，否则抛 `PermissionError(403)` 或友好错误

> 关键：mongo-store 有 `$pipeline`/`aggregate` 逃生舱，本项目**一律不经 LLM 生成的 pipeline 直通**，只走 query\_guard 校验后的受限形态，从根上封死裸管道泄露（见底座评估结论）。

### 4.6.1 问法缓存/示例检索（保守形态，P1 增强，非核心链路）

> 定位：**可选命中层**，服务于"高频访问、内容量大"场景。本增强**不改变主链路**，且守住三条保守原则，避免 RAG 的副作用（见需求补充评估）：
> ① **检索命中不直接驱动执行**——只有精确命中才复用模板，且复用后仍过 query\_guard；模糊检索只作 **few-shot 参考**拼入 prompt，仍走 LLM 生成。
> ② **自学习保守回写**——仅"query\_guard 通过 + 执行成功 + 用户未差评"才 upsert；被反馈差评或字段失效则降权直至剔除。
> ③ **弱机零重依赖**——只用纯 Python（归一化精确 + 字符 bigram Jaccard / 编辑距离），**不上向量库、不跑 embedding**。

**三层策略（`services/query_cache.py`）**：

```python
def qnorm(q: str) -> str:
    # 统一小写、去空白/标点、全半角归一；返回可哈希唯一键
    ...

def exact_hit(qnorm_key: str) -> dict | None:
    # L1 精确热缓存：命中 → 返回 template，并 hit+=1（常问统计）
    # 命中后由 qa_service 复用模板 → 仍走 query_guard.verify → query_executor.run

def top_k_fuzzy(q: str, k=3, min_score=0.55) -> list[dict]:
    # L2 模糊示例检索：字符 bigram Jaccard + Levenshtein 综合分，<min_score 不返回
    # 返回的模板只作为 few-shot 注入 prompt_builder，不直接执行

def upsert(template: dict, q: str, success: bool) -> None:
    # 保守自学习：success=True 且 qnorm 不存在 → 写入/升级 favor；
    # 收到差评/发现字段失效 → favor 降权，低于阈值剔除
```

**qa\_service 编排接入（在 §4.4 第 1 步 LLM 调用前）**：

1. 计算 `qnorm` → 若 `exact_hit`：
   - 复用模板 → `query_guard.verify` → `query_executor.run` → 直接出结果（省一次 LLM）
   - **校验不通过则丢弃缓存、回退走 LLM**（绝不跳过守卫）
2. 未精确命中 → `top_k_fuzzy`：
   - 命中且得分达标 → 注入 prompt 作 few-shot（`prompt_builder` 加"参考以下历史成功问法与查询"段）
   - 未命中 → 纯 LLM 生成（同 v1.0）
3. 无论哪条路径，成功后 → `query_cache.upsert(success=True)` 回写；用户点"反馈不满意"或编辑重发后 → 关联 qnorm `upsert(success=False)` 降权

**schema 失效**：schema 版本（`schemaVer`）变更时，将已有示例 `favor` 归零并重学习；`MODEL_TABLE` 变更即 bump 版本号。

**常问 Tab 数据源（对齐原型 hotConfigModal 语义：频次阈值，非手工列表）**：
- 原型确认："常问设置"弹窗 = **问题频次阈值**（同一问题出现次数 ≥ 阈值即视为常问，对齐原型 hotConfigModal；需求文档 §3.2 已同步修正为阈值语义）；阈值即 `.env` 的 `SYS_HOT_THRESHOLD` 语义，默认 3。
- `AppConfig.hotRecommend = {enabled: bool, threshold: int}`（默认 enabled=true, threshold=SYS_HOT_THRESHOLD）。
- 新增接口 `GET /api/qa/quick-asks` → `{enabled, hot: [{question, hit}]}`：`QueryExample.hit ≥ threshold` 按 `hit` 降序 top10；**冷启动**（统计为空）回退返回后端预置 2 条常问（"政企行业收入3000万-5000万数据"/"北京代表处今年达成情况"，对齐原型 `_QQ_DATA.recent`）；`enabled=false` 时前端隐藏常问 Tab。

### 4.7 其他业务接口契约（REST）——不变（同 v1.0 §4.6）

| 方法・路径                                | 作用              | 请求/响应要点                                                                |
| ------------------------------------ | --------------- | ---------------------------------------------------------------------- |
| GET `/api/qa/sessions`               | 会话列表（近30天，置顶优先） | `[{id,title,pinned,userName,msgCount,updatedAt}]`（下划线→驼峰由响应 DTO 转）     |
| POST `/api/qa/sessions`              | 新建会话            | `{title}` → `{id}`                                                     |
| PATCH `/api/qa/sessions/{id}`        | 置顶/重命名          | `{pinned?}` `{title?}`                                                 |
| DELETE `/api/qa/sessions/{id}`       | 删除会话（级联消息）      | -                                                                      |
| GET `/api/qa/sessions/{id}/messages` | 历史消息            | user 存 content；ai 存 aiMeta                                             |
| GET `/api/qa/log`                    | 日志列表            | **数据来源 = QaMessage×QaSession 内存聚合派生**（按时间窗 days/userName/内容 kw 过滤、分页），不单建日志表。注：原型日志视图无导航入口（残留代码），页面不做、仅保留本接口 |
| GET `/api/qa/quick-asks`             | 快捷提问"常问"数据      | `{enabled, hot}`，语义见 §4.6.1 常问 Tab 数据源（频次阈值）                    |
| GET `/api/qa/sources`                | 数据源定义（含默认勾选）    | 8 项分组                                                                  |
| GET/PUT `/api/config`                | 应用配置读写          | key 与值结构：`greeting={text, questions[≤10]}`（原型为单 textarea+问题列表）/ `suggestions` `tts` `stt` `modelConfig`=bool / `hotRecommend={enabled, threshold:int}` |
| GET/POST/DELETE `/api/models`        | 模型配置            | POST 仅收 baseUrl/apiKey/modelName（3 项），`name` 后端自动生成（=modelName，同名追加 host 前缀）；apiKey 出参脱敏 `sk-***` |
| GET `/api/feedback`                  | 回复校对列表          | search/userSearch/status/分页                                            |
| PUT `/api/feedback/{id}`             | 处理反馈            | `{status:"已处理", remark}`                                               |
| GET `/api/import/template`           | 下载导入模板          | 参数 `type=commercial|ppl|goal`；openpyxl 现场生成表头+1 行示例的 xlsx 流             |
| POST `/api/import/upload`            | 上传 xlsx         | multipart；type/goal 覆盖该年该表                                             |
| GET `/api/import/log`                | 导入记录            | 分页+type 过滤                                                             |
| POST `/api/tts`                      | 语音合成            | `{text}` → 代理火山 TTS                                                    |
| POST `/api/models/test`              | 新增模型前测试连接      | `{baseUrl, apiKey, modelName}` → 后端发一次最小 chat 请求，返回 `{ok, latency_ms}` 或 `{ok:false, error}`；apiKey 仅本次使用不落库（对齐原型 mcTestConnection） |

### 4.8 导入契约

- 同 v1.0：年份选择→截止日期→上传 xlsx→openpyxl 解析→校验
- **模板下载**：`GET /api/import/template?type=...` 返回该台账的 xlsx 模板（表头与解析校验共用同一份列定义常量，防止模板与解析漂移）；对应需求 §3.5"提供下载模板"与验收脚本第 7 步

- **goal 覆盖语义**：`store.remove('GoalLedger', {'year': y, 'unit': {'$exists': True}})` 后 `store.insert_many` 该年全部（mongo-store addFields 自动建档）

- 失败/部分成功写 `ImportLog(status='失败-格式不符'/'部分成功')`

- 导入后同一 Mongo 库即时报问数可见

### 4.9 种子数据（`generate_data.py`）

- `random.seed(42)` 保证可复现
- **AiModel 默认记录（DeepSeek）从 env 的 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL` 灌入**；`qa_service` 运行时若无启用模型 → 抛业务错误（禁静默兜底，python-structure-rules）

- 数量对齐需求 §4.4：commercial ≥400、ppl ≥100（含 ≥7 高风险）、goal/report\_\* × 21 单元 × 2 年度等

- 写入方式：`store.set_context({'roles':['internal']})` → `store.insert_many` 逐表灌入

- 校验逻辑自洽：明细汇总≈统计表；完成率=income/goal；占比合计=100%；yoy 保留 1 位（应用层校验脚本）

## 5. 执行步骤（逐步骤状态，可中断续做）

**执行中按步推进，每完成一步勾选；中断后从第一个** **`[ ]`** **续做。**

| 步骤         | 状态       | 详细说明                                                                                                                                                                                           |
| ---------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. 骨架与依赖   | \[ ] 待处理 | 建 `server/app/` 目录树、`requirements.txt`（pymongo\[async] 等）、`.env.example`；导入 mongo-store 库。**验证**：`py_compile` + `python -c "import fastapi, pymongo, openpyxl, httpx, pydantic_settings"`      |
| 2. 配置      | \[ ] 待处理 | `config.py`（§4.2）。**验证**：`python -c "from app.config import cfg"` 字段齐全                                                                                                                         |
| 3. 数据层     | \[ ] 待处理 | `database.py`（AsyncIOMotorClient + `init(db)`）、`models/schema_defs.py` + `registry.py`（§4.3，**14 核心模型**注册）。**验证**：`py_compile`；`python -c "from app.models.registry import REGISTERED, MODEL_TABLE"` |
| 4. 库适配与权限  | \[ ] 待处理 | 按本项目改造 mongo-store（**先改 `server-py/db/mongo_store` 源头，再整目录复制同步进项目**——python-structure-rules 铁律，禁只改副本）：新增 `query` 只读角色读取路径、确认 `read` 白名单、封禁 LLM 直通 `$pipeline/aggregate`。**验证**：`python -m py_compile db/mongo_store/*.py`；模块可 import；`server-py` 与项目内两份 diff 一致                            |
| 5. 种子数据    | \[ ] 待处理 | `generate_data.py`（§4.9），固定种子、逻辑自洽。**验证**：`py_compile`；一次导入后抽查"明细汇总=统计"                                                                                                                        |
| 6. 查询安全    | \[ ] 待处理 | `query_guard.py` + `query_executor.py`（§4.6）。**验证**：单测——合法 query 通过；危险操作符/未知模型/未知字段/越界聚合被拒                                                                                                     |
| 7. LLM 客户端 | \[ ] 待处理 | `llm_client.py`（OpenAI 兼容，usage/耗时）。**验证**：`py_compile`；配真实 Key 后一次连通（服务器）                                                                                                                     |
| 7.5 问法缓存增强 | \[ ] 待处理 | `services/query_cache.py`（§4.6.1）+ `prompt_builder.py` few-shot 注入 + `qa_service` 三层接入 + `registry` **补注册 QueryExample（第 15 个模型）**。**验证**：单测——精确命中复用模板仍过守卫；模糊命中注入参考仍走 LLM；差评降权；三原则代码注释对照                                                                |
| 8. Agent   | \[ ] 待处理 | `schema_registry.py` + `prompt_builder.py` + `step_tracker.py`。**验证**：`py_compile`；打印一份注入 system prompt 检查枚举完整                                                                                 |
| 9. 认证      | \[ ] 待处理 | `auth/service.py` + `auth/router.py`。**验证**：`py_compile`；login→check→(改 token)check 401 三连                                                                                                     |
| 10. 问数编排   | \[ ] 待处理 | `qa_service.py` + `routers/qa.py`。**验证**：`py_compile`；起本地服务 curl `/api/qa/ask` 跑通 1 个示例问题                                                                                                      |
| 11. 业务路由   | \[ ] 待处理 | `routers/config.py` `models_mgr.py` `feedback.py` `import_data.py` `tts.py`。**验证**：`py_compile` 全通过                                                                                            |
| 12. 主程序    | \[ ] 待处理 | `main.py`：路由注册、启动事件注册 schema+种子、CORS。**验证**：`py_compile`；本地 `uvicorn` 起 `/docs` 可访问（本地仅静态自检、常驻走服务器）                                                                                            |
| 13. 接口回归   | \[ ] 待处理 | 需求 §3.1.7 的 7 个示例问题逐条 curl 验证结构化响应。**验证**：7/7 通过；含越界拒绝用例                                                                                                                                       |
| 14. 部署到服务器 | \[ ] 待处理 | 走《未处理-部署与nginx登录-执行》文档：上传 server/、装依赖、配置 `.env`、nginx 接入 auth\_request、pm2 起服务 + MongoDB 常驻（端口 27018）。**验证**：云端 curl 登录+问数+守卫拒绝（testing-rules，本地不常驻）                                                            |

## 6. 实施顺序（阶段依赖）

| 阶段     | 内容                          | 依赖 |
| ------ | --------------------------- | -- |
| A 基础设施 | 步骤 1-5（骨架/配置/数据层/schema/种子） | 无  |
| B 核心能力 | 步骤 6-8（安全/LLM/Agent）        | A  |
| C 接口层  | 步骤 9-11（认证/问数/业务路由）         | B  |
| D 组装   | 步骤 12-14（主程序/回归/部署）         | C  |

## 7. 禁止事项

❌ 不建本地常驻服务实例（遵循 testing-rules：常驻/演示服务只在服务器 <user> 走 pm2，MongoDB 亦然）
❌ 不把 `.env` 真实值（SECRET\_KEY/管理员密码/Mongo 凭据/火山KEY/API Key）提交入库或写进示例文件
❌ 不经 LLM 生成的 `$pipeline`/`aggregate` 直通 mongo-store（一律先过 query\_guard 受限形态）
❌ 不允许 AI 查询访问读白名单（`internal/query`）之外的角色；`internal` 写角色绝不对 AI 查询开放
❌ 不把模型 API Key 明文返回前端（出参必须脱敏）
❌ 不手写枚举中文以外的硬编码维度值，维度一律取自 schema\_registry
❌ 不保留被取代的过渡方案（如"先用 SQLite/SQL 跑通再迁 Mongo"）

## 8. 注意事项

1. mongo-store 依赖 `pymongo[async]`，用 `AsyncIOMotorClient` 传入 `init(db)`；本地 `py_compile`/import 验模块加载，真库联调只在服务器
2. 完成率、收入占比等派生指标用应用层查询 + 内存小表 join 计算，不落冗余列
3. text-to-query 第二次 LLM 调用输入必须含**真实结果行**，避免编造结论
4. `query` 是只读角色名，勿与 MongoDB 查询关键字混淆；权限由 `store.set_context` 注入
5. 步骤完成即把 `[x]` 勾上；文件名前缀随进度 未处理→处理中→已完成
6. 评审关注：查询只读安全（query\_guard）、分层清晰、schemas 类型覆盖、自制数据可复现（固定种子）、**无 LLM 裸管道**
7. 问法缓存（§4.6.1）为 **P1 非核心增强**：默认可后置到主链路打通后再启用；启用时严守三原则——精确命中仍过守卫、模糊只作 few-shot、差评降权
8. 缓存绝不写入 `internal` 只读之外权限；`QueryExample.template` 只能存 query\_guard 白名单内形态，防污染示例库
9. 本文件为执行级设计（v2.0 适配版），审阅通过后再开始第 5 章步骤
10. services/agent/routers 核心模块函数签名一律 Python type hints（需求 §7.2 代码 review 检查点）
11. CORS 仅开发场景使用：`allow_origins=["http://localhost:5173"]`（vite dev）；生产走 nginx 同源，不依赖 CORS

