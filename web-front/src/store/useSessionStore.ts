import { create } from 'zustand'
import { qaApi } from '../api/modules/qa'
import type { SessionItem } from '../types'

interface SessionStore {
  sessions: SessionItem[]
  loaded: boolean
  loading: boolean
  fetchMethod: () => Promise<void>
}

/** 会话列表（启动期拉取遵循 store-init-pattern：防重锁） */
export const useSessionStore = create<SessionStore>((set, get) => ({
  sessions: [],
  loaded: false,
  loading: false,
  fetchMethod: async () => {
    if (get().loading) return
    set({ loading: true })
    try {
      const { data } = await qaApi.listSessions()
      set({ sessions: data, loaded: true })
    } finally {
      set({ loading: false })
    }
  },
}))
