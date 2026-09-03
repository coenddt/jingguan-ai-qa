---
name: "web-front-feature-workflow"
description: "web-front 新页面/新功能开发工作流：页面设计、API 模块对接、组件选用、路由配置。规划/开发新页面时调用。"
---

# 新功能开发工作流（web-front/）

## 概述

遵循 **设计 → 审阅 → 开发** 三个阶段。前端目录为 `web-front/`，接口契约见 `doc/execution/2026/09/未处理-后端FastAPI分层执行文档.md`。

---

## 第一阶段：需求分析

### 1.1 理解功能方向

| 信息维度 | 说明 |
|---------|------|
| 功能目标 | 用户要完成什么（问数/配置/校对/导入） |
| 操作方式 | 增删改查？批量操作？ |
| 交互形式 | 聊天流/表格/表单/弹窗/图表 |
| 数据范围 | 全部数据/指定会话或数据源 |

### 1.2 检查现有能力

先查 `web-front/src/components/`（已复用通用组件，见 09 规范）与 `src/features/qa/`，再决定新建。

**页面位置判断标准：**

| 场景 | 位置 |
|:----|------|
| 问数链路新组件 | `src/features/qa/` 下新建 |
| 现有页面子功能 | 在现有页面中新增 Tab 或弹窗 |
| 独立新模块 | `src/pages/` 下新建页面目录 |

---

## 第二阶段：方案设计

### 2.1 组件选用规范

| 功能 | 推荐组件 |
|:----|---------|
| 页面标题 | PageHeader / PageTitle |
| 搜索筛选 | SearchFilter |
| 分页 | CustomTablePagination |
| 提示 | SnackbarAlert + useSnackbar |
| 确认弹窗 | ConfirmDialog |
| 加载遮罩 | LoadingOverlay / TableSkeleton |
| 空行占位 | EmptyTableRow |
| Markdown 渲染 | MarkdownView（AI 回复必须走此组件） |
| 图表 | `src/features/qa/charts/`（ECharts 封装，柱/条/饼/折） |
| 滚动动效 | AnimateInView |

### 2.2 API 模块对接

在 `src/api/modules/` 目录下选择或新增对应的 API 模块文件（端点清单见 05 规范）。

### 2.3 路由配置

在 `src/App.tsx` 中注册新页面路由，并补充路由守卫（未登录 → `/login`）。

---

## 第三阶段：审阅

### 3.1 自审

1. UI 风格是否与现有页面一致（深蓝+金色基调，见 web-front-ui-aesthetic）？
2. 是否覆盖了需求文档全部功能点？
3. 移动端是否可用？
4. 错误处理是否完善（401 跳登录、接口异常提示）？

### 3.2 代码规范审查

| 检查项 | 标准 |
|:------|------|
| 样式方案 | Tailwind CSS v4 + daisyUI 5（禁 antd/MUI） |
| 日期格式化 | dayjs，格式 YYYY-MM-DD HH:mm |
| 搜索筛选 | 必须使用 SearchFilter |
| 分页 | 使用 CustomTablePagination |
| 图标 | lucide-react，禁 emoji |
