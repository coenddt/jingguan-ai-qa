/** 台账导入域纯业务函数（ImportDialog 上传与分页拉取） */

import { importApi } from '../api/modules/importApi'
import type { ImportLogItem, PagedQuery } from '../types'

export interface ImportUploadResult {
  ok: boolean
  status: string
  success: number
  total: number
  errors: string[]
}

/** 上传台账文件，返回导入结果 */
export async function uploadLedger(file: File, type: string, year: number): Promise<ImportUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await importApi.upload(form, { type, year })
  return data
}

export async function fetchImportLogPage({ page, pageSize }: PagedQuery): Promise<{ items: ImportLogItem[]; total: number }> {
  const { data } = await importApi.listLog({ page: page + 1, pageSize })
  return data
}

