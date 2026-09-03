import { http } from '../client'
import type { ImportLogItem } from '../../types'

export const importApi = {
  downloadTemplate: (type: string) =>
    http.get<Blob>('/import/template', { params: { type }, responseType: 'blob' }),
  upload: (form: FormData, params: { type: string; year: number }) =>
    http.post<{ ok: boolean; status: string; success: number; total: number; errors: string[] }>(
      '/import/upload', form, { params }),
  listLog: (params: { page: number; pageSize: number; type?: string }) =>
    http.get<{ items: ImportLogItem[]; total: number }>('/import/log', { params }),
}
