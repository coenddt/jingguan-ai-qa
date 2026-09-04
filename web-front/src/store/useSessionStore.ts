import { qaApi } from '../api/modules/qa'
import type { SessionItem } from '../types'
import { createListStore } from './createListStore'

/** 会话列表（启动期拉取遵循 store-init-pattern：防重锁） */
export const useSessionStore = createListStore<SessionItem>(async () => {
  const { data } = await qaApi.listSessions()
  return data
})
