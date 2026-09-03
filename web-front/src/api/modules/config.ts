import { http } from '../client'
import type { AppConfig } from '../../types'

export const configApi = {
  get: () => http.get<AppConfig>('/config'),
  put: (data: Partial<AppConfig>) => http.put<AppConfig>('/config', data),
}
