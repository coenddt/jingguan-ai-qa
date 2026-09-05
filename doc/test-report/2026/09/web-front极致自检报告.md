---
name: "web-front-extreme-self-check-report"
description: "web-front 极致自检报告：8 维度加权定级 + 本轮改造项 + 验证证据。B 级达成，总分 4.05。"
---

# Web 前端极致自检报告 · 2026-09-05

## 结论

**总分 4.05 / 5.0　级别 B（合格，可发布）**

```
4×0.25(功能) + 3×0.15(性能) + 4×0.15(安全) + 4×0.10(健壮)
+ 4×0.10(代码) + 4×0.10(测试) + 4×0.10(体验) + 3×0.05(a11y)
= 1.00 + 0.45 + 0.60 + 0.40 + 0.40 + 0.40 + 0.40 + 0.15 = 4.05
```

**否决项核对**：安全 4（>1）、无错误数据、无主流程崩溃 → 无否决。

## 分维评分表

| 维度 | 分值 | 证据 | 备注 |
|------|------|------|------|
| 功能正确性 | 4 | 静态走查 | SSE 流完整处理、三态齐全；无端到端实测扣 1 |
| 性能 | 3 | vite build 分包实测 | 路由 lazy + ECharts 独立 chunk；无 CWV/Lighthouse 实测 |
| 安全 | 4 | 全仓扫描 | 0 dangerHTML/eval；DOMPurify 全去标签；未跑 npm audit |
| 健壮性 | 4 | 代码走查 | ErrorBoundary+路由复位；AbortController；无断网降级 |
| 代码质量 | 4 | tsc --noEmit | 0 error、0 any；缺 ESLint、内联样式多扣 1 |
| 可测试性 | 4 | vitest run | 22/22 通过，核心纯逻辑 + 列表 hook |
| 交互体验 | 4 | 代码走查 | 骨架屏、spinner、防重、二次确认齐全 |
| 可访问性 | 3 | 静态走查 | 17+ 图标按钮补 aria-*；无 axe 实测扣分 |

## 本轮改造项

| 维度 | 改造 | 涉及文件 |
|------|------|----------|
| 健壮性 | 新增 ErrorBoundary（含 resetKey 路由复位） | `components/ErrorBoundary/index.tsx`、`App.tsx` |
| 性能 | 路由级 lazy + Suspense；ChartView lazy 分包 ECharts | `App.tsx`、`features/qa/AiCard/index.tsx` |
| 性能 | 修复 DevLogCard 静态引入 charts 使 ECharts 退出首屏 | `features/qa/DevLogCard.tsx` |
| 可访问性 | 17+ 图标按钮补 aria-label；toggle 补 role=switch+aria-checked | QaTopBar/InputBar/Sidebar/PageTitle/QuickAsk 等 |
| 可测试性 | 接入 vitest+jsdom；6 个测试文件 22 用例 | `vitest.config.ts`、`src/**/*.test.*` |

## 验证证据

| 项 | 结果 |
|----|------|
| `tsc --noEmit` | 0 错误（exit 0） |
| `vitest run` | 6 文件 / 22 用例全通过 |
| `vite build` | 成功；ECharts 独立 chunk，主包 280kB |
| 浏览器实测（本机瞬起 preview，主站登录页） | 见「浏览器实测证据」 |

## 浏览器实测证据（2026-09-05）

**范围说明**：真实浏览器对瞬起 preview 的静态产物实测登录页；QA 主页面 CWV/LCP/INP 需后端鉴权（仅云端可跑），不在本组实测。

| 指标 | 实测值 | 说明 |
|------|--------|------|
| TTFB | 23ms | 静态资源 |
| DOMContentLoaded | 196ms | |
| load | 200ms | |
| CLS | 0 | 滚动后无布局偏移 |
| 首屏初始字节 | 788KB → **445KB** | 修复后 |
| ECharts chunk | 退出首屏 | 由 788KB 维护到 445KB 的关键收益 |

> 生产构建发现 DevLogCard **静态**引入 charts 把 ECharts(1,053kB/537KB-gzip) 拉回主包，已改为 `React.lazy`，实测确认其退出首屏请求。

**可访问性 DOM 审计（登录页）**：按钮 1/1 具名；图片 0；输入框 2/2 有标注 → 无违规项。

## 遗留问题（未阻塞发布）

| 优先级 | 问题 | 影响 | 建议 |
|--------|------|------|------|
| P1 | 未配置 ESLint | 代码质量问题无法自动拦截 | 接入 eslint + 卡口 |
| P1 | 全仓 105 处内联 `style={{}}` | 偏离 daisyUI/Tailwind 规范 | 逐步收敛到类名 |
| P2 | 无 ErrorBoundary 子树级细分 | 单模块崩溃兜底粒度糙 | 关键模块加子边界 |
| P2 | 无断网降级/失败重试 | 弱网体验一般 | 请求层加幂等重试 |
| P2 | a11y 无 axe/Lighthouse 实测 | 对比度/焦点未量化 | 联调期跑 axe 扫描 |
| P3 | 覆盖报告工具链失灵 | CWV/覆盖门未进 CI | vitest 版本升级后再探 |

## 禁止事项

❌ 无证据打分
❌ 否决项进加权计算
❌ 绕过 `npm test` 门禁发布

## 注意事项

1. 性能/可访问量指标以真实浏览器实测为准，静态自检仅反映代码层面
2. `npm test` 为当前唯一自动化门禁；覆盖门待工具链修复后接入
3. 既有 `server/**` 等未提交改动不属本报告范围，另行提交
4. 临时构建产物 dist/ 已清理，无残留