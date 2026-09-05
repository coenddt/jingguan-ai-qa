# LLM 外置 JSON Schema 壳 测试报告

> 日期: 2026-09-05
> 依据: doc/execution/2026/09/已完成-LLM外置JSONSchema壳落地-执行.md
> 性质: 测试报告（代码自检 + 部署 + 功能链路验证）

## 1. 测试环境

- 服务器: `<user>@<SERVER_IP>`（Ubuntu）
- 服务名 / 部署路径: `jingguan-api`（pm2 id 0）/ `/home/<user>/jingguan/api`
- 对外 API: `https://<user>.cxbidding.com`（nginx → 127.0.0.1:8000 uvicorn）
- 涉及改动文件: `app/services/json_schema_shell.py`（新增）、`app/services/llm_client.py`、`app/services/qa_service.py`
- 模型: deepseek-v4-flash（platform=deepseek）

## 2. 代码自检结果（execution 第5章 A1-A8）

| 项 | 结果 | 证据 |
|----|------|------|
| A1-A4 语法+模块导入（壳/llm_client/qa_service） | ✅ | 三文件 py_compile 0 退出; `import app.services.llm_client` 等无环/无 ImportError |
| A5 正例（壳 validate） | ✅ | `validate(aggregate 合法查询,'query_gen')==原对象`；说明：query_guard.verify 依赖云端 schema，本地不可跑，语义链路在 T4 云端验证 |
| A6 反例（10 类结构越界） | ✅ 10/10 | 缺 mode/model、多未定义键、mode 枚举外、limit 类型错、bool 当 integer、measures 缺 field/op/未知键、非对象 全部抛 ShellError，错误带 `@路径`+原因 |
| A7 attach_schema 恒定性 | ✅ | 同一场景两次 attach 完全等值（前缀稳定，可缓存） |
| A8 未注册场景直通 | ✅ | conclusion 场景 attach/validate 均原样返回 |

## 3. 部署结果（execution 第6章 D1-D6）

| 项 | 结果 | 证据 |
|----|------|------|
| D1-D2 上传 | ✅ | scp 3 文件到 `/home/<user>/jingguan/api/app/services/`；服务端 `py_compile` OK |
| D3-D4 pm2 重启/启动日志 | ✅ | `pm2 restart jingguan-api` → process 3540548 启动，`Uvicorn running on 8000`，无新 ImportError（error.log 中 ImportError 为历史崩溃循环旧栈，与本改动无关） |
| D5 curl 线上 | ✅ | `https://<user>.cxbidding.com/api/config` → 200 |
| 版本核对 | ✅ | 服务器 `grep` 确认 `json_schema_shell.validate` 与 `except (GuardError, ShellError,...)` 均就位 |

## 4. 测试结果（execution 第7章 T1-T7）

| # | 用例 | 结果 | 关键证据 | 备注 |
|---|------|------|-----------|------|
| T1 | 结构合法 query_gen（冷问） | ✅ | `query_source=llm`，3 候选全过**壳+守卫**，出 findings/table/stats/chart/text/follow_ups 卡片 | req=1567f58e0c6c，返回 5 条 |
| T1b | 精确缓存直答 | ✅ | `query_source=exact_cache`，复用模板（未走 LLM/壳，符合预期） | req=d838f8c11412 |
| T3 | 前缀缓存红线 | ✅ | 冷问 `ask_candidates cache_hit=8448 cache_miss=156`（改造前 8064/7680）；`ask_preheat cache_hit=2688` | 前缀缓存未失效 |
| T4 | aggregate 问法 | ✅ | model=ReportProduct, mode=aggregate, groupBy=productLine, sum income，正常出聚合卡片 | 语义链路（含 query_guard.verify）云端过 |
| T6 | conclusion 直通 | ✅ | text + 3 条 follow_ups 正常渲染（conclusion 未注册 schema，直通未被误伤） | |
| T5 | 结构拦截不 500 | ✅（代理覆盖） | 无法可靠诱使真实 LLM 产出结构越界；用本地 A6 10/10 反例证明 ShellError 路径 + 服务器 grep 证明串行重试 except 元组已含 ShellError | 见下"说明" |
| T7 | 测试数据清理 | ✅ | 临时 json/脚本删除；测试会话可随 DELETE 清理 | |

**T5 说明**：真实 DeepSeek 在此场景下持续产出结构合法查询（3/3 候选全过），无法自然复现结构越界。该路径的可靠性已由两层覆盖：① 本地 A6 反例断言 ShellError 精确抛出（10/10）；② 服务器侧代码就位验证 `except (GuardError, ShellError, BusinessError, RuntimeError, TimeoutError)`，确认一旦 ShellError 抛出会被捕获、触发 `auto_feedback(category='shell')` 并串行重试，最终 422 而非崩溃 500。不为此做强制注入测试为刻意避免污染生产数据与触发无关重试。

## 5. 结论与遗留

**达成情况（对照 execution 第1章 7 项目标）**：

| 目标 | 达成 |
|------|------|
| 1. 独立壳模块仅结构校验 | ✅ |
| 2. invoke 浅层挂载、chat 零改动 | ✅ |
| 3. 结构越界：候选丢弃 + 串行重试捕获 ShellError + 自动反馈、不 500 | ✅（A6 + 接线验证） |
| 4. 前缀缓存不失效 cache_hit>0 | ✅（8448 vs 8064） |
| 5. 代码自检全绿 | ✅ |
| 6. 云端链路测试通过 | ✅ |
| 7. 产出测试报告 | ✅ 本文档 |

**遗留 / 待观察**：
1. query_gen **一轮通过率**是否因壳的收紧而变化——本次云端 2 次冷问 3/3 通过，样本小，建议正常使用一段时间后对照 `ask_candidates` 的 guard/shell 失败占比。
2. 结构拦截在实际流量中出现时，验证 `auto_feedback(category='shell')` 落库可见（本次未触发属正常）。
3. mode 枚举 `{query, aggregate}` 若未来出现其他合理结构，需同步评估壳与 query_guard。

**整体判断**：壳功能稳定、零误拦、前缀缓存未退化；可按方案持续使用。