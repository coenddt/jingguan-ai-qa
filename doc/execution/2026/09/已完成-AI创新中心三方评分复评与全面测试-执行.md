# AI创新中心三方评分复评与全面测试 执行文档

> 日期: 2026-09-06
> 设计依据:
> - `.trae/rules/python-selfcheck-rules.md`（服务端 100 分评分卡）
> - `doc/Web前端极致自检规范.md`（前端 8 维加权评分卡）
> - `doc/execution/2026/09/已完成-text-to-query评测集与云端Runner-执行.md`（LLM 评测 Runner 契约）
> - `doc/report/server-selfcheck-2026-09-05.md`（服务端 v4=90.2 A）
> - `doc/test-report/2026/09/web-front极致自检报告.md`（前端 v1=4.95 A）
> - `doc/test-report/2026/09/text-to-query评测报告-20260905.md`（LLM 四指标 100/97.96/97.96/100）
> 性质: 代码执行文档（AI 照此执行）

## 1. 目标（验收标准）

1. **服务端 Python 复评 v5**：按 python-selfcheck-rules 评分卡跑全量否决项 + 6 维加权，复算总分；与 v4（90.2 A）对比，产出变化原因与意义说明。
2. **Web 前端复评 v2**：按《Web前端极致自检规范》8 维加权复算 + 否决项核对；与 v1（4.95 A）对比，产出变化原因与意义说明。
3. **大模型调用复评**：云端跑 `eval.run_eval`（49 正常 + 10 越界），复测四指标（守卫通过率 / 模型选对率 / 结果正确率 / 越界安全率），与上轮对比，产出变化原因与意义说明。
4. **三份评分结果文档各追加「复评章节」**：新分数、与上轮差值、变化原因（逐条）、意义（质量趋势判断）。保留历史快照。
5. **全面测试三件套全绿**：
   - 服务端单元测试：`pytest` 全量通过（当前基线 214 passed），覆盖率快照；
   - 客户端 E2E：Playwright 全量通过（qa.spec 3 用例 + voice.spec 全量）；
   - 整体平台压力测试：只读接口 10 个短时并发压测（每接口并发 20、时长 10s 内）；LLM 只测部分（真实问数 ≤15 请求、并发 ≤3、总耗时 ≤10min 内完成），产出 P50/P95/P99、错误率、吞吐数据。
6. **最终测试报告文档** `doc/test-report/2026/09/最终测试报告-20260906.md`：汇总三端评分 + 三类测试结果 + 发布放行判定。
7. **临时产物清理**：压测脚本/数据留在 `server/tmp/` 用后即删；`git status` 收尾确认无残留。

## 2. 涉及端 × 角色

| 端 | 是否涉及 | 角色 | 说明 |
|---|---|---|---|
| server-finance（服务端 Python） | 是 | admin | 评分 v5 + 单元测试 + 只读接口压测（云端） |
| web-front（前端 React） | 是 | admin | 评分 v2 + vitest 单测 + Playwright E2E |
| LLM 链路（问数 text-to-query） | 是 | user | 评测复评（云端）+ 压测只测小批量（token 预算内） |
| miniapp-finance | 否 | - | 本任务不涉及小程序端 |

## 3. 迁移与移除清单（动手清单）

### 3.1 新增清单

| 新增项 | 所在文件 | 说明 |
|---|---|---|
| 最终测试报告 | `doc/test-report/2026/09/最终测试报告-20260906.md` | 三端评分 + 三类测试汇总 |
| 压测脚本（临时） | `server/tmp/load_test.py` | 只读接口并发压测 + LLM 小批量；用后即删 |
| 压测结果数据 | `server/tmp/load_result.json` | 脚本输出快照；报告完成后即删 |

### 3.2 修改清单（追加章节，保留历史快照）

| 修改项 | 文件 | 说明 |
|---|---|---|
| 服务端复评章节（v5） | `doc/report/server-selfcheck-2026-09-05.md` | 文末追加「v5 复评」节：分数对比/变化原因/意义 |
| 前端复评章节（v2） | `doc/test-report/2026/09/web-front极致自检报告.md` | 文末追加「复评 v2」节 |
| LLM 评测复评章节 | `doc/test-report/2026/09/text-to-query评测报告-20260905.md` | 文末追加「复评 2026-09-06」节 |

