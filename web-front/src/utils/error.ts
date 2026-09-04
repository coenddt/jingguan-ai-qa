/** 从类 axios 错误中提取后端 detail 文案（无则返回 undefined） */
export function getApiErrorMsg(e: unknown): string | undefined {
  return (e as { response?: { data?: { detail?: string } } } | undefined)?.response?.data?.detail
}
