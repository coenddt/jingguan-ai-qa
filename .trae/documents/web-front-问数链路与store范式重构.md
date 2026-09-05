# web-front 问数链路与 store 范式重构计划

## Context（为什么改）

上次代码结构审查结论：web-front 分层与规范落地优秀（未达"极致"），集中在 3 个范式/架构偏离点。本次仅做这三项，均不改变行为，纯工程收敛：

1. **usePagedList 渲染期写 ref**：`stateRef.current = {...}` 写在渲染函数体内，属 React 明令禁止的 render-phase mutation，StrictMode/并发下存在隐患。
2. **store 防重锁/防重取语义不清晰**：`createListStore` 与 `useConfigStore` 各自的 `fetchMethod` 防重语义不同且无注释，易被误用。
3. **问数 `send` 走 window 全局事件总线**：`dispatchQaAsk`/`onQaAsk` 用 `CustomEvent` 跨层通信，弱类型、打破单向数据流、来源不可追踪。

目标：消除渲染期 ref 写、统一 store 语义并澄清、把追问链路收敛为 React Context 单向数据流，全部行为等价。

---

## 改动 1：usePagedList 消除渲染期 ref 写

文件：`web-front/src/hooks/usePagedList.ts`

把渲染期 `stateRef.current = { page, rowsPerPage, filters }` 移入 `useEffect`，保持动作引用稳定（空依赖数组不变，调用方作为 useEffect 依赖的使用方式不受影响）：

```ts
const stateRef = useRef({ page, rowsPerPage, filters })
useEffect(() => {
  stateRef.current = { page, rowsPerPage, filters }
}, [page, rowsPerPage, filters])
```

- `load` 仍显式传实参；`search/reset/changePage/changeRowsPerPage/refresh` 逻辑不变。
- **安全性论证**：动作（search/changePage 等）先 `setState` 再 `load`，load 用的是显式实参；`refresh` 读取 `stateRef` 时组件已 re-render 到新状态、useEffect 已同步，读到的即为最新值。无过期路径。
- 需补 `import { useEffect }`（当前文件只用 useCallback/useRef/useState）。

验证：`npx tsc --noEmit` 零错误；分页可达性（翻页/改每页条数/搜索/重置/刷新）行为与重构前一致。本文件不产生依赖改动，无全局回归。

---

## 改动 2：createListStore / useConfigStore 语义澄清

关键修正：上次审查把两者差异当作"需统一"——**经核实形态不同、不应强行统一**：
- `useSessionStore`/`useModelStore` 是**列表**（items: T[]），需要"置顶/重命名/删除后强制重取"（见 `useSessionActions` 内多处 `await fetchSessions()`），因此 `createListStore.fetchMethod` 用"**仅防重锁、不防重取**"（`if (get().loading) return`）是**正确**的——若加 `loaded` 短路会把强制刷新改坏（破坏性变更）。
- `useConfigStore` 持有**单个 config 对象**（非列表），一次性拉取，用"**防重锁 + 防重取**"（`if (get().loading || get().loaded) return`）也**正确**。

因此本次交付为**低风险澄清 + 可选增强**（默认仅补注释，不引入破坏性参数）：

1. 文件 `web-front/src/store/createListStore.ts`
   - 在 `fetchMethod` 上补注释，明确"防重锁、不防重取（调用方需在操作后调用以强制刷新）；区别于 useConfigStore 的防重取"。列出代表调用点 `useSessionActions`。
   - **可选增强**（如用户需要再启用）：为 `fetchMethod` 增加 `options?: { onError?: (e: unknown) => void }`，在 catch 内回调后**仍保留 **`throw`**，维持现有调用方 `.catch(() => showSnackbar(...))` 不变。

2. 文件 `web-front/src/store/useConfigStore.ts`
   - 在 `fetchMethod` 上补注释，说明"单对象一次性拉取，防重锁 + 防重取"。
   - 保持 `saveMethod` 不变。

> 不修改 `useSessionActions.ts`、`Qa/index.tsx`、`ModelConfig/index.tsx`、`QaLogView.tsx` 等调用方，零行为变化。

---

## 改动 3：问数 send 事件总线 → React Context（单向数据流）

