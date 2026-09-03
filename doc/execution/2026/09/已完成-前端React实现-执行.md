# 经管之星·AI问数助手 前端 React 执行文档

> 日期：2026-09-03（2026-09-04 修订：技术栈对齐 `.trae/skills/web-front-*` 技能规范，弃用 antd，改用 Tailwind CSS 4 + daisyUI 5；语言定稿 TypeScript，React 19 + TS）
> 设计依据：`doc/solution/2026/09/已完成-经管之星AI问数助手需求文档.md`
> 接口依据：`doc/execution/2026/09/未处理-后端FastAPI分层执行文档.md`（v2.0 · mongo-store+MongoDB 版）
> 技能依据：`.trae/skills/web-front-*`（技术栈/组件/UI 规范，与本档冲突时以技能为准）
> 性质：代码执行文档（AI 照此执行前端落地）
> 目录：`web-front/`

## 1. 目标（验收标准）

1. React 19 + Vite + TypeScript 工程，`npm run dev/build` 可跑，接口全部走后端 `/api`
2. UI 一律 Tailwind CSS v4 + daisyUI 5（**禁止 antd/MUI**），图标全部 lucide-react（禁止 emoji 图标）
3. 端到端复刻原型 4 个页面全部可见功能：智能问数、应用配置、模型配置、回复校对
4. AI 回复卡片完整渲染后端 `QaAskResp`：分析过程 5 步（可折叠）+ 数据发现 + 表格 + 统计 + ECharts 图表（柱/条/饼/折）+ 追问 chips + 页脚
5. 会话管理（近30天列表/置顶/重命名/删除/新建/自动命名/切换恢复）全部走后端持久化
6. 未登录（接口 401）→ 自动跳登录页；登录后 24h 免重复登录；登出主动失效
7. 数据源选择、收藏/常问快捷提问、消息收藏/编辑/重发/复制全可用

## 2. 技术栈与规范依据（强制）

| 类别 | 选型 | 说明 |
|---|---|---|
| 框架 | React 19 + Vite 5 + **TypeScript** | strict 模式；新文件一律 `.ts`/`.tsx`，禁止擅自改用 JavaScript |
| 路由 | React Router v6 | 路由定义与守卫写在 `src/App.tsx`（不单独建 router 文件） |
| 状态 | Zustand v4 | Store 文件命名 `useXxxStore.ts`，启动期初始化遵循 store-init-pattern skill |
| UI | Tailwind CSS v4（`@tailwindcss/vite`）+ daisyUI 5 | 禁止 antd/MUI；组件对照见 §5.4 |
| 图标 | lucide-react | 统一 `strokeWidth={1.5}`，`size` 控制大小；禁止 emoji 替代图标 |
| 请求 | axios | `src/api/client.ts`：baseURL `/api`、`withCredentials`、401 拦截；API 模块在 `src/api/modules/` |
| 图表 | echarts + echarts-for-react | 封装于 `src/features/qa/charts/`，4 类图 |
| Markdown | react-markdown + remark-gfm + dompurify | AI 回复文本必须走已复用的 `MarkdownView` 组件，禁止另行手写配置 |
| 日期 | dayjs | 一律 `YYYY-MM-DD HH:mm`，空值显示 `-` |

技能索引：01-tech-stack（选型）、02-daisyui-conventions（组件对照）、03-code-style（编码）、04-project-structure（结构/路由/认证）、05-api-call-conventions（API）、06/07（SearchFilter）、08（上传）、09（公共组件复用）、10（表格列宽）、11（按钮不换行）、ui-aesthetic（深蓝+金色视觉）、store-init-pattern（Store 初始化）。

## 3. 涉及端 × 角色

| 端 | 是否涉及 | 角色 | 说明 |
|---|---|---|---|
| web-front（React） | 是 | 核心交付 | 本执行文档全部内容 |
| server（FastAPI） | 是 | 联调依赖 | 接口契约已定，本端只消费 `/api` |
| nginx | 是 | 环境 | 401→登录页跳转在本端处理；登录态以 24h HttpOnly Cookie 为准，localStorage 仅存"已登录"意向标记 |
| miniapp/other | 否 | - | 不涉及 |

## 4. 工程现状与迁移清单

