> 适用场景：新建/修改 server/ Python 后端工程（FastAPI 分层、目录组织、mongo_store 数据层接入）时必读——提炼自《后端FastAPI分层执行文档》v2.0 的结构契约

# 分层铁律（标准目录树，新工程一律照此搭建）

```
server/app/
├── main.py        # 仅组装：实例/CORS/路由注册/启动事件，禁业务逻辑
├── config.py      # pydantic-settings 读 .env，全工程唯一配置入口
├── database.py    # 建连 + init(db) + get_db()
├── schemas.py     # 跨路由共享的请求/响应 DTO；单文件膨胀时按域拆 dto/
├── db/            # 底座库（mongo_store 等），与业务代码隔离
├── models/        # schema/ 按 schema 分文件定义（__init__ 汇总 ALL_SCHEMAS）+ registry.py 集中注册
├── routers/       # 路由层：解析参数 → 调 service → 组装响应
├── services/      # 业务编排层：核心逻辑、守卫、执行器、缓存
├── agent/         # LLM 专属：prompt 组装/schema 注入/步骤跟踪，纯函数
└── seed/          # 种子数据，固定种子可复现
```

- 依赖只向下：`routers → services → models/db`；`agent/` 只被 services 调用。禁反向 import、禁 routers 绕过 services 直接读写库
- 路由层禁业务判断/DB 操作；service 层禁碰 HTTP 细节（Request/Response），异常用业务异常（`PermissionError` 等），HTTP 状态码只在路由层映射
- 强内聚领域（如 auth：router+service 成对且互不与他人共享）可独立成包；独立后该领域文件禁再散落 routers/services 两处

# 数据层

- schema 定义与注册各只一处：`models/schema_defs.py` 定义全部模型，`models/registry.py` 注册并导出 `MODEL_TABLE`（白名单唯一事实源）；禁散落注册、禁业务代码内临时 register
- 库内字段 camelCase（对齐前端），Python 标识符/DTO snake_case；命名转换只在 schemas.py DTO 边界做一次
- 派生指标（完成率/占比/同比）一律应用层两次查询 + 内存小表 join，禁落冗余列
- 读写角色在 schema 处声明（read/write 数组），运行时 `store.set_context` 注入；AI/LLM 产出的查询一律只读角色 + 强制行数上限
- **校验与执行分离**：guard 纯校验无副作用；executor 负责角色注入/超时/限额。LLM 产出一律先过 guard 的受限形态（model+condition+fields+聚合模板），禁裸 `$pipeline`/`aggregate` 直通底座

# 纯函数与确定性

- `agent/`（prompt_builder、step_tracker、schema_registry）纯组装：禁 IO、禁时钟、禁读会话态；`llm_client` 是唯一 LLM IO 出口
- 种子数据 `random.seed` 固定，同参数同结果逐点一致
- 相似度/检索类需求先用纯 Python（bigram Jaccard / 编辑距离）百行内解决，禁为此引入向量库/embedding 重依赖

# 文件组织

- 单文件超 ~300 行且含多个职责时拆分；拆分按职责命名（`query_guard.py`），禁建 `utils.py`/`common.py` 垃圾抽屉
- `__init__.py` 只做包标记与导出，禁业务逻辑
- 没有第二个调用方不抽公共函数；同逻辑三处重复再聚合
- 底座库 mongo_store 唯一事实源在 `server/app/db/mongo_store`，改造直接改这里；其他项目（如个人绘画集）的底座副本各自维护、互不同步（原 server-py 载体已于 2026-09-04 删除）

# 禁止事项

❌ 配置散落：禁在 config.py 之外 `os.getenv`/硬编码密钥；`.env` 真实值不入 git，密钥出参脱敏
❌ 过渡方案共存：换数据层/换方案后旧方案代码立即删净，禁"先跑通再迁"双轨并存
❌ 静默兜底：模型/字段不存在直接抛业务错误，禁回退默认值
❌ 缓存命中跳过守卫：任何来源的查询模板执行前必过 guard（精确命中可复用模板，不可免检）

> 验证与部署遵循 testing-rules：本地仅 `py_compile` + import 模块加载检查；常驻服务与真库联调只在服务器（<user> 账号 pm2）
