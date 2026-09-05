/** 从类 axios 错误中提取后端 detail 文案（无则返回 undefined） */
export function getApiErrorMsg(e: unknown): string | undefined {
  return (e as { response?: { data?: { detail?: string } } } | undefined)?.response?.data?.detail
}

/** 从任意抛出值提取用户可读错误文案：优先后端 detail，其次普通 Error.message（含 SSE 流内 error 事件 message 透出） */
export function getErrorMessage(e: unknown): string | undefined {
  return getApiErrorMsg(e) ?? (e instanceof Error ? e.message : undefined)
}