### 4.1 已复用基础（已存在，禁止重建/覆盖）

`web-front/src/` 下已从 web-saas 复制完成（2026-09-03，原为 JSX），样式依赖 Tailwind + daisyUI + `src/index.css` 的 `@theme` 变量；**骨架阶段统一转换为 `.tsx`/`.ts` 并补充类型**：

| 类别 | 内容 |
|---|---|
| 通用组件 | `SnackbarAlert` `ConfirmDialog` `PageHeader` `PageTitle` `Breadcrumb` `EmptyTableRow` `LoadingOverlay` `CustomTablePagination` `TableSkeleton` `MarkdownView` `SearchFilter` `StepperIndicator` `AnimateInView`（均在 `src/components/<Name>/index.tsx`） |
| Hooks | `src/hooks/useSnackbar.js`（配合 SnackbarAlert 做全局提示） |
| 工具 | `src/utils/markdown.js` `url-state.js` `format.js` `date.js` |

开发页面时**必须优先复用**上述组件，禁止重复造轮子（详见 web-front-09 skill）。

### 4.2 新增清单

| 新增项 | 路径 | 说明 |
|---|---|---|
| 工程骨架 | `web-front/` 根文件 | Vite + React19 + TS：`package.json` `vite.config.ts` `tsconfig.json`（strict） `index.html`；依赖 axios/echarts/echarts-for-react/zustand/dayjs/react-markdown/remark-gfm/dompurify/lucide-react；dev 依赖 typescript/@types/react/@types/react-dom/tailwindcss@4/@tailwindcss/vite/daisyui@5 |
| 入口 | `src/main.tsx`、`src/App.tsx` | App.tsx 含路由定义 + 守卫 + 全局 Layout + auth:expired 监听 |
| 全局样式 | `src/index.css` | `@import "tailwindcss"` + `@plugin "daisyui"`；`@theme` 深蓝+金色品牌变量；`.glass-card`/`.gold-gradient` 等装饰类（见 web-front-ui-aesthetic skill，缺失则已复用组件样式失效） |
| API 封装 | `src/api/client.ts` + `src/api/modules/`（qa/auth/config/models/feedback/importApi/tts） | 按后端契约封装（TS 标注入参/返回值），页面禁止裸调 axios |
| 契约类型 | `src/types.ts` | TS `interface`/`type`，对齐后端 QaAskResp（§5.2） |
| 状态 | `src/store/`（useSessionStore.ts/useConfigStore.ts/useModelStore.ts） | Zustand；启动期拉取的 store 遵循 store-init-pattern（hydration 感知 + 防重锁） |
| 登录 | `src/pages/Login.tsx` | 深色 Hero（网格点阵+金色辉光）+ 金色 CTA（`.btn-gold`） |
| 布局 | `src/components/Layout/`（Sidebar.tsx/Header.tsx） | 侧边栏4页入口 + 顶栏 + 二级页面包屑（复用 `Breadcrumb`，"系统管理 / 应用配置"等，对齐原型） |
| 问数 | `src/pages/Qa.tsx` | 会话侧栏 + 欢迎页 + 聊天 + 输入栏装配 |
| 问数组件 | `src/features/qa/`（SessionList.tsx/Welcome.tsx/ChatMessage.tsx/AiCard.tsx/InputBar.tsx/SourcePicker.tsx/QuickAsk.tsx/ImportDialog.tsx/TtsButton.tsx） | 见 §5 |
| 图表 | `src/features/qa/charts/`（Bar/Line/Pie/index.tsx） | ECharts 封装，4 类图 |
| 配置页 | `src/pages/config/AppConfig.tsx`、`src/pages/config/ModelConfig.tsx` | 6 张卡片 + 模型 CRUD |
| 反馈页 | `src/pages/Feedback.tsx` | 回复校对列表 + 详情/处理 |

### 4.3 修改清单

| 修改项 | 文件 | 由 → 到 |
|---|---|---|
| 无 | - | - |

### 4.4 删除清单

| 删除项 | 位置 | 原因 | 替代 |
|---|---|---|---|
| 无 | - | 全新前端 | - |

## 5. 详细执行契约（代码优先）

### 5.1 axios 客户端（`src/api/client.ts`）

