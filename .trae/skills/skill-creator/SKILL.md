---
name: "skill-creator"
description: "创建 SKILL.md 文件的工具。当用户要求创建/添加任何 skill 时必须立即调用。"
---

# Skill Creator

## 核心概念

在 `.trae/skills/<skill-name>/SKILL.md` 中定义 name + description（含触发条件）+ 详细指令。

**目录**: `.trae/skills/<skill-name>/`

## 创建步骤

```js
// 1. 询问用户 skill 名称和用途
// 2. 创建目录: mkdir -p .trae/skills/<skill-name>/
// 3. 创建 SKILL.md（见下方格式）
// 4. 验证结构正确
```

## SKILL.md 格式

```markdown
---
name: "<skill-name>"
description: "<做什么 + 何时触发，≤200 字符>"
---

# <标题>

<详细指令、使用指南、示例>
```

## description 字段要求

description 必须同时包含功能描述和触发条件。

| 要素 | 要求 |
|------|------|
| 做什么 | 该 skill 的核心功能 |
| 何时触发 | 触发场景，以 "Invoke when..." 开头 |
| 语言 | 默认英文，用户指定时跟随 |
| 长度 | ≤ 200 字符 |

示例：

```
"Reviews code for best practices. Invoke when user asks for code review or before merging."
```

## 禁止事项

❌ 只口头解释如何创建而不调用本工具  
❌ 手工编写指令而不先调用本 skill  

## 注意事项

1. description 是触发匹配的关键，必须同时包含功能 + 触发条件
2. 文件必须放在 `.trae/skills/<skill-name>/SKILL.md`，路径不对则不可用
3. 创建后可用 Glob 验证文件是否存在
