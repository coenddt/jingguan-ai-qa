# 经管之星 · AI 问数助手

> **让数据问答对话可及——自然语言进，text-to-query 出，结果直观可见。**

企业级销售经管数据管理平台，核心为 **AI 智能问数**：用户在聊天框用自然语言提问，AI 自动选模型、生成查询（text-to-query）、执行取数，并以「分析过程 5 步 + 数据发现 + 表格 + 统计 + 图表 + 追问建议」的结构化卡片流式回答。

> 术语注：**text-to-query** 指 LLM 产出对 mongo-store 模型的结构化查询（模型名 + 条件 + 聚合模板），**非 SQL 文本**；早先文档中的 "text2sql/SQL" 表述一律按此理解。

***

## ✨ 核心特性

- **智能问数链路端到端真实化**：选模型 → 生成查询 → 守卫校验 → 执行 → 图表/结论，分析过程 5 步展示真实中间产物

- **数据可信底线**：text-to-query 数据自制（8 张业务表：3 台账 + 5 统计报表，维度值取自原型）

- **防护即反馈**：LLM 产出查询一律先过守卫校验（只读 + 白名单 + 行数上限）再执行，禁裸管道直通；任何兜底 / 越界 / 拦截触发都会自动产出告警反馈供回溯加固

- **结构化回答卡片**：分析过程、数据发现、表格、统计、图表、追问建议一体呈现

- **多模型可切换**：OpenAI 兼容协议（DeepSeek / 火山方舟），模型可配置

- **语音输入**：浏览器实时录音 → 豆包语音识别 2.0 双向流式，识别文本实时回填聊天框

- **5 大功能页面**：智能问数、应用配置、模型配置、回复校对、个人中心

***

## 🧱 技术栈

| 端               | 技术                                                                            |
| --------------- | ----------------------------------------------------------------------------- |
| 前端 `web-front/` | React 19 + Vite + TypeScript + Tailwind CSS 4 + daisyUI 5 + Zustand + ECharts |
| 后端 `server/`    | Python 3.11 + FastAPI（分层）+ PyMongo（async）                                     |
| 数据库             | MongoDB（单实例，端口 27018）                                                         |
| 大模型             | OpenAI 兼容协议（DeepSeek / 火山方舟）                                                  |
| 网关              | Nginx（静态托管 + auth\_request 登录校验 + 反向代理 `/api`）                                |

***

## 📁 目录结构

```
AI创新中心项目/
├── doc/                  # 全部交付 / 需求 / 方案 / 执行 / 测试文档（见下文文档索引）
├── server/               # Python 后端（FastAPI 分层 + mongo_store 数据层 + 评测 eval + 变异测试 mutants）
│   ├── app/              #   应用主代码
│   ├── eval/             #   text-to-query 评测集与 Runner
│   └── tests/            #   后端测试
├── web-front/            # 前端（React 19 SPA）
│   ├── src/              #   页面 / 组件 / store
│   └── e2e/              #   Playwright E2E 用例
├── .agents/              # Agent 常驻规则与技能（按需加载，见 AGENTS.md）
├── .trae/                # Trae 平台遗留原版（仅供参考）
├── tmp/                  # 临时文件目录（已 gitignore，用完即删）
├── AGENTS.md             # Agent 规则入口
└── README.md             # 本文档
```

***

## 📚 重要文档索引

> 以下为项目核心技术/交付文档，均以本地相对路径给出，点击即可跳转。

### 总览与交付

| 文档                                                 | 说明                                                |
| -------------------------------------------------- | ------------------------------------------------- |
| [最终交付文档](doc/经管之星AI问数助手-最终交付文档.md)                 | v2.0 技术交付文档：架构 + 实现细节 + 完整 Mermaid 图，**读该项目先看此份** |
| [需求文档](doc/solution/2026/09/已完成-经管之星AI问数助手需求文档.md) | v1.0 需求文档（含总体技术方案），原型功能逐项拆解                       |
| [部署步骤文档](doc/部署步骤文档.md)                            | 云端（服务器 `<user>` 账号 / pm2 / nginx）部署全流程              |
| [Web 前端极致自检规范](doc/Web前端极致自检规范.md)                 | 前端极致自检评分规范                                        |

### 方案设计（doc/solution/2026/09/）

| 文档                                                                          | 说明                       |
| --------------------------------------------------------------------------- | ------------------------ |
| [问数查询链路优化 - 方案](doc/solution/2026/09/已完成-问数查询链路优化-方案.md)                    | text-to-query 查询链路优化设计   |
| [LLM 外置 JSONSchema 壳 - 方案](doc/solution/2026/09/已完成-LLM外置JSONSchema壳-方案.md) | LLM 结构化输出 JSONSchema 壳设计 |

### 执行文档（doc/execution/2026/09/）