```ts
import axios from 'axios'
import type { AxiosError } from 'axios'

export const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000,
})

// 401 → 未登录/过期
http.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(err)
  }
)
```

登录态约定：`localStorage['jg_login'] = '1'` 仅作"意向"标记，**真正校验以后端 `/api/auth/check` 为准**；服务端过期返回 401 时强制跳登录。API 函数与页面组件**无需显式传任何认证参数**；后端返回业务 JSON，无 `{code,message,data}` 包装，`res.data` 即业务数据。

### 5.2 数据契约（`src/types.ts`，TS interface，对齐后端 QaAskResp）

```ts
export interface Step { title: string; desc: string; done: boolean }
export interface Chart {
  type: 'bar' | 'bar_h' | 'pie' | 'line'
  title: string
  unit?: string
  series: number[]
  x: string[]
  legend?: string[]
}
export interface QaAskResp {
  session_id: string  // id 一律 string（mongo-store idPrefix，如 QS0001）
  steps: Step[]
  findings: string[]
  columns: string[]
  rows: (string | number)[][]
  stats: { count: number; avg: number; max: number; max_of: string; min: number; min_of: string }
  chart: Chart | null
  text: string
  follow_ups: string[]
  meta: { elapsed_s: number; tokens: number }
}
export interface SessionItem { id: string; title: string; pinned: boolean; userName: string; msgCount: number; updatedAt: string }
export interface MsgItem { id: string; role: 'user' | 'ai'; content: string; aiMeta?: QaAskResp }
export interface DataSourceGroup {
  group: string
  items: { key: string; name: string; label?: string; group: string; selected: boolean }[]
}
```

### 5.3 路由与守卫（`src/App.tsx`）

```tsx
// 路由定义与守卫都在 App.tsx：
// /login、/qa（默认页）、/config/app、/config/model、/feedback
// 守卫：无本地登录态 且 首屏接口 401 → 跳 /login
// useEffect 监听 'auth:expired' 事件 → 清态 + 跳 /login + useSnackbar 提示
```

### 5.4 UI 组件对照（daisyUI/Tailwind，禁 antd）

| 功能 | 方案（原 antd 思路 → 本项目实现） |
|---|---|
| 按钮 | `btn btn-primary/btn-outline/btn-ghost/btn-sm`，**全部加 `whitespace-nowrap`**；金色 CTA 用 `.btn-gold` |
| 输入/下拉/文本域 | `input/select/textarea` + `input-bordered w-full`；与按钮同行时输入框 `flex-1`（禁 w-full 挤出按钮） |
| 弹窗 | daisyUI `<dialog className="modal modal-open"><div className="modal-box">`；删除/操作确认统一用 `ConfirmDialog` |
| 全局提示 | `useSnackbar` + `SnackbarAlert`（保存成功/失败反馈） |
| 折叠（AI 分析过程） | `collapse collapse-arrow bg-base-100 border border-gray-200 rounded-xl`，默认收起 |
| 表格 | `<table className="table">` + `overflow-x-auto`；动态列以内容自适应 + 总 minWidth 兜底；列表页表格按 web-front-10 设置列宽与换行 |
| 分页 | `CustomTablePagination`（禁手写） |
| 搜索筛选 | `SearchFilter`（fields 配置 text/select/date）；回复校对、导入记录等列表页**必须**用它，禁手写内联筛选 |
| 加载 | `LoadingOverlay` / `TableSkeleton` / `loading loading-spinner` |
| 空态 | 表格用 `EmptyTableRow`；欢迎页等用引导性空态 |
| 开关/复选 | `toggle toggle-primary` / `checkbox checkbox-primary` |
| 卡片 | 亮色：`bg-white rounded-2xl shadow-sm border border-gray-200 p-6`；卡片悬浮 `.card-hover` |
| 标签 | `badge badge-ghost/badge-success/badge-error`（状态：成功绿/失败红/处理中金） |
| 面包屑 | 复用 `Breadcrumb` |
| 图标 | lucide-react，`size={16/20/24}`，禁 emoji |

视觉基调按 web-front-ui-aesthetic：亮色页面背景（`#f8fafc`）+ 深蓝金色点缀；登录页深色 Hero（`#0f172a`）；深色背景文字用 `text-white/85`、`text-white/50`；金色仅作点缀（Logo/高亮数据/CTA）；禁纯黑、禁外部图片、装饰纯 CSS。

