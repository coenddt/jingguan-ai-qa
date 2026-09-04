---
name: "web-front-03-code-style"
description: "web-front 代码风格：文件组织、组件模式、useCallback/异步分层/业务分层强制规范、Zustand 细粒度、日期格式化、UI 文案。编写或审查代码时调用。"
---

# 代码风格和开发规范（web-front/）

## 文件组织
- 页面组件在 `web-front/src/pages/` 目录下
- 布局组件在 `web-front/src/components/Layout/` 目录
- API 代码在 `web-front/src/api/` 目录
- 状态管理 Store 在 `web-front/src/store/` 目录
- 通用工具函数在 `web-front/src/utils/` 目录（无业务语义）
- 纯业务函数在 `web-front/src/services/` 目录（按业务域拆文件）
- 自定义 Hooks 在 `web-front/src/hooks/` 目录
- 问数业务组件在 `web-front/src/features/qa/` 目录（聊天/图表/会话等）

## 组件开发规范
- 使用函数式组件 + Hooks
- 使用 `useState` 管理组件状态
- 使用 `useEffect` 处理副作用
- **组件内所有命名函数必须用 `useCallback` 包裹**并正确声明依赖（事件回调、处理函数、传给子组件的回调 props）；仅受控输入的 `onChange={(e) => setX(e.target.value)}` 等单行内联箭头可豁免
- 派生计算值用 `useMemo`

## 异步分层规范（强制）
| 层 | 规则 |
|----|------|
| 组件层（pages / features / components 组件体内） | **禁止定义 `async` 函数、禁止 `await` / `try-catch`**；组件直接消费 Promise 时用 `.then().catch().finally()` 链；错误已收敛且无返回值的 hooks 动作可直接作为事件回调调用 |
| 逻辑层（hooks / services / utils / api / store） | 异步函数用 `async` 定义，内部调用统一 `await`；错误在 hook 内收敛（配合 useSnackbar）或继续上抛 |

- 复杂状态（≥3 个关联 state，或包含异步流程）必须封装为自定义 Hook（放 `src/hooks/useXxx.ts`），组件只保留简单 UI 态
- hooks 动作内部已 `try-catch` 完整处理错误时，组件侧直接调用（fire-and-forget）；需要消费结果时组件侧用 `.then/.catch`

## 业务分层（强制）
- 通用工具函数（无业务语义，如日期格式化、localStorage 读写、错误信息提取）→ `src/utils/`
- 纯业务函数（有业务语义、可脱离组件复用，如拼接复制文本、下载 Blob、收藏读写、图表配置构建）→ `src/services/`，按业务域拆文件
- 复杂状态与异步流程 → `src/hooks/`
- 组件体内禁止堆放业务逻辑函数；发现即下沉

## 命名规范
- 组件文件使用 PascalCase
- 组件函数名使用 PascalCase
- 普通变量和函数使用 camelCase
- 常量使用 UPPER_SNAKE_CASE
- 私有变量/函数使用下划线前缀（_privateFn）

## TypeScript 规范
- 新文件一律 `.ts` / `.tsx`，禁止新建 `.js` / `.jsx`
- 组件 Props 用 `interface` 定义并导出；API 返回结构在 `src/types.ts` 用 `interface`/`type` 定义（对齐后端契约）
- 避免 `any`；无法预知类型时用 `unknown` + 类型收窄
- `npx tsc --noEmit` 零错误为每步提交底线

## 状态管理
- 使用 Zustand 创建自定义 Store
- Store 文件命名为 useXxxStore.ts
- **Zustand 必须细粒度使用**：`useXxxStore((s) => s.field)` 逐字段选择订阅；**禁止 `useXxxStore()` 无选择器解构大对象**（数据本身是数组时可整体选取，如 `(s) => s.items`）
- 全局状态放在 Store 中，本地状态使用 useState；复杂本地状态封装 hooks（见异步分层规范）
- 启动期初始化的 Store 遵循 store-init-pattern skill

## 表格刷新按钮规范
- 所有包含表格的页面必须提供刷新按钮（Refresh 图标 + Tooltip 提示"刷新"）

## 日期时间格式化规范
- 所有时间日期必须使用 dayjs 格式化，格式 `YYYY-MM-DD HH:mm`
- 空值显示 `-`：`{row.updatedAt ? dayjs(row.updatedAt).format('YYYY-MM-DD HH:mm') : '-'}`

## UI 文案规范
- 时间戳、辅助信息等使用辅助文字样式（小字号、石板灰）
- 数值类数据（统计 count/avg/max/min、金额等）使用粗体加重视觉权重

## 禁止使用的命令
- **禁止使用 `Set-Content`、`Out-File`、`Add-Content`** 等 PowerShell 文件写入命令
