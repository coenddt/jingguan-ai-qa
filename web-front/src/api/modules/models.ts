import { http } from '../client'
import type { ModelItem } from '../../types'

export const modelsApi = {
  list: () => http.get<ModelItem[]>('/models'),
  add: (data: { baseUrl: string; apiKey: string; modelName: string }) => http.post<ModelItem>('/models', data),
  remove: (id: string) => http.delete<{ ok: boolean }>(`/models/${id}`),
  enable: (id: string, enabled: boolean) => http.patch<{ ok: boolean }>(`/models/${id}`, { enabled }),
  test: (data: { baseUrl: string; apiKey: string; modelName: string }) =>
    http.post<{ ok: boolean; latency_ms?: number; error?: string }>('/models/test', data),
}