### 5.5 智能问数装配（`pages/Qa.tsx` 数据流）

- 选中会话 → 载入 `GET /qa/sessions/{id}/messages` 渲染；新会话空态显示 `<Welcome/>`
- 发送问题 → 两种模式：
  - **一次性**：`POST /api/qa/ask` 返回 `QaAskResp` → 追加 ai 消息（AiCard 渲染）→ 更新会话列表；请求耗时长，输入栏/卡片用 `loading loading-spinner` 占位防重复提交
  - **流式（增强）**：SSE 逐步推 5 步状态 + 最终结果（后端若实现则用 EventSource；首版仅一次性）
- 快捷问题 / 收藏问题点击 → 直接填入并发送
- 数据源勾选 → 存入 localStorage `jg_sources`，随请求 `source_keys` 上报

**AI 消息卡片（`AiCard.tsx`）渲染 `QaAskResp`（自上而下，白底圆角卡片，段间距 16~20px）**：

```
① 分析过程 <collapse collapse-arrow> 默认收起：5×Step(title/desc done=✓ 用 lucide Check 图标)
② 数据发现 findings 列表（无序列表即可，不引组件库）
③ 数据表格 <table className="table"> + overflow-x-auto；行数>200 顶部提示"共N条已截断"
④ 数据统计 记录数/均值/最大值(含归属)/最小值(含归属)；数值 font-extrabold
⑤ 数据可视化 <Chart type=chart.type>；图例+单位(unit)
⑥ 页脚：复制(整卡文本)/反馈(daisyUI modal 提交)/语音播报(TTS,受配置开关)/ 耗时·Tokens·时间戳(dayjs YYYY-MM-DD HH:mm)
⑦ 追问 chips：3×follow_ups，rounded-full，点击即发送
```

**AI 回复文本（`QaAskResp.text`）必须用 `MarkdownView` 组件渲染**（内部 react-markdown + remark-gfm + dompurify），禁止手写 markdown 配置。

**用户消息气泡（`ChatMessage.tsx`）操作按钮**：收藏(Star 图标,金色高亮)/编辑(文本域+取消·重新发送)/重新发送/复制；操作反馈用 useSnackbar。

### 5.6 图表组件（`features/qa/charts/index.tsx`）

```tsx
const chartOpt = { bar: (d)=>({type:'bar',yAxis:{type:'value'}}), bar_h: (d)=>({type:'bar',xAxis:{type:'value'}}),
  pie: (d)=>({type:'pie', data: d.pieData}), line: (d)=>({type:'line'}) };
// echarts-for-react <ReactECharts option={...} style={{height:320}} />；统一 tooltip/legend/主题
```

4 类映射：柱状=bar、条形=bar_h、饼=pie（加 itemStyle 半径）、折线=line（数据>=2 点才渲染线）。配色与品牌色板一致（深蓝 `#1a3a6c`/`#2c5282` + 金 `#d4af37`/`#b48a32`）。

### 5.7 会话管理侧栏（`SessionList.tsx`）

- 侧栏可收起/展开（**默认收起**，对齐原型 qaSidebar collapsed；侧栏内按钮与问数页顶栏按钮均可切换）；发送首条消息时主侧边栏自动收起（对齐原型 sendChat 行为）
- `GET /qa/sessions` 渲染，置顶(pinned)排前；`POST /qa/sessions` 新建；`PATCH /qa/sessions/{id}` 置顶/重命名；`DELETE /qa/sessions/{id}` 删除（级联消息）
- 自动命名：后端负责（首条用户消息前 20 字）；前端新会话标题显示"新对话"
- 条目省略号菜单：置顶/取消置顶、重命名(daisyUI modal+input)、删除(`ConfirmDialog`)
- 时间显示 dayjs `YYYY-MM-DD HH:mm`

### 5.8 欢迎页（`Welcome.tsx`）

