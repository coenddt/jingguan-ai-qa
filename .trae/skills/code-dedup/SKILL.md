---
name: "code-dedup"
description: "检查代码是否符合去重规范（重复逻辑/跨文件重复函数/缺失聚合），生成重构建议。Invoke when writing code that may duplicate existing logic, or when user asks to check/refactor duplicate code."
---

# 代码去重规范（Code Dedup）

## 触发时机
- 编写新代码时，怀疑可能重复了已有逻辑 → 先运行 `check` 再动手
- 用户指定目录/文件需要检查代码规范 → 运行 `check`
- 用户要求重构重复代码 → 运行 `refactor`

## 三条核心规则

### 规则 1：禁止重复逻辑
当同一段逻辑在 **2 处及以上**文件中出现时，必须提取为公共函数。

```js
// ❌ 错误：dd-validate.js 和 analysis-renderer.js 各自实现
function normalizeConclusionMarkdown(text) { /* ... */ }

// ✅ 正确：提取到公共文件
// markdown-utils.js
function normalizeConclusionMarkdown(text) { /* ... */ }
// 所有使用方 require('./markdown-utils')
```

### 规则 2：公共函数分级迁移
同一函数被 **2 处及以上**引用时，从原文件迁移到更公共的位置：

| 使用范围 | 存放位置 |
|---------|---------|
| 同一子目录 2+ 文件 | 子目录的 `utils.js` |
| 跨子目录但在同一项目 | 项目根的 `utils/` 或 `common/` |
| 跨项目（server-shared ↔ server-finance） | `server-shared/` |

### 规则 3：同类函数聚合
当同一文件中有 **3 个及以上**同类公共函数时，聚合到独立文件：

- **无状态纯函数** → `utils/<prefix>-utils.js`
- **有状态/带生命周期** → 封装为 Class，存 `utils/<prefix>-service.js`

```
// ❌ 分散：markdown-utils.js 里既有 normalizeConclusionMarkdown 
//    又有 normalizeChecklistText、normalizeMetaFields、normalizeEvidenceDate
// ✅ 聚合：全部放 normalize-utils.js，按功能分区
```

## CLI 工具

### 检查模式（只报告，不改代码）
```bash
node .trae/skills/code-dedup/code-dedup.js --bundle '{"cmd":"check","path":"server-finance/service"}'
```

### 重构模式（生成修复步骤，不自动修改）
```bash
node .trae/skills/code-dedup/code-dedup.js --bundle '{"cmd":"check","path":"server-finance/service","fix":true}'
```

> 统一在 **Git Bash** 终端执行（Trae 默认终端已配 Git Bash）。JSON 一律用**单引号内联**（`'...'` 内全部为字面量，无引号剥离、无中文乱码）；超长 JSON 可用 stdin heredoc（`--stdin <<'EOF'`），无需临时文件。

### 参数说明
| 参数 | 类型 | 说明 |
|------|------|------|
| `cmd` | `"check"` | 检查模式（默认） |
| `path` | `string` | 目录或文件路径，相对工作目录 |
| `fix` | `boolean` | `true` 时生成修复步骤建议 |
| `exclude` | `string[]` | 额外排除 glob 模式 |

## 输出示例
```json
{
  "summary": {
    "rule1_duplicate_logic": 1,
    "rule2_cross_file": 2,
    "rule3_aggregation": 0,
    "totalIssues": 3,
    "fileCount": 15,
    "functionCount": 42
  },
  "issues": [
    {
      "rule": 1,
      "type": "duplicate_logic",
      "files": ["server-finance/service/dd-validate.js", "server-finance/service/analysis-renderer.js"],
      "functions": ["normalizeConclusionMarkdown(markdown)", "_normalizeConclusionMarkdown(text)"],
      "similarity": 98,
      "message": "函数相似度 98%，可提取为公共函数",
      "suggestion": "将 normalizeConclusionMarkdown 提取到 server-finance/service/markdown-utils.js"
    }
  ]
}
```

## 设计原则
- **安全优先**：`fix` 模式仅生成建议，不自动修改代码
- **启发式检测**：基于函数体文本相似度 + 命名约定，无需 AST 依赖
- **渐进式**：先在子目录内检查，逐步上升到项目级
- **不破坏**：同文件内的相似函数不告警（可能是内部协作）