### 3.3 删除清单

| 删除项 | 位置 | 原因 | 替代 |
|---|---|---|---|
| `load_test.py` / `load_result.json` | `server/tmp/` | 临时压测产物，防残留 | 报告正文内嵌数据 |
| 临时 SSH 脚本（含口令） | `tmp/` | testing-rules 收尾铁律 | 用后即删 |

## 4. 详细执行契约（代码优先）

### 4.1 服务端评分命令集（v5，本地 r=server/ 目录执行）

否决项（任一失败 → 总分 0，不继续）：

```bash
# ① 编译（改动文件逐个 py_compile；无改动则全量模块）：
python -m py_compile app/main.py
# ② 导入：暴露缺依赖/循环导入
python -c "import app.main"
# ③ 核心单测全量（本地内存态 ASGI，不建常驻服务）：
python -m pytest tests -q
# ④ 高危漏洞：
python -m bandit -r app -ll
python -m pip_audit --path requirements.txt   # 若无 pip_audit 用 `pip-audit`
```

加权维度（评分卡：正确性 30 / 测试质量 25 / 静态 20 / 类型 10 / 安全 10 / 可维护 5）：

```bash
# 测试质量-覆盖率（行+分支，≥90% 满分线性折算）：
python -m pytest --cov=app --cov-branch -q
# 测试质量-变异（只对 setup.cfg only_mutate 的 4 核心文件，耗时大；超时可沿用上轮 34.3% 存活值并在报告中注明）：
python -m mutmut run --paths-to-mutate "app/services/query_guard.py app/services/query_cache.py app/services/query_candidate.py app/services/query_executor.py"
# 静态质量：
python -m pylint app --fail-under=9.0
python -m ruff check app tests
# 类型安全（读 pyproject.toml 降准配置，非 --strict）：
python -m mypy app
# 可维护性：
python -m radon cc app -s   # ≤15 达标（沿用 v4 口径）
python -m vulture app       # 白名单外零死代码
```

评分折算规则（python-selfcheck-rules 评分卡）：覆盖率 15 分按 `15 × 实际/90` 折算（>90 记满分）；变异 10 分按 `10 × (30% 存活基准折算)`（沿用 v4 口径：存活 34.3% → 4.2）；pylint ≥9.0 → 12；ruff 零违规 → 8；mypy 零报错 → 10；bandit 0 高危 + pip-audit 0 CVE → 10（1 高危 −10 / 1 中危 −2，下限 0）；圈复杂度达标 → 3 + 死代码零 → 2。

### 4.2 前端评分命令集（v2，本地 r=web-front/ 目录执行）

否决项核对 + 8 维证据采集：

```bash
npx tsc --noEmit                          # 0 错误
npm run lint                              # eslint --max-warnings 0 全绿
npm test                                  # vitest 全量（基线 7 文件 30 用例）
npm run e2e                               # 先 build + playwright 全量（qa.spec 3 + voice.spec）
npm run audit:gate                        # 生产依赖 0 high
npm run build                             # vite build 成功（ECharts 独立 chunk）
```

云端实测（本轮无 UI 改动，用例引用上轮 2026-09-05 实测数据：FCP/LCP≈1032ms、CLS=0、INP=32ms、axe=0）；若 execute 前完成了 UI 相关修复，则需重跑云端真机抽查。

8 维加权公式（《Web前端极致自检规范》）：
`5×0.25(功能)+性能×0.15+安全×0.15+健壮×0.10+代码×0.10+测试×0.10+体验×0.10+a11y×0.05`。

### 4.3 LLM 复评命令集（云端 <user>@<SERVER_IP>）

```bash
ssh <user>@<SERVER_IP>
cd /home/<user>/jingguan/api && .venv/bin/python -m eval.run_eval   # 49 正常 + 10 越界
# 退出码 0 = 全部达标；解析：守卫通过率/模型选对率/结果正确率/越界安全率 + 未达标明细（自动反馈）
```

评测集基线：49 正常 + 10 越界；上轮四指标 100.0 / 97.96 / 97.96 / 100.0。

### 4.4 压力测试契约（云端 <user>，只读接口 + LLM 小批量）

**目标接口**（仅只读 GET + LLM 小批量）：

