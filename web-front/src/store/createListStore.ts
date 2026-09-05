/** Zustand 列表 store 工厂：items/loaded/loading + 防重锁（store-init-pattern Variant A），
 *  useSessionStore / useModelStore 同构模板收敛于此
 *  防重语义：仅防重锁（if(get().loading) return），不防重取——列表需在操作（置顶/重命名/删除）
 *  后调用 fetchMethod 强制刷新（见 useSessionActions）。区别于 useConfigStore 的单对象防重取。 */

import { create } from 'zustand'

export interface ListStore<T> {
  items: T[]
  loaded: boolean
  loading: boolean
  fetchMethod: () => Promise<void>
}

export function createListStore<T>(fetcher: () => Promise<T[]>) {
  return create<ListStore<T>>((set, get) => ({
    items: [],
    loaded: false,
    loading: false,
    fetchMethod: async () => {
      if (get().loading) return
      set({ loading: true })
      try {
        const items = await fetcher()
        set({ items, loaded: true })
      } finally {
        set({ loading: false })
      }
    },
  }))
}
