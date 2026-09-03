---
name: "web-front-01-tech-stack"
description: "web-front 技术栈：React 19、Vite、TypeScript、Tailwind CSS 4、daisyUI 5、Zustand、dayjs、axios、ECharts。了解项目依赖或引入新库时调用。"
---

# 技术栈规范（web-front/）

## 核心技术
- **React**: 19.x
- **Vite**: 构建工具 (v5)
- **TypeScript**: 项目使用 TypeScript（strict 模式），新文件一律 `.ts` / `.tsx`，禁止擅自改用 JavaScript
- **React Router**: 路由管理 (v6)
- **Zustand**: 轻量级状态管理库 (v4)

## UI 与样式方案
- **Tailwind CSS**: v4.x，通过 `@tailwindcss/vite` 插件集成
- **daisyUI**: v5.x，作为 Tailwind CSS 插件使用
- **lucide-react**: 图标库（全部图标来源，统一 `strokeWidth={1.5}`）
- 自定义 CSS 变量在 `web-front/src/index.css` 的 `@theme` 中定义（深蓝+金色品牌色板）

## 本项目专用依赖
- **echarts + echarts-for-react**: 问数结果图表（柱/条/饼/折 4 类）
- **react-markdown + remark-gfm + dompurify**: AI 回复 Markdown 渲染（配合 `MarkdownView` 组件）

## 其他依赖
- **dayjs**: 轻量级日期处理库
- **axios**: HTTP 请求库（baseURL `/api`，Cookie 认证）

## 组件复用来源
通用组件复用自 `生活助手智能体/web-saas`（已复制到 `web-front/src/components/`，原为 JSX，骨架阶段统一转换为 `.tsx` 并补充类型）。web-front 新代码一律 TypeScript。

## 禁止引入
- **antd / MUI**: 禁止（与 Tailwind + daisyUI 冲突）
- 任何与既有通用组件功能重复的新组件库