| 接口 | 方法 | 归类 | 说明 |
|---|---|---|---|
| `/api/config` | GET | 只读 | 配置读取 |
| `/api/qa/sources` | GET | 只读 | 数据源列表 |
| `/api/qa/sessions` | GET | 只读 | 会话列表 |
| `/api/qa/sessions/{sid}/messages` | GET | 只读 | 消息历史（sid 取 sessions 首条） |
| `/api/qa/quick-asks` | GET | 只读 | 快捷提问 |
| `/api/qa/log` | GET | 只读 | 问数日志 |
| `/api/models` | GET | 只读 | 模型列表 |
| `/api/import/template` | GET | 只读 | 导入模板 |
| `/api/import/log` | GET | 只读 | 导入日志 |
| `/api/feedback` | GET | 只读 | 反馈列表 |
| `/api/qa/ask` | POST | LLM 部分 | SSE 真实问数，仅 ≤15 请求、并发 ≤3 |

鉴权：先 `POST /api/auth/login`（测试账密 admin / admin123）取 session cookie，再带 cookie 压测（全部接口均受 require_login 保护）。

压测脚本契约 `server/tmp/load_test.py`（httpx + asyncio，短时即止）：

```python
# async 并发压测：login 取 cookie →
# 阶段1 只读接口：并发 20 × 每接口 10s（asyncio.gather），采集 ok/err、耗时分布(P50/P95/P99)、RPS、错误率
# 阶段2 LLM 部分：真实问数 5 题 × 并发 3（顺序批次：3/3/3/3/3，避免同批重题），
#   每题超时 90s，SSE 流式读到 [DONE]/error 计完成；统计耗时与成功；总请求 ≤15
# 输出：json 落盘 server/tmp/load_result.json；错误接口自动打印原因（自动反馈）
```

LLM 压测题（复用评测集风格的真实问法，5 题）：
1. 「2025 年各产品线签约额合计」（聚合）
2. 「查宁波市 2025 年重点项目按目标金额排序」（明细）
3. 「上季度各行业签约额平均」（avg 分组）
4. 「2025 年高风险项目有哪些」（PplLedger 明细）
5. 「各产品线单笔最高签约额」（max 分组）

Token 预算：query_gen + 执行 + 结论 × ≤15 请求，估算 ≤60k tokens，短时完成（总耗时 ≤10min），符合"短时大量 token、不宜长时消耗"约束。

## 5. 执行步骤（逐步骤状态，可中断续做）

| 步骤 | 状态 | 详细说明 |
|---|---|---|
| 1. 服务端 Python 评分 v5 | [x] 已完成 | 否决项全过（编译/导入/单测214/Bandit 0高危/pip-audit 0CVE）；6 维：正确性30+测试质量15.2+静态20+类型10+安全10+可维护5 = **90.2 A**（与 v4 持平，本轮无代码改动） |
| 2. 评分异常修复闭环（条件） | [x] 未触发 | 否决项全过、无维度低于 v4、无代码缺陷 → 无需修复 |
| 3. 前端评分 v2 | [x] 已完成 | tsc 0 错误 / lint 0 warn / vitest 7文件30用例 / audit 0 漏洞 / build 成功 / e2e 4 用例：**4.95 A**（与 v1 持平） |
| 4. LLM 评测复评（云端） | [x] 已完成 | `eval.run_eval` 49+10：守卫100% / 选对98.0% / 正确98.0% / 越界100%，tokens 164052，唯一 n36 已知歧义（与上轮持平） |
| 5. 服务端单元测试全量 + 覆盖率 | [x] 已完成 | pytest 全量 **214 passed** + 覆盖率 **66%**（与 v4 一致，已在步骤1采集） |
| 6. 客户端 E2E 全量 | [x] 已完成 | Playwright **4 passed**（qa.spec 3 + voice.spec 1） |
| 7. 整体平台压力测试（云端） | [x] 已完成 | 10 只读接口 **1430 请求 / 0 错误 / 0 5xx / P95≤5.3ms**；LLM 5 题 **100%**（平均 3.2s）；临时脚本已删 |
| 8. 更新三份评分结果文档 | [ ] 待处理 | **做什么**：按 3.2 分别在 3 份文档文末追加「复评章节」，含新分数、差值、逐条变化原因、意义（质量趋势）<br>**涉及文件**：server-selfcheck-2026-09-05.md / web-front极致自检报告.md / text-to-query评测报告-20260905.md<br>**验证方式**：每份文档出现「复评章节」且数值与步骤 1/3/4 一致 |
| 9. 产出最终测试报告 | [ ] 待处理 | **做什么**：新建 `doc/test-report/2026/09/最终测试报告-20260906.md`（结构见 4.7）<br>**涉及文件**：最终测试报告-20260906.md<br>**验证方式**：报告含三端评分 + 三类测试 + 放行判定 |
| 10. 收尾清理 | [ ] 待处理 | **做什么**：删除 `server/tmp/load_test.py`、`load_result.json` 及含口令的临时 SSH 脚本；`git status` 确认无残留<br>**涉及文件**：server/tmp、tmp/<br>**验证方式**：git status 干净（不含 .env/密钥/临时产物） |

