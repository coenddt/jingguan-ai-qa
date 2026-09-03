---
name: "web-front-03-code-style"
description: "web-front 代码风格：文件组织、组件模式、命名规范、Zustand 状态管理、日期格式化、UI 文案。编写或审查代码时调用。"
---

# 代码风格和开发规范（web-front/）

## 文件组织
- 页面组件在 `web-front/src/pages/` 目录下
- 布局组件在 `web-front/src/components/Layout/` 目录
- API 代码在 `web-front/src/api/` 目录
- 状态管理 Store 在 `web-front/src/store/` 目录
- 工具函数在 `web-front/src/utils/` 目录
- 问数业务组件在 `web-front/src/features/qa/` 目录（聊天/图表/会话等）

## 组件开发规范
- 使用函数式组件 + Hooks
- 使用 `useState` 管理组件状态
- 使用 `useEffect` 处理副作用
- 使用 `useCallback` 和 `useMemo` 优化性能

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
- 全局状态放在 Store 中，本地状态使用 useState
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
