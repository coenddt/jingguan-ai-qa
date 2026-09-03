---
name: "web-front-02-daisyui-conventions"
description: "web-front daisyUI + Tailwind CSS v4 组件使用规范：响应式设计、主题色、图标用法。编写任意 UI 组件时调用。"
---

# daisyUI + Tailwind CSS 使用规范（web-front/）

> 禁止使用 antd 或 MUI，统一 Tailwind CSS v4 + daisyUI 5。通用组件已复用到 `web-front/src/components/`，先查再用。

## 响应式设计原则
- 使用 Tailwind 的响应式前缀：`sm:`, `md:`, `lg:`, `xl:`
- 使用 CSS Grid 进行页面布局：`grid grid-cols-12 gap-4` + `col-span-N`
- 移动端优先设计
- 表格使用 `overflow-x-auto` 包装以支持小屏幕横向滚动

## 常用组件对照

| 功能 | daisyUI / Tailwind 方案 |
|-----------|------------------------|
| 按钮 | `btn btn-primary` / `btn-outline` / `btn-ghost` / `btn-sm` |
| 输入框 | `input input-bordered w-full` |
| 文本域 | `textarea textarea-bordered w-full` |
| 下拉选择 | `select select-bordered w-full` |
| 表格 | `<table className="table">` + `overflow-x-auto` |
| 分页 | `CustomTablePagination` 组件（`web-front/src/components/`） |
| 弹窗 | `<dialog className="modal modal-open"><div className="modal-box">` 或 `ConfirmDialog` 组件 |
| 消息提示 | `SnackbarAlert` + `useSnackbar` hook |
| 标签 | `badge badge-ghost` / `badge-success` / `badge-error` |
| 加载中 | `loading loading-spinner loading-md` |
| 进度条 | `<progress className="progress progress-primary">` |
| 骨架屏 | `TableSkeleton` 组件或 `<div className="skeleton h-4 w-full">` |
| 开关 | `<input type="checkbox" className="toggle toggle-primary" />` |
| 复选框 | `<input type="checkbox" className="checkbox checkbox-primary" />` |
| 卡片 | `<div className="card bg-base-100 shadow-sm border border-gray-100">` |
| 上层面板 | `<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">` |
| 分隔线 | `<hr className="border-gray-200">` |
| 导航标签 | `<div className="tabs tabs-bordered">` + `<button className="tab">` |
| 手风琴 | `<div className="collapse collapse-arrow bg-base-100 border border-gray-200 rounded-xl">`（AI 分析过程折叠区适用） |
| 面包屑 | `Breadcrumb` 组件（`web-front/src/components/`） |
| 提示 | `<div className="tooltip" data-tip="...">` |

## 图标使用
- 所有图标从 `lucide-react` 导入，禁止 emoji 替代图标
- 使用 `size` prop 控制图标大小：`size={16}`, `size={20}`, `size={24}`
- 图标作为纯 SVG 组件使用，无需额外包装

## 主题色引用
项目在 `web-front/src/index.css` 的 `@theme` 中定义以下颜色变量，可在 Tailwind 类中直接使用：

| 变量名 | Tailwind 类 | 色值 |
|-------|------------|------|
| primary | `text-primary` / `bg-primary` | #1a3a6c |
| primary-light | `text-primary-light` / `bg-primary-light` | #2c5282 |
| primary-dark | `text-primary-dark` / `bg-primary-dark` | #0f294d |
| secondary | `text-secondary` / `bg-secondary` | #b48a32 |
| secondary-light | `text-secondary-light` | #d4af37 |
| secondary-dark | `text-secondary-dark` | #8e6d24 |
| success | `text-success` / `bg-success` | #16a34a |
| warning | `text-warning` / `bg-warning` | #d97706 |
| error | `text-error` / `bg-error` | #dc2626 |
| info | `text-info` / `bg-info` | #2563eb |
| divider | `border-divider` | #e2e8f0 |

> 搭建 web-front 工程骨架时，必须把上述 `@theme` 变量与 `.glass-card` / `.gold-gradient` 等装饰类（见 web-front-ui-aesthetic skill）一并落到 `src/index.css`，否则复制来的组件样式失效。
