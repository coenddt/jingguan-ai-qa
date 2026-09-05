import { http } from '../client'
import type { DataSourceGroup, MsgItem, SessionItem } from '../../types'

/** 后端 SSE 事件（session/steps/step/block/done/error） */
export interface QaStreamEvent {
  type: 'session' | 'steps' | 'step' | 'block' | 'done' | 'error'
  data?: unknown
  index?: number
  title?: string
  desc?: string
  status?: 'running' | 'done' | 'fail'
  name?: string
  message?: string
}

export type AskStreamHandler = (ev: QaStreamEvent) => void

/** 解析 SSE 字节流（data: {...}\n\n 帧） */
async function readSse(res: Response, onEvent: AskStreamHandler): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式读取')
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (line) onEvent(JSON.parse(line.slice(6)) as QaStreamEvent)
    }
  }
}

async function askStream(body: { question: string; session_id?: string | null; source_keys: string[] },
  onEvent: AskStreamHandler, signal?: AbortSignal): Promise<void> {
  const res = await fetch('/api/qa/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
    signal,
  })
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:expired'))
    throw new Error('登录已过期，请重新登录')
  }
  if (!res.ok) {
    let msg = '问数请求失败'
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : msg
    } catch { /* 非 JSON 错误体 */ }
    throw new Error(msg)
  }
  let streamErr: string | null = null
  await readSse(res, (ev) => {
    if (ev.type === 'error') streamErr = ev.message || '问数处理失败'
    onEvent(ev)
  })
  if (streamErr) throw new Error(streamErr)
}

export const qaApi = {
  listSessions: () => http.get<SessionItem[]>('/qa/sessions'),
  createSession: (title: string) => http.post<{ id: string; title: string }>('/qa/sessions', { title }),
  patchSession: (id: string, data: { pinned?: boolean; title?: string }) =>
    http.patch<{ ok: boolean }>(`/qa/sessions/${id}`, data),
  deleteSession: (id: string) => http.delete<{ ok: boolean }>(`/qa/sessions/${id}`),
  listMessages: (id: string) => http.get<MsgItem[]>(`/qa/sessions/${id}/messages`),
  ask: askStream,
  getSources: () => http.get<DataSourceGroup[]>('/qa/sources'),
  getQuickAsks: () => http.get<{ enabled: boolean; hot: { question: string; hit: number }[] }>('/qa/quick-asks'),
}