品牌标题"你好/我是经管之星·AI问数助手"固定（原型 h1/h2，衬线标题+金色点缀）；副文案与推荐问题网格**从后端应用配置拉取**（`GET /config` → `greeting.text` + `greeting.questions[]`；配置弹窗对齐原型 greetingConfigModal：单 textarea + 问题列表增删、上限 10 条），不是硬编码；**默认 3 条对齐原型 appConfig**（各产品线销售情况 / 北京的产品线收入情况 / 深圳的产品销售情况），网格两列排布（`grid grid-cols-1 md:grid-cols-2 gap-4`）。点击推荐项 → 直接发送。

### 5.9 快捷提问（`QuickAsk.tsx`）

闪电图标弹 daisyUI dropdown/modal 面板两 Tab（`tabs tabs-bordered`）：**常问**（`GET /api/qa/quick-asks`：`hit ≥ 频次阈值` 的问题按热度降序，冷启动回退后端预置 2 条常问（"政企行业收入3000万-5000万数据"/"北京代表处今年达成情况"，对齐原型 `_QQ_DATA.recent`）；`enabled=false` 整 Tab 隐藏；语义见后端文档 §4.6.1）/ **收藏**（本地 localStorage 收藏问题，可移除）。chips 用 `rounded-full`，点击即发送。

> 取舍说明：收藏问题仅存前端 localStorage（演示级取舍，换浏览器/清缓存会丢，属预期行为）；后端不建收藏模型。

### 5.10 数据源选择（`SourcePicker.tsx`）

`GET /qa/sources` → 按组多选（台账/统计报表，`checkbox checkbox-primary`）；条目有 `label` 副标题时显示（如"整体达成"→"中国区整体及各经营单元达成"，对齐原型）；显示"已选 N 个数据源 / 已选择所有数据源"；全选/全不选；选择持久化 localStorage。

### 5.11 输入栏（`InputBar.tsx`）

- Enter 发送、Shift+Enter 换行、空内容禁发；`textarea textarea-bordered`，发送按钮 `btn btn-primary whitespace-nowrap`
- 闪电(快捷提问)、麦克风(**STT 开关**开才可用，否则占位禁点；与 §5.12 stt 配置一致)、数据源选择、发送按钮；全部 lucide-react 图标

### 5.12 应用配置页（`AppConfig.tsx`，6 张卡片）

| 卡片 | 开关→配置项 | 持久化 key |
|---|---|---|
| 对话开场白 | 开场白文案 textarea + 开场问题列表(增删，≤10 条) | greeting |
| 下一步问题建议 | 追问 chips 显隐 | suggestions |
| 文字转语音 | 页脚语音播放可用性 | tts |
| 语音转文字 | 输入栏麦克风可用性 | stt |
| 模型配置 | 点击跳 `/config/model` | modelConfig |
| 常问设置 | 问题频次阈值（次，≥阈值视为常问；对齐原型 hotConfigModal） | hotRecommend |

卡片样式 `bg-white rounded-2xl shadow-sm border border-gray-200 p-6`；开关用 `toggle toggle-primary`。GET/PUT `/config`；配置全局生效、即时生效（切回即用新值）。

### 5.13 模型配置页（`ModelConfig.tsx`）

- 应用模型设置：启用模型下拉（`select select-bordered`）+ 保存（`btn btn-primary whitespace-nowrap`）
- 新增模型弹窗（daisyUI modal）：**仅 3 个必填项** baseUrl/apiKey/modelName（OpenAI 兼容；对齐原型无 name 输入，name 由后端自动生成）；`GET/POST/DELETE /api/models`
- **测试连接**：`POST /api/models/test` 发一次最小请求验证连通；测试通过前"添加"按钮禁用（对齐原型 mcTestConnection）
- apiKey 出参已脱敏（`sk-***`），前端不做回填
- DeepSeek 为默认启用项（后端保证）

### 5.14 回复校对页（`Feedback.tsx`）

- 筛选：**必须用 `SearchFilter` 组件**（问题搜索 text / 用户搜索 text / 状态 select：全部/待处理/已处理）
- 列表：`table` + 列宽规范（主文本列 `min-w-[140px] max-w-[260px] whitespace-normal break-words`，时间列 `w-[160px]`，操作列 `w-[100px]`）；`CustomTablePagination` 分页 5/10 条；刷新按钮（Refresh 图标 + Tooltip"刷新"）
- 查看详情弹窗（daisyUI modal：原问题+AI回复(`MarkdownView`)+用户描述）+ 写备注 + 标记已处理：`GET /api/feedback`、`PUT /api/feedback/{id}`

