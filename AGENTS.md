# AGENTS.md — AI 创新中心项目

> 本文件是 Codex 的常驻规则入口。分领域详细规则位于 `.agents/rules/`，按下方索引在执行对应场景前用 Read 按需读取，不要一次性全部加载。

## 项目基调（最高准绳，一切实现与取舍以此为准）

**让数据问答对话可及——自然语言进，text-to-query 出，结果直观可见。**

- 一切功能设计、交互流程、文案取舍，都服务于「用户在聊天框提问，AI 自动选模型、生成查询（text-to-query）、执行取数，并以结构化卡片（分析过程 + 数据发现 + 表格 + 统计 + 图表 + 追问建议）回答」这一目的，而非堆砌技术演示。
- 演示是生命线：智能问数链路（选模型 → 生成查询 → 执行 → 图表/结论，分析过程 5 步真实中间产物）必须端到端可演示，禁止半成品。
- 数据可信是底线：text-to-query 数据自制（8 张业务表：3 台账 + 5 统计报表，维度值以原型为准）；LLM 产出的查询一律先过守卫校验（只读 + 白名单 + 行数上限）再执行，禁裸管道直通。
- 术语注：text-to-query 指 LLM 产出对 mongo-store 模型的结构化查询（模型名 + 条件 + 聚合模板），非 SQL 文本；文档/口语中的 "text2sql/SQL" 表述一律按此理解。
- 技术实现是仆从：任何技术方案若与此基调冲突，以此基调为准重新权衡。

## 铁律（每次任务都适用）

- **常驻/演示服务实例只允许在服务器 `<user>` 账号下运行（pm2 管理），严禁在本地启动常驻实例。** 完整链路验证一律通过云端：SSH 到服务器看日志、curl 线上端口（服务器信息见按需规则 deploy-rules）。
- **临时文件**统一写在项目根 `tmp/` 目录（已 gitignore），用完立即删除；含密码的临时 SSH 脚本执行完立即删除；收尾复查无残留。
- **密钥安全**：`.env`（含令牌/连接串/API Key/密码）严禁提交入库，密钥只存在于服务器侧 .env；命令输出中密钥脱敏。
- **收尾自检（改完代码必做）**：Python 逐文件 `python -m py_compile` + `python -c "import <模块>"`；Node/TS 逐文件 `node --check`，TS 以 `tsc --noEmit` 为准；`git status` 确认无临时文件残留。

## 按需加载规则索引（.agents/rules/）

执行下列场景前，先读取对应规则文档再动手：

| 场景 | 先读 |
|------|------|
| 部署 / 上线 / SCP 上传 / SSH 服务器操作 / SFTP 传输，或询问部署路径、服务器账号 | [.agents/rules/deploy-rules.md](.agents/rules/deploy-rules.md) |
| 新建 / 修改 `server-py` 或 `server/` 的 Python 后端（FastAPI 分层、目录组织、mongo_store 数据层接入） | [.agents/rules/python-structure-rules.md](.agents/rules/python-structure-rules.md) |
| 调用 `.agents/skills` 下 CLI 工具（ssh-server-task、gallery-ingest 等）传参执行 | [.agents/rules/cli-args-rules.md](.agents/rules/cli-args-rules.md) |
| 代码修改后的自检与测试、云端验证、收尾检查的完整细节 | [.agents/rules/testing-rules.md](.agents/rules/testing-rules.md) |
| 需要回顾项目基调完整原文 | [.agents/rules/project_rules.md](.agents/rules/project_rules.md) |

## 技能（.agents/skills/）

- 项目技能位于 `.agents/skills/<skill-name>/SKILL.md`，Codex 自动扫描；需要时用 `$skill-name` 显式调用，或任务匹配技能 description 时自动触发。
- 技能正文含"按需加载"指引（如 `subs/` 子文件）时，遵循其决策树按需读取对应子文件，不要一次全部读入。
- 历史的 `.trae/` 目录为 Trae 平台遗留原版，仅供参考；Codex 一律使用 `.agents/` 下的副本，技能与规则中的执行路径以 `.agents/` 为准（密钥文件除外，见下）。
- `ssh-server-task` 与 `gallery-ingest` 技能目录内的 `.env` 含真实密钥，为保持技能可用已随目录复制，严禁提交入库；两处副本内容必须保持一致，修改时同步更新。
