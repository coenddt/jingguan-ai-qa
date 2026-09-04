# LLM 调用平台化 + 提示词工程统一管理

## Context（背景与目标）

当前 LLM 调用与提示词散落两处、缺少平台概念：
- 提示词分散：查询生成 prompt 在 [prompt_builder.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/agent/prompt_builder.py)，结论 prompt 内联硬编码在 [qa_service.py#L185-L193](file:///f:/独立开发者/项目/AI创新中心项目/server/app/services/qa_service.py#L185-L193)
- LLM 调用无平台/模型/场景分层：[llm_client.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/services/llm_client.py) 只认 `base_url/api_key/model`，`AiModel` 表无平台字段，temperature/重试次数等参数散落硬编码

目标：按"平台 → 模型 → 场景"三层架构重构：
1. **平台层**（deepseek / 火山引擎）：平台预设（base_url 等），新增平台只加一条预设
2. **模型层**（deepseek-v4-flash 等）：沿用 `AiModel` 表（管理端可视化配置），新增 `platform` 字段挂接平台
3. **场景层**（查询生成 / 结论生成…）：提示词工程目录统一管理，每个场景独立模块 + 场景特定参数（temperature、重试、few-shot 条数）

## 架构设计

```
┌─ 场景层（纯函数，agent/prompts/）─ 提示词模板 + 场景参数（temperature/retries/json）
├─ 模型层（AiModel 表）           ─ modelName / apiKey / platform（管理端配置）
└─ 平台层（llm_client 平台预设）   ─ deepseek / volcengine 的 base_url 预设
         ↓
services/llm_client.invoke(scenario_id, variables, model_conf)  ← 唯一 LLM IO 出口（不变）
```

分层铁律不变：`agent/` 纯函数禁 IO，`services/llm_client` 是唯一 LLM IO 出口。

## 改动清单

### 1. 新建提示词工程目录 `server/app/agent/prompts/`

| 文件 | 职责 |
|---|---|
| `__init__.py` | 对外唯一出口：`build_messages(scenario_id, variables)`、`scenario_params(scenario_id)`；场景不存在直接抛 `ValueError`（禁静默兜底） |
| `registry.py` | `SCENARIOS` 注册表：`{'query_gen': query_gen, 'conclusion': conclusion}`，新增场景只需注册一行 |
| `query_gen.py` | 场景① text-to-query 查询生成：`PARAMS = {'temperature': 0.1, 'json': True, 'retries': 3, 'few_shot_k': 3}` + `build(variables)` 纯函数（吸收原 `prompt_builder.py` 的 SYSTEM_TMPL / few-shot / retry 模板；variables 含 `question`、可选 `few_shots`、可选 `bad_query`+`error` 表示重试形态） |
| `conclusion.py` | 场景② 分析结论+追问：`PARAMS = {'temperature': 0.3, 'json': True, 'retries': 0}` + `build(variables)`（吸收 qa_service 内联的 `conclusion_sys`；variables 含 `question`/`query`/`rows`） |

**删除** `server/app/agent/prompt_builder.py`（内容已迁入，禁双轨并存）。

### 2. 平台层：[llm_client.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/services/llm_client.py)

- 新增 `PLATFORM_PRESETS`：`deepseek → https://api.deepseek.com/v1`、`volcengine → https://ark.cn-beijing.volces.com/api/v3`（两者均 OpenAI 兼容 `/chat/completions`，HTTP 通道复用现有 `chat()`）
- 新增 `resolve_base_url(platform, base_url)`：显式 baseUrl 优先，空则取平台预设；未知平台抛错
- 新增场景化通用入口 `invoke(scenario_id, variables, model_conf) -> tuple[obj, meta]`：
  1. `build_messages` 取该场景提示词
  2. 合并场景参数（temperature 等）
  3. `model_conf`（AiModel 记录：platform/baseUrl/apiKey/modelName）解析平台与模型
  4. `json` 场景自动 `extract_json`
- 保留低层 `chat()`（连通性测试用）与 `extract_json`

### 3. 模型层：AiModel 挂接平台

- [ai_model.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/models/schema/ai_model.py)：新增 `'platform': {'type': 'string', 'default': 'deepseek'}`（mongo_store 读取时应用 default，存量记录自动补齐，已确认 [crud.py#L665](file:///f:/独立开发者/项目/AI创新中心项目/server/app/db/mongo_store/crud.py#L665) 读路径生效）
- [config.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/config.py)：新增 `LLM_PLATFORM: str = 'deepseek'`
- [generate_data.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/seed/generate_data.py#L147-L151) `_seed_app_defaults`：插入 `platform: cfg.LLM_PLATFORM`

### 4. 业务编排：[qa_service.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/services/qa_service.py)

- `_active_model()` 投影补 `platform`
- 删除内联 `conclusion_sys` 与 `llm_kw` 拼装，三处调用改为场景化：
  - 生成：`llm_client.invoke('query_gen', {'question': question, 'few_shots': few}, model_conf)`
  - 重试：`llm_client.invoke('query_gen', {'question': ..., 'bad_query': q, 'error': last_err}, model_conf)`，重试次数从 `scenario_params('query_gen')['retries']` 读取
  - 结论：`llm_client.invoke('conclusion', {'question': ..., 'query': used_query, 'rows': sample}, model_conf)`

### 5. 管理端路由：[models_mgr.py](file:///f:/独立开发者/项目/AI创新中心项目/server/app/routers/models_mgr.py)

- `ModelIn`：新增 `platform: str = 'deepseek'`，`baseUrl` 改为可选（空则用平台预设落库）
- 新增/测试时校验 platform ∈ `PLATFORM_PRESETS`（未知平台抛 `BusinessError` 400），落库前解析 baseUrl
- `_mask` 出参补 `platform`

### 6. 前端（web-front，最小改动支撑平台切换）

- [types](file:///f:/独立开发者/项目/AI创新中心项目/web-front/src/types) `ModelItem` 加 `platform` 字段；[models.ts](file:///f:/独立开发者/项目/AI创新中心项目/web-front/src/api/modules/models.ts) add/test 载荷加 `platform`
- [ModelConfig.tsx](file:///f:/独立开发者/项目/AI创新中心项目/web-front/src/pages/config/ModelConfig.tsx)：新增"平台"下拉（DeepSeek / 火山引擎方舟），切换时 baseUrl 输入框动态占位显示对应预设 URL（baseUrl 留空即用预设）；列表项展示平台徽标

## 验证方案（按 testing-rules）

1. **本地静态自检**：`python -m py_compile` 逐个改动文件；`python -c "import app.agent.prompts"`、`import app.services.qa_service` 等模块加载验证；前端跑 `tsc --noEmit`
2. **云端链路验证**（<user> 服务器）：SCP 上传 → pm2 重启 → curl 验证：
   - `/api/models/test` 用火山引擎平台配置测试连通
   - 问数链路端到端：提问 → LLM 生成查询（过守卫）→ 执行 → 结构化卡片（表格/图表/结论/追问）渲染正常
   - 触发一次守卫失败重试路径，确认场景重试参数生效
3. 收尾 `git status` 确认无临时文件残留

## 边界（本次不做）

- 不引入新 SDK（httpx OpenAI 兼容通道足够覆盖 DeepSeek 与火山方舟）
- 不改守卫/执行器/缓存逻辑；不动 8 张业务表口径
- 不新增场景（架构预留 registry 注册位即可）
