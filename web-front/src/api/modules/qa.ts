import { http } from '../client'
import type { DataSourceGroup, MsgItem, QaAskResp, SessionItem } from '../../types'

export const qaApi = {
  listSessions: () => http.get<SessionItem[]>('/qa/sessions'),
  createSession: (title: string) => http.post<{ id: string; title: string }>('/qa/sessions', { title }),
  patchSession: (id: string, data: { pinned?: boolean; title?: string }) =>
    http.patch<{ ok: boolean }>(`/qa/sessions/${id}`, data),
  deleteSession: (id: string) => http.delete<{ ok: boolean }>(`/qa/sessions/${id}`),
  listMessages: (id: string) => http.get<MsgItem[]>(`/qa/sessions/${id}/messages`),
  ask: (data: { question: string; session_id?: string | null; source_keys: string[] }) =>
    http.post<QaAskResp>('/qa/ask', data),
  getSources: () => http.get<DataSourceGroup[]>('/qa/sources'),
  getQuickAsks: () => http.get<{ enabled: boolean; hot: { question: string; hit: number }[] }>('/qa/quick-asks'),
}
