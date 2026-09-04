import { http } from '../client'
import type { ModelItem } from '../../types'

/** LLM 平台预设（与后端 services/llm_client PLATFORM_PRESETS 对齐；baseUrl 留空即用平台预设） */
export const LLM_PLATFORMS = [
  { value: 'deepseek', label: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1' },
  { value: 'volcengine', label: '火山引擎方舟', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3' },
] as const

export interface ModelPayload {
  platform: string
  baseUrl: string
  apiKey: string
  modelName: string
}

export const modelsApi = {
  list: () => http.get<ModelItem[]>('/models'),
  add: (data: ModelPayload) => http.post<ModelItem>('/models', data),
  remove: (id: string) => http.delete<{ ok: boolean }>(`/models/${id}`),
  enable: (id: string, enabled: boolean) => http.patch<{ ok: boolean }>(`/models/${id}`, { enabled }),
  test: (data: ModelPayload) =>
    http.post<{ ok: boolean; latency_ms?: number; error?: string }>('/models/test', data),
}
