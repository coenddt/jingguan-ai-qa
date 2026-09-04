---
name: "web-front-rules-readme"
description: "web-front 开发规则总纲：全部规范索引（基础/接口/组件/架构/UI）、使用决策树、新增规则指引。导航项目规则或新增规则时调用。"
---

# web-front 开发规则总纲

> 适用目录：`web-front/`（经管之星·AI问数助手 前端）。规范体系复用自 web-saas，已按本项目路径与契约改编。

## 规则分类

### 第一类：基础规范
| 编号 | Skill | 适用场景 |
|------|-------|---------|
| 01 | web-front-01-tech-stack | 了解技术选型、引入新依赖 |
| 02 | web-front-02-daisyui-conventions | 编写任意 UI 组件 |
| 03 | web-front-03-code-style | 日常编码必读 |
| 04 | web-front-04-project-structure | 了解项目架构 |

### 第二类：接口规范
| 编号 | Skill | 适用场景 |
|------|-------|---------|
| 05 | web-front-05-api-call-conventions | 编写或修改 API 调用 |

### 第三类：组件规范
| 编号 | Skill | 适用场景 |
|------|-------|---------|
| 06 | web-front-06-search-filter | 实现搜索筛选功能 |
| 07 | web-front-07-search-component-priority | 新增列表页时必读 |
| 08 | web-front-08-upload-component | 需要文件上传功能（台账导入） |

### 第四类：架构规范
| 编号 | Skill | 适用场景 |
|------|-------|---------|
| 09 | web-front-09-component-hooks-abstraction | 开发/重构业务页面（复用组件清单） |
| - | store-init-pattern | Zustand Store 启动期初始化 |

### 第五类：UI 规范
| 编号 | Skill | 适用场景 |
|------|-------|---------|
| 10 | web-front-10-table-column-width | 创建或修改列表页面 |
| 11 | web-front-11-button-text-wrap | UI 开发 |
| - | web-front-ui-aesthetic | 视觉基调（深蓝+金色品牌） |

### 工作流
| Skill | 适用场景 |
|-------|---------|
| web-front-feature-workflow | 规划/开发新页面或新功能 |

## 快速决策树

```
开始开发？
├─ 新建页面 → 读 03(代码风格：useCallback/异步分层/业务分层)、04(项目结构)
│  ├─ 需要表格 → 09(CustomTablePagination) + 10(列宽)
│  ├─ 需要搜索 → 06(SearchFilter) + 07(优先使用)
│  ├─ 需要上传 → 08(文件上传指南)
│  ├─ 需要弹窗 → 09(ConfirmDialog/SnackbarAlert)
│  └─ 需要分页 → 09(CustomTablePagination)
├─ 修改 API → 读 05(API调用规范)
├─ 编写 UI → 读 02(daisyUI组件规范) + ui-aesthetic(视觉基调)
├─ 复杂状态/异步流程 → 封装 src/hooks/（03+09 异步分层）
├─ 纯业务函数 → 封装 src/services/（03 业务分层）
├─ 代码审查 → 读 03、07、09（重点：useCallback、then/catch、Zustand 细粒度、UI 分块拆分）
└─ 重构优化 → 读 09(UI 分块拆分原则)
```

## 新增规则说明

出现新通用模式、新规范确立、规则体系覆盖不足时，应考虑新增规则。步骤：检查是否可归入现有规则 → 创建新规则文件 → 更新本总纲 → 更新其他相关规则。
