---
name: "store-init-pattern"
description: "web-front Zustand persist store 初始化模式：hydration 感知、防重锁、可选防抖。实现应用启动期拉取数据且每次刷新只执行一次的 store 方法时调用。"
---

# Store Init Pattern（web-front/）

## Problem

When using `zustand/middleware/persist` (especially with `sessionStorage`), page refresh restores **stale** data from storage. The store never re-fetches fresh data from the server, so user info, permissions, or any server-side changes don't take effect until next login.

## Solution Overview

Three-layer initialization pattern:

```
useEffect → initMethod() → hydration wait → fetchMethod() → update store
  (component)   (store)          (persist)      (store)        (store)
```

Each layer has single responsibility:

| Method | Where | Responsibility |
|--------|-------|---------------|
| `fetchMethod` | Store action | API call + dedup guard (防重锁 / 防抖) |
| `initMethod` | Store action | Wait for persist hydration, then trigger fetch. Returns cleanup function. |
| `useEffect` | Component | One-liner to kick off init. Cleanup handled by `initMethod` return. |

## Implementation

### 1. Store: `fetchMethod` with dedup guard

Use an IIFE closure with a `pending` lock to prevent concurrent duplicate calls:

```js
const useStore = create(
  persist(
    (set, get) => ({
      // ...state fields...

      /** 获取最新数据（防重锁版本 —— 适合页面初始化场景） */
      fetchData: (() => {
        let pending = false
        return async () => {
          if (pending) return     // 已有请求在跑，跳过
          pending = true

          try {
            const res = await http.get('/path/to/data')   // src/api/client.ts 实例
            set({ ...extractFields(res.data) })
          } finally {
            pending = false
          }
        }
      })(),

      /** 应用初始化：等 hydration 完成后调用 fetch */
      initData: () => {
        const doFetch = () => get().fetchData()

        if (useStore.persist?.hasHydrated?.()) {
          doFetch()
          return () => {}
        }

        const unsub = useStore.persist?.onFinishHydration?.(doFetch)
        return () => { unsub?.() }
      },
    }),
    { name: 'store-key', storage: createJSONStorage(() => sessionStorage) }
  )
)
```

### 2. Component

```jsx
useEffect(() => useStore.getState().initData?.(), [])
```

That's it. The effect returns the cleanup function returned by `initData`, which React calls on unmount to unsubscribe.

## Dedup Variants

### Variant A: Pending Lock (默认)

Use when:
- 只需要防止并发重复请求
- 请求是同步触发的（如页面初始化）
- 不需要等待"安静了再请求"

```js
let pending = false
return async () => {
  if (pending) return
  pending = true
  try { ... }
  finally { pending = false }
}
```

### Variant B: Debounce (防抖)

Use when:
- 需要在用户停止操作后才发起请求
- 可能被高频事件触发（resize、scroll、input）
- 希望合并多次触发为一次请求

```js
let timer = null
return (...args) => {
  clearTimeout(timer)
  return new Promise((resolve) => {
    timer = setTimeout(async () => {
      try {
        const res = await http.get('/path/to/data', ...args)
        set({ ...extractFields(res.data) })
        resolve(res)
      } catch (err) {
        resolve(null)
      }
    }, 300) // 防抖窗口 300ms
  })
}
```

### Variant C: Once (只执行一次)

Use when:
- 需要在应用生命周期内只执行一次，无论触发多少次
- 类似 `useEffect([], [])` 但更安全

```js
let executed = false
return async () => {
  if (executed) return
  executed = true
  try { ... }
  catch { ... }
}
```

## 本项目适用场景

- 会话列表 store（启动期拉取 `/api/qa/sessions`）
- 数据源分组 store（启动期拉取 `/api/qa/sources`）
- 应用配置 store（启动期拉取 `/api/config`）

## FAQ

**Q: 为什么要把 cleanup 放在 `initMethod` 返回值里，而不是在组件里处理？**
- 因为组件不需要关心内部实现细节。`initMethod` 自己知道需不需要 unsubscribe，返回一个空函数或真实的 cleanup 函数，由 React useEffect 统一调用。

**Q: 防抖和 pending 锁能同时用吗？**
- 可以。先防抖合并高频触发，防抖执行时再用 pending 锁防止并发。

**Q: 认证注意？**
- 请求统一走 `src/api/client.ts` 的 http 实例（Cookie 认证），401 会被全局拦截跳登录，store 内无需处理。