| 文档                                                                | 说明                |
| ----------------------------------------------------------------- | ----------------- |
| [后端 FastAPI 分层执行文档](doc/execution/2026/09/已完成-后端FastAPI分层执行文档.md) | 后端分层架构落实（结构契约）    |
| [前端 React 实现 - 执行](doc/execution/2026/09/已完成-前端React实现-执行.md)     | 前端链路实现            |
| [自动反馈告警闭环 - 执行](doc/execution/2026/09/已完成-自动反馈告警闭环-执行.md)         | 纵深防御 + 自动反馈告警机制落地 |
| [问数条件不足澄清分支 - 执行](doc/execution/2026/09/未处理-问数条件不足澄清分支-执行.md)     | 条件不足澄清分支执行记录（已由澄清表单结构化落地）   |
| [澄清表单结构化 - 执行](doc/execution/2026/09/已完成-澄清表单结构化-执行.md)             | 澄清表单结构化落地                    |
| [澄清表单过度追问修复 - 复盘](doc/execution/2026/09/已完成-澄清表单过度追问修复-执行复盘.md)   | 澄清表单过度追问修复执行复盘               |
| [LLM 外置 JSONSchema 壳落地 - 执行](doc/execution/2026/09/已完成-LLM外置JSONSchema壳落地-执行.md) | LLM 结构化输出壳落地                  |
| [text-to-query 评测集与云端 Runner - 执行](doc/execution/2026/09/已完成-text-to-query评测集与云端Runner-执行.md) | 评测集与云端 Runner 落地               |
| [部署与 nginx 登录 - 执行](doc/execution/2026/09/已完成-部署与nginx登录-执行.md)         | 云端部署 + nginx 登录校验落地            |
| [结构与去重自检修复 - 执行](doc/execution/2026/09/已完成-结构与去重自检修复-执行.md)         | 代码结构优化与去重自检修复                |
| [扩充评测集聚合与复合分组 - 执行](doc/execution/2026/09/已完成-扩充评测集聚合与复合分组-执行.md) | 评测集聚合 / 复合分组扩充                |
| [安全加固修复 - 执行](doc/execution/2026/09/已完成-安全加固修复-执行.md)             | 安全加固修复执行          |

### 测试报告（doc/test-report/2026/09/）

| 文档                                                                          | 说明            |
| --------------------------------------------------------------------------- | ------------- |
| [text-to-query 评测报告](doc/test-report/2026/09/text-to-query评测报告-20260905.md) | LLM 查询生成评测集结果 |
| [web-front 极致自检报告](doc/test-report/2026/09/web-front极致自检报告.md)              | 前端极致自检评分详情    |
| [LLM 外置 JSONSchema 壳 - 测试报告](doc/test-report/2026/09/已完成-LLM外置JSONSchema壳-测试报告.md) | LLM 外置壳测试结果     |
| [服务器自检报告](doc/report/server-selfcheck-2026-09-05.md)                        | 后端自检评分详情      |

### 测试用例与其他（doc/test-case、doc/test-report）

- 测试计划 / 结果：见 [doc/test-case/2026/09/](doc/test-case/2026/09/)

- 原型文件：`doc/original/demo.html`（160 万字符纯前端演示原型，需求数据来源）

***

## 🚀 快速开始

> 铁律：**常驻/演示服务实例只允许在服务器** **`<user>`** **账号下用 pm2 运行，严禁本地启动常驻实例。** 本地仅开发编码 + 静态自检；完整链路验证走云端。详见 `AGENTS.md`。

### 后端（server/）

```bash
cd server
pip install -r requirements.txt
# 配置环境变量（参照 .env.example）
python -m uvicorn app.main:app --port 8000
```

### 前端（web-front/）

```bash
cd web-front
npm install
npm run dev       # 开发
npm run build     # 生产构建（dist/）
```

***

## 📋 项目规则体系

项目遵循「基调思想 + 自动反馈原则」双顶层准则，详见 [AGENTS.md](AGENTS.md) 与 `.agents/rules/` 分领域规则：

| 规则                                                                   | 作用                              |
| -------------------------------------------------------------------- | ------------------------------- |
| [project\_rules.md](.agents/rules/project_rules.md)                  | 项目基调最高准绳（同名文件亦在 `.trae/rules/`） |
| [sleep-deploy-rules.md](.agents/rules/deploy-rules.md)               | 部署 / SCP / SSH / 服务器账号规范        |
| [python-structure-rules.md](.agents/rules/python-structure-rules.md) | 后端 FastAPI 分层结构契约               |
| [testing-rules.md](.agents/rules/testing-rules.md)                   | 代码自检与测试、服务端运行铁律、收尾检查            |

***

## ⚠️ 注意事项

- **密钥安全**：`.env`（含令牌 / 连接串 / API Key / 密码）严禁提交入库，密钥只存在于服务器侧 `.env`。

- **临时文件**统一写 `tmp/`（已 gitignore），用完即删；含密码的临时 SSH 脚本执行完立即删除。

- **数据可信是底线**：任何 LLM 产出的查询必须先过守卫校验再执行，禁止裸管道直通。