### 现状链路（已探明）
- 发射方：仅 `features/qa/AiCard/AiFollowUps.tsx` 调 `dispatchQaAsk(f)`
- 订阅方：仅 `hooks/useQaChat.ts` L101 `useEffect(() => onQaAsk((q) => void send(q)), [send])`
- send 的其他 props 消费点：`Welcome onAsk`、`MessageList onResend → ChatMessage onResend`、`AiCard question`(非 send)

### 方案
新建 `web-front/src/features/qa/qaContext.tsx`：

```tsx
import { createContext, useContext } from 'react'

const AskContext = createContext<(q: string) => void>(() => {})
/** 问数发送统一入口：props 透传深、改用 context 单层下发 */
export const AskProvider = AskContext.Provider
export function useAsk() {
  return useContext(AskContext)
}
```

改动点：
- **`pages/Qa/index.tsx`**：`<AskProvider value={send}>` 包住主区（Welcome + MessageList 所在容器）；`MessageList` 删除 `onResend` prop、`Welcome` 删除 `onAsk` prop。
- **`hooks/useQaChat.ts`**：删除 `useEffect(() => onQaAsk(...))` 事件订阅（及 `onQaAsk` import）；`send` 正常返回给调用方供 Provider。
- **`services/qa.ts`**：删除 `QA_ASK_EVENT`/`dispatchQaAsk`/`onQaAsk` 三项；保留 `buildAiCardCopyText`。
- **`features/qa/AiCard/AiFollowUps.tsx`**：`dispatchQaAsk(f)` → `useAsk()(f)`。
- **`features/qa/Welcome.tsx`**：`{ onAsk }` prop → `const ask = useAsk()`，`onAsk(q)` → `ask(q)`。
- **`features/qa/MessageList.tsx`**：移除 `onResend` prop，组件内不再透传 `send`；`ChatMessage` 改为内部 `useAsk()`。
- **`features/qa/ChatMessage.tsx`**：`{ onResend }` prop → `const ask = useAsk()`；`resend`/`sendDraft` 调 `ask(...)`。
- `features/qa/AiCard/index.tsx`：`question` prop 保留（供 AiFeedbackModal），追问经 `AiFollowUps` 消费 useAsk，无需改。

> 用 context 而非 props 透传，是向 React 标准通路收敛、同时避免多层透传——正是原作者用事件总线的初衷，现在用更范式合规的方式实现。
> 注意：AskContext 默认值用空实现 `() => {}` 包裹兜底——若组件在 Provider 外使用会静默不发送。审查留存：该兜底不触发自动反馈（属 UI 层，可接受；如需严格可抛错，但此处从简）。

---

## 改动文件总览

| 文件 | 改动 |
|------|------|
| `src/hooks/usePagedList.ts` | ref 写入移入 useEffect（改动 1） |
| `src/store/createListStore.ts` | 补防重语义注释（改动 2，可选 onError） |
| `src/store/useConfigStore.ts` | 补防重语义注释（改动 2） |
| `src/features/qa/qaContext.tsx` | **新增** AskProvider/useAsk（改动 3） |
| `src/pages/Qa/index.tsx` | AskProvider 包裹 + 去 onAsk/onResend props |
| `src/hooks/useQaChat.ts` | 删事件订阅 |
| `src/services/qa.ts` | 删事件总线三项 |
| `src/features/qa/AiCard/AiFollowUps.tsx` | dispatchQaAsk → useAsk |
| `src/features/qa/Welcome.tsx` | onAsk prop → useAsk |
| `src/features/qa/MessageList.tsx` | 去 onResend 透传 |
| `src/features/qa/ChatMessage.tsx` | onResend prop → useAsk |

---

## 验证

本地（不改服务、不启动常驻）：
1. `npx tsc --noEmit` 零错误（每步提交底线，见 testing-rules）。
2. 改动 1：对 `usePagedList` 的 3 处使用（Feedback / ImportLogTable / 日志分页）走一遍翻页、改每页条数、搜索、重置、刷新。
3. 改动 3：构建 `npm run build` 通过；确认 json 内无 `qa:ask`/`dispatchQaAsk` 残留（`rg "dispatchQaAsk|onQaAsk|qa:ask"` 应为空）。
4. `git status` 收尾确认无 `tmp/` 残留、不提交 `.env`。

行为回归（改动 3 核心路径）：欢迎页快捷提问 → 发送 → 流式节奏卡 → 追问 chips 点击 → 同会话内发送新问题成功；多条消息 resend / 编辑重发正常。