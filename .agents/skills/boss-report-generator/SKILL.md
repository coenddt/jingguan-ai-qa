---
name: "boss-report-generator"
description: "Generates a boss-friendly PDF report from user-provided requirements with Mermaid diagrams converted to PNG. ONLY manually invoked via /boss-report command. DO NOT auto-invoke."
---

# Boss Report Generator

**⚠️ 仅手动调用**：用户必须输入 `/boss-report` 才触发，禁止 AI 自动调用。

## 核心概念

将需求材料转为老板友好的 PDF 报告——去掉技术术语，突出业务价值，用 Mermaid 图解呈现，支持传入预算和工期参数调整成本/时间分布。历史产物见 `doc/design/其他/boss-report/`（新系统说明v3.pdf 等）。

## 前置准备

```bash
# 确保 mmdc 可用
npm install -g @mermaid-js/mermaid-cli
```

## Step 1：读取源材料

原始需求文档 `financial-asset-agent-requirements.md` 已移除。以用户在 `/boss-report` 命令中提供的需求材料为准；若用户未提供，询问其指定源文档（如 `doc/design/` 下的设计文档），禁止凭空编造需求。

## Step 2：参数适配

| 参数 | 说明 | 默认 |
|:---|:---|:---|
| `总体参考价` | 老板给的预算，影响成本分布图 | 使用文档数据 |
| `开发时间` | 老板给的工期，影响甘特图 | 使用文档数据 |

## Step 3：创建 Mermaid 图

所有图宽高比必须在 [0.667, 1.5] 之间：

| 图 | 布局 | -w | -H | 比例 |
|:---|:---|:---|:---|:---|
| system-architecture | LR 3列 | 1440 | 1080 | 1.333 |
| ai-pipeline | TB 7节点 | 1080 | 1440 | 0.75 |
| dev-timeline | Gantt | 1440 | 1080 | 1.333 |
| cost-distribution | Pie | 1200 | 1200 | 1.0 |
| three-agents | LR 3列 | 1440 | 1080 | 1.333 |

```bash
# 宽图 (LR, gantt)
npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.png -w 1440 -H 1080 --backgroundColor white

# 长图 (TB, pipeline)
npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.png -w 1080 -H 1440 --backgroundColor white

# 方图 (pie)
npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.png -w 1200 -H 1200 --backgroundColor white
```

写入 `doc/design/其他/boss-report/mmd/` 目录。

## Step 4：生成 Markdown 报告

写入 `doc/design/其他/boss-report/boss-report.md`，结构如下：

```
# [项目名称] — 项目方案汇报
## 一、项目概述
## 二、系统功能全景（嵌入 system-architecture.png）
## 三、AI智能分析能力（嵌入 ai-pipeline.png + three-agents.png）
## 四、开发计划（嵌入 dev-timeline.png）
## 五、成本分析（嵌入 cost-distribution.png）
## 六、风险与保障
```

**写作红线**：
- 禁用代码片段（JS/JSON/API路径），禁用技术术语（MongoDB→数据库，SSE→实时传输）
- 每个功能回答"对业务意味着什么"，突出"AI生成代码+20轮自检"流程

## Step 5：生成 PDF

```bash
node "f:\独立开发者\项目\生活助手智能体\scripts\generate-boss-pdf.js"
```

输出：`doc/design/其他/boss-report/boss-report.pdf`

## 输出文件

| 文件 | 路径 |
|:---|:---|
| Markdown 报告 | `doc/design/其他/boss-report/boss-report.md` |
| PDF 报告 | `doc/design/其他/boss-report/boss-report.pdf` |
| 架构图 | `doc/design/其他/boss-report/png/system-architecture.png` |
| AI 流水线 | `doc/design/其他/boss-report/png/ai-pipeline.png` |
| 开发甘特图 | `doc/design/其他/boss-report/png/dev-timeline.png` |
| 成本分布 | `doc/design/其他/boss-report/png/cost-distribution.png` |
| 三大 Agent | `doc/design/其他/boss-report/png/three-agents.png` |

## 禁止事项

❌ 禁止自动调用（仅 `/boss-report` 命令触发）  
❌ 禁止在报告中出现代码/JSON/API路径  
❌ 禁止出现 Node.js/MongoDB/React 等技术术语  
❌ 禁止宽高比超出 [0.667, 1.5] 范围  
❌ 禁止图使用英文标签（必须中文）  

## 注意事项

1. **业务语言**：所有技术名词替换为业务友好表述，如 "向量化" → "AI语义理解"
2. **基础设施并行**：甘特图中云资源/服务器/骨架/SaaS/小程序初始化必须同一起点
3. **文件类型全覆盖**：流水线必须包含 PDF/Word/Excel/语音/视频/图片/压缩包(ZIP/RAR)
4. **开发流程强调**：每个模块描述必须体现 AI生成代码 → 20轮自检 → 人工调试 → AI迭代 → 20轮再自检
5. **成本参数可选**：老板给预算就调整饼图分布，不给就用文档数据