### 5.15 台账导入（`ImportDialog.tsx`）

- 入口：数据源弹窗内"导入 + 导入记录"
- 上传控件：无封装上传组件，用 daisyUI 基础方案——`<label className="btn btn-primary cursor-pointer whitespace-nowrap"><Upload size={20}/>选择文件<input type="file" className="hidden" onChange={...}/></label>`；FormData 走 http 实例（Cookie 认证，无需 token），上传中按钮 loading 防重复提交；结果用 useSnackbar 反馈
- 下载模板：`GET /api/import/template?type=commercial|ppl|goal` 下载对应 xlsx 模板（列定义与后端解析共用）
- 年份选择弹窗：daisyUI select 选年份(2025/2026) + 统计截止日期(商业需) + 上传 xlsx + 确认
- `POST /api/import/upload`（multipart）；导入记录 `GET /api/import/log`（`SearchFilter` type 过滤 + `CustomTablePagination` 分页；`EmptyTableRow`/`TableSkeleton` 空态加载态）
- 结果状态：成功 / 失败-原因 / 部分成功 → badge（绿/红/金）+ 顶部提示

### 5.16 语音（`features/qa/TtsButton.tsx`）

- 受 `tts` 配置开关控制；`POST /api/tts {text}` 返回音频流，`<audio controls autoplay/>` 播放、可停止
- TTS 网络失败降级提示（useSnackbar），不阻断主流程
- STT（语音转文字）首版仅占位禁用（stt 开关关闭默认）

## 6. 执行步骤

| 步骤 | 状态 | 详细说明 |
|---|---|---|
| 1. 工程骨架 | [ ] 待处理 | **做什么**：搭 Vite + React19 + TS 骨架。**注意 `web-front/src/components|hooks|utils` 已存在（原为 JSX），禁止覆盖/删除，须统一转换为 `.tsx`/`.ts` 并补充类型**（可先在临时目录 `npm create vite@latest` 生成 `--template react-ts` 后合并，或直接手工落盘根文件）。装依赖：axios/echarts/echarts-for-react/zustand/dayjs/react-markdown/remark-gfm/dompurify/lucide-react + dev：typescript/@types/react/@types/react-dom/tailwindcss@4/@tailwindcss/vite/daisyui@5。`vite.config.ts` 接入 `@tailwindcss/vite` 插件 + server.proxy `/api→process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'`（本地联调允许**临时**起后端进程，用完即停，非常驻/不开自启/不装 pm2；长期联调指向服务器 nginx）。`tsconfig.json` 开 strict。`src/index.css` 落 `@theme` 品牌变量与 `.glass-card`/`.gold-gradient` 等装饰类。<br>**验证**：`npm run dev` 起默认页且 daisyUI 样式/品牌变量生效；`npx tsc --noEmit` 零错误（含已转换组件） |
| 2. api 层+契约 | [ ] 待处理 | `src/api/client.ts` + `src/api/modules/` 各模块（TS 标注入参/返回值） + `src/types.ts` 契约（§5.1/5.2）。<br>**验证**：`npx tsc --noEmit` 零错误，`npm run build` 通过 |
| 3. 布局+路由+登录 | [ ] 待处理 | `Layout/` + `App.tsx` 路由守卫 + `Login.tsx`（§5.3；深色 Hero + `.btn-gold`）。<br>**验证**：`tsc --noEmit` + `npm run build` 通过；手动触发 401 见跳登录 |
| 4. 会话+问数装配 | [ ] 待处理 | `Qa.tsx` + `SessionList/Welcome/InputBar`（§5.5/5.7/5.8/5.11）。<br>**验证**：`tsc --noEmit` 零错误；能新建/切换会话、发消息收到 QaAskResp |
| 5. AI卡片+图表 | [ ] 待处理 | `AiCard.tsx` + `charts/` + `MarkdownView` 渲染 + 统计/追问/页脚（§5.5/5.6）。<br>**验证**：`tsc --noEmit` 零错误；四个原型问题渲染出表格+对应图表类型 |
| 6. 消息操作+快捷 | [ ] 待处理 | `ChatMessage` 收藏/编辑/重发/复制 + `QuickAsk`（§5.9）。<br>**验证**：收藏进收藏Tab、编辑重发替换 |
| 7. 数据源+导入 | [ ] 待处理 | `SourcePicker` + `ImportDialog`（§5.10/5.15）。<br>**验证**：勾选随请求上报；导入后数据可见 |
| 8. 配置页 | [ ] 待处理 | `AppConfig` + `ModelConfig`（§5.12/5.13）。<br>**验证**：改开场白新会话生效；加模型可切换 |
| 9. 反馈页 | [ ] 待处理 | `Feedback`（§5.14，SearchFilter + CustomTablePagination）。<br>**验证**：反馈提交→列表出现→标记已处理 |
| 10. 语音+打磨 | [ ] 待处理 | `TtsButton` + STT 占位 + UI 基调走查（ui-aesthetic）+ 空态/异常兜底（§5.16）。<br>**验证**：TTS 开/关行为正确；无控制台报错 |
| 11. 端到端联调 | [ ] 待处理 | 与后端+nginx 联调：登录→7 个示例问题→全部渲染正常。<br>**验证**：7/7 通过；401 过期跳登录；降级提示可用 |

## 7. 实施顺序

| 阶段 | 内容 | 依赖 |
|---|---|---|
| A 底座 | 步骤 1-3（骨架/api/布局/登录） | 无 |
| B 核心体验 | 步骤 4-7（问数/AI卡/图表/操作/导入） | A |
| C 管理端 | 步骤 8-9（配置/反馈） | B |
| D 增强 | 步骤 10-11（语音/打磨/联调） | C |

## 8. 禁止事项

❌ **禁止引入 antd / MUI**（与 Tailwind + daisyUI 冲突）；禁止引入与已复用通用组件功能重复的组件库
❌ **禁止新建 `.js`/`.jsx`**（统一 `.ts`/`.tsx`；已复用组件同步转 TSX 并补类型；避免 `any`）
❌ **禁止 emoji 替代图标**（全部 lucide-react，`strokeWidth={1.5}`）
❌ 禁止手写内联搜索筛选（必须 `SearchFilter`）、手写分页（必须 `CustomTablePagination`）、手写 AI 文本 markdown 配置（必须 `MarkdownView`）
❌ 禁止按钮文字换行（全部 `whitespace-nowrap`）；禁止表格不设 minWidth/列宽
❌ 不把 nginx 登录逻辑做进前端（只做 401 响应跳转；鉴权归 nginx+后端）
❌ 不在前端存储/回显模型 API Key、管理员密码等敏感值
❌ 不硬编码欢迎文案/推荐问题/维度枚举（一律后端配置/接口返回）
❌ 不写组件导出的过渡方案（无占位残留代码替换正式功能）
❌ 不在前端假数据兜底（必须接后端真实返回；接口未就绪时报错提示，不 mock）

## 9. 注意事项

1. axios 必须 `withCredentials: true`，否则登录 Cookie 不随请求上传
2. ECharts 4 类图仅渲染后端 `chart.type` 指定类型；`pie` 需 ECharts 转换 `{name,value}`，`bar_h` 交换 x/y 轴
3. AI 消息 `aiMeta` 是还原卡片的唯一来源，渲染失败时降级为纯文本 `content`
4. 会话列表排序与自动命名由后端负责，前端不重复实现
5. 步骤完成即勾 `[x]`，文件名前缀随进度改 `处理中-/**已完成-**`
6. 原型问数页存在"日志"视图与会话详情面板（demo L925-947、qaDetailPanel），但**无任何导航入口**（残留代码）；按需求 §5.1 精神首版不做页面，后端 `GET /api/qa/log` 接口保留备用
7. 全工程 **TypeScript（strict）**；每步完成线 = `npx tsc --noEmit` 零错误 + `npm run build` 零错误 + ESLint 无 error + 自审（web-front-feature-workflow §3.2：样式方案/日期格式化/SearchFilter/分页/图标五项检查）
8. Store 涉及启动期拉数据（会话列表/数据源分组/应用配置）时，遵循 store-init-pattern：`fetchMethod` 防重锁 + `initMethod` hydration 感知，组件一行 `useEffect` 调用

