---
name: "code-structure-optimizer"
description: "Optimizes project code structure by splitting large files (>300 lines), extracting reusable code, and applying best practices. Invoke when user asks to refactor/optimize code structure, reduce file size, or improve code organization."
---

# Code Structure Optimizer

用三项策略优化项目代码结构：拆分大文件、提取可复用代码、应用最佳实践。改动前先分析完整项目上下文。

## 核心原则

- **单一职责**：每个文件/模块只有一个清晰的职责
- **DRY**：重复代码提取到共享模块
- **渐进重构**：增量改动，不破坏现有功能
- **约定优于配置**：遵循项目已有模式和约定
- **可读性优先**：为人优化，不为机器优化

## 按需加载（决策树）

正文只保留核心原则与红线约束，实现细节按需读取 `subs/` 子文件：

| 场景 | 读取文件 |
|------|---------|
| 文件拆分（>300 行）+ 目录结构优化 | [subs/file-splitting.md](subs/file-splitting.md) |
| 提取可复用代码（工具函数/组件/共享样式常量） | [subs/reusable-extraction.md](subs/reusable-extraction.md) |
| Web 开发结构规范（页面即布局盒） | [subs/web-structure.md](subs/web-structure.md) |
| 清理与合并 / 命名与内聚 / 验证清单 | [subs/cleanup-verify.md](subs/cleanup-verify.md) |

## 禁止事项

❌ 重构时改动业务逻辑  
❌ 无明显收益时过早抽象  
❌ 优化 < 200 行的文件（除非有明显结构问题）  
❌ 用 `###` 及以上层级标题  

## 注意事项

1. 始终遵循项目已有的命名规范和文件模式
2. 移动代码后更新 ALL 引用文件的 import 路径
3. 改动后必须验证项目能构建通过
4. 重构是大手术，优先做拆分大文件和提取重复代码，不做过度设计
