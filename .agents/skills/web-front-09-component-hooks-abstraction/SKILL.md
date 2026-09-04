---
name: "web-front-09-component-hooks-abstraction"
description: "web-front 公共组件与 Hooks 清单：SnackbarAlert、ConfirmDialog、PageHeader、EmptyTableRow、LoadingOverlay、CustomTablePagination、MarkdownView、useSnackbar 等。开发页面时优先复用。"
---

# 组件和 Hooks 抽象规范（web-front/）

> 以下通用组件已从 web-saas 复制到 `web-front/src/components/`（2026-09-03，原为 JSX，骨架阶段统一转换为 `.tsx` 并补充类型），样式依赖 Tailwind + daisyUI + `src/index.css` 的 `@theme` 主题变量。开发页面时**必须优先复用**，禁止重复造轮子。

## 公共组件清单

### 1. SnackbarAlert（全局提示）

位于 `src/components/SnackbarAlert/index.tsx`，配合 `useSnackbar` hook（`src/hooks/useSnackbar.ts`）使用。

```jsx
import SnackbarAlert from '../components/SnackbarAlert'
import { useSnackbar } from '../hooks/useSnackbar'

const { snackbar, showSnackbar, hideSnackbar } = useSnackbar()
showSnackbar('保存成功', 'success')

<SnackbarAlert snackbar={snackbar} onClose={hideSnackbar} />
```

### 2. ConfirmDialog（确认对话框）

位于 `src/components/ConfirmDialog/index.tsx`，用于删除/操作确认。

| Prop | 类型 | 说明 |
|------|------|------|
| `open` | `boolean` | 是否打开 |
| `onConfirm` | `function` | 确认回调 |
| `onClose` | `function` | 关闭回调 |
| `title` | `string` | 标题，默认"确认操作" |
| `content` | `string` | 内容文本（或用 children 自定义） |
| `confirmColor` | `string` | 确认按钮颜色，默认"error" |
| `loading` | `boolean` | 确认中 loading 态 |

### 3. PageHeader（页面标题栏）

位于 `src/components/PageHeader/index.tsx`。

| Prop | 类型 | 说明 |
|------|------|------|
| `title` | `string` | 页面标题 |
| `onRefresh` | `function` | 刷新回调 |
| `actions` | `array` | 操作按钮数组：`{ label, icon, onClick }` |

组合复用 `Breadcrumb` + `PageTitle`。

### 4. EmptyTableRow（表格空状态行）

```jsx
<EmptyTableRow colSpan={8} message="暂无会话数据" />
```

### 5. LoadingOverlay（加载状态）

```jsx
<LoadingOverlay loading={loading}>
  <table className="table">...</table>
</LoadingOverlay>
```

### 6. CustomTablePagination（表格分页）

```jsx
<CustomTablePagination
  page={page}
  rowsPerPage={rowsPerPage}
  total={total}
  onPageChange={handleChangePage}
  onRowsPerPageChange={handleChangeRowsPerPage}
/>
```

### 7. TableSkeleton（表格骨架屏）

```jsx
{loading ? <TableSkeleton rows={6} cols={5} /> : <table>...</table>}
```

### 8. MarkdownView（Markdown 渲染）

位于 `src/components/MarkdownView/index.tsx`，依赖 `utils/markdown`（已复用）。
**AI 回复文本（`QaAskResp.text`）渲染必须走此组件**，禁止另行手写 react-markdown 配置。

### 9. 其他已复用组件

| 组件 | 用途 |
|------|------|
| `PageTitle` | 简单页面标题 |
| `Breadcrumb` | 面包屑（react-router 自动生成） |
| `StepperIndicator` | 步骤指示器 |
| `AnimateInView` | 滚动入场动画（delay 递进） |
| `Modal` | 通用弹窗壳（替代各处手写 dialog 骨架） |
| `SearchBar` / `SearchFilter` | 搜索筛选（见 06/07 专属规范） |

## 已复用工具函数与分层（src/utils/ 与 src/services/）

| 文件 | 用途 |
|------|------|
| `utils/markdown.ts` | normalizeMarkdown / stripMarkdownForPreview |
| `utils/date.ts` | 日期工具 |
| `utils/error.ts` | 错误信息提取 |
| `utils/localStorage.ts` | localStorage 安全读写 |
| `services/*.ts` | 纯业务函数按业务域拆分（qa/tts/clipboard/download/chart/favorites/feedback/importLog，见 03 业务分层） |

## 新增通用组件的原则

- 同一模式出现 ≥2 处即提升为通用组件，放 `src/components/`
- 业务专属组件放 `src/features/qa/`，不下沉到 components

## UI 分块提取子组件（强制）

页面/组件内的 UI 分块（卡片、表格块、弹窗、表单块、列表行、页脚工具条等）**必须提取为子组件**，禁止单文件巨型 JSX：

| 子组件类型 | 存放位置 |
|-----------|---------|
| 页面私有子组件 | 页面同目录，如 `pages/Feedback/FeedbackTable.tsx`、`pages/Qa/QaTopBar.tsx` |
| 业务组件的子块 | `features/qa/` 下独立文件或组件目录（如 `features/qa/AiCard/AiSteps.tsx`） |
| 跨页面复用 | `src/components/` |

- 子组件通过 props 通信；回调 props 由父组件用 `useCallback` 提供
- 单一渲染片段（≤10 行的简单映射/条件块）可内联，不必强行拆分

## 复杂状态封装 Hooks（强制）

- 组件内复杂状态（≥3 个关联 state，或含异步流程）提取到 `src/hooks/useXxx.ts`，统一存放、规范化命名
- hooks 内部用 `async/await` + `try-catch` 收敛错误；组件内零异步（详见 web-front-03 异步分层规范）
- 示例：`useQaChat`（消息流）、`useSessionActions`（会话 CRUD）、`useModelForm`（新增模型表单）、`useGreetingForm`（开场白表单）、`useTts`（语音播放）、`usePagedList`（分页列表：items/total/page/rowsPerPage/loading/filters + 动作）

## 列表页分页组合（强制）

- 列表页分页统一用 `usePagedList`（`src/hooks/usePagedList.ts`）+ 后端库内分页接口（返回 `{items,total}`），禁再手写 page/rowsPerPage/loading 散装 state
- 同构的"全量列表 store"（防重锁 + loaded 标记）用 `createListStore`（`src/store/createListStore.ts`）工厂创建，禁每个 store 复制同构模板
