import { http } from '../client'
import type { FeedbackItem } from '../../types'

export const feedbackApi = {
  create: (data: { sessionId?: string; question: string; answer: string; description: string }) =>
    http.post<FeedbackItem>('/feedback', data),
  list: (params: { page: number; pageSize: number; search?: string; status?: string }) =>
    http.get<{ items: FeedbackItem[]; total: number }>('/feedback', { params }),
  update: (id: string, data: { status: string; remark: string }) =>
    http.put<{ ok: boolean }>(`/feedback/${id}`, data),
}