### 4.7 最终测试报告结构（文档骨架）

```markdown
# AI创新中心 最终测试报告
> 日期: 2026-09-06 / 环境: 本地评分 + 云端(<user>@<SERVER_IP>)评测与压测
## 1. 测试概要（范围 × 结果矩阵：三端评分 + 单元/E2E/压测）
## 2. 服务端单元测试（pytest 全量结果 + 覆盖率对比 v4）
## 3. 客户端 E2E（playwright 用例 × 结果表）
## 4. 整体平台压力测试（只读接口并发表 + LLM 小批量结果 + P50/P95/P99/错误率）
## 5. 三方评分结果汇总（服务端 90.2→? / 前端 4.95→? / LLM 四指标→? 对比表 + 变化意义）
## 6. 结论与建议（发布放行判定 + 遗留问题 + 后续方向）
```

## 6. 实施顺序（阶段依赖）

| 阶段 | 内容 | 依赖 |
|---|---|---|
| 阶段 1 | 本地评分：步骤 1→2(条件)→3→5→6 | 无 |
| 阶段 2 | 云端验证：步骤 4（LLM 复评）→ 7（压测） | 阶段 1 完成（复用评分结论） |
| 阶段 3 | 文档：步骤 8（更新评分文档）→ 9（最终报告） | 阶段 1+2 全部数值就绪 |
| 阶段 4 | 收尾：步骤 10 | 阶段 3 完成 |

## 7. 禁止事项

❌ 本地启动常驻/演示服务实例（评分、单测内存态执行，不绑端口；LLM 链路上云端）
❌ 压测写操作接口（POST /api/models、POST /api/models/test、POST /api/feedback、POST /api/import/upload、POST /api/qa/sessions、POST /api/tts、WS /api/asr/ws、POST /api/import 等一律不压）
❌ LLM 长时间大批量压测（仅 ≤15 请求、并发 ≤3、总耗时 ≤10min；控制 token 短时预算）
❌ 用真实数据造脏/写库（压测只读；LLM 压测请求走只读守卫链路，不触发 mutation）
❌ 否决项未过就算分 / 无证据打分
❌ 压测脚本/SSH 临时脚本残留（含口令的用后即删）
❌ 把 .env 或密钥带入压测脚本与文档

## 8. 注意事项

1. 评分为"复评复核"性质：若无新增代码改动，分数持平属正常预期；文档须如实写明"持平/波动原因"，不强行编造变化。
2. 复评若暴露问题 → 走步骤 2 修复闭环并产出自动反馈（触发原因/命中环节/修复方式），禁止静默。
3. 变异测试只对核心 4 文件（守卫/缓存/候选/执行器），耗时大可沿用上轮存活值并注明，不跑全量。
4. 服务端单测本地可跑（进程内内存态 ASGI + monkeypatch，非常驻实例）；LLM 评测与压测一律云端。
5. 覆盖率/性能/可访问性数据以本轮回测为准；前端云端实测若无 UI 改动，引用上轮数据并在报告中注明采样时间。
6. LLM 评测存在非确定性（deepseek-v4-flash），四指标轻微波动属正常，报告须给出波动区间与趋势判断。
7. 报告文档保留历史快照（追加而非覆盖），体现质量趋势可回溯。
8. 测试数据用完即删（临时会话、压测记录），遵守 testing-rules 收尾铁律。