/** 问数聊天流：messages/activeId/sending + loadMessages/send（SSE 流式：步骤/结果块逐个 patch） */

import { useCallback, useEffect, useRef, useState } from 'react'
import { qaApi } from '../api/modules/qa'
import type { QaStreamEvent } from '../api/modules/qa'
import { useSessionStore } from '../store/useSessionStore'
import { getApiErrorMsg } from '../utils/error'
import { writeJsonLS } from '../utils/localStorage'
import { useSnackbar } from './useSnackbar'
import type { MsgItem, QaAskResp, Step } from '../types'

/** 上次会话持久化 key：切会话/开新会话/新建会话落库时同步，供刷新或返回消息页时恢复 */
export const LAST_SESSION_KEY = 'jg_qa_last_session'

export function useQaChat(selectedSources: string[]) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<MsgItem[]>([])
  const [sending, setSending] = useState(false)
  /** 进行中流的终止器：切会话/组件卸载时中止，避免 sending 卡死与无效流消费 */
  const abortRef = useRef<AbortController | null>(null)
  const fetchSessions = useSessionStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()

  // 卸载时中止进行中的问数流
  useEffect(() => () => { abortRef.current?.abort() }, [])

  /** 切换会话 / 开新会话（id 为空即新会话） */
  const loadMessages = useCallback(async (id: string | null) => {
    abortRef.current?.abort()
    abortRef.current = null
    setActiveId(id || null)
    writeJsonLS(LAST_SESSION_KEY, id)
    if (!id) {
      setMessages([])
      return
    }
    try {
      const { data } = await qaApi.listMessages(id)
      setMessages(data)
    } catch {
      showSnackbar('历史消息加载失败', 'error')
    }
  }, [showSnackbar])

  const send = useCallback(async (question: string) => {
    if (!question.trim() || sending) return
    setSending(true)
    const now = Date.now()
    const localId = `local-u-${now}`
    const aiId = `local-a-${now}`
    setMessages((prev) => [...prev, { id: localId, role: 'user', content: question },
      { id: aiId, role: 'ai', content: '', aiMeta: {}, streaming: true }])

    // 流式逐块 patch 当前 AI 消息
    const patch = (fn: (d: Partial<QaAskResp>) => Partial<QaAskResp>) => {
      setMessages((prev) => prev.map((m) => (
        m.id === aiId ? { ...m, aiMeta: fn(m.aiMeta ?? {}) } : m)))
    }

    const onEvent = (ev: QaStreamEvent) => {
      if (ev.type === 'steps') {
        const steps = (ev.data as { title: string }[]).map<Step>((t) => ({ title: t.title, desc: '', done: false }))
        patch((d) => ({ ...d, steps }))
      } else if (ev.type === 'step') {
        patch((d) => ({
          ...d,
          steps: (d.steps ?? []).map((s, i) => (i === ev.index
            ? { ...s, running: ev.status === 'running', desc: ev.desc ?? '', done: ev.status === 'done' }
            : s)),
        }))
      } else if (ev.type === 'block') {
        if (ev.name === 'table') {
          const t = ev.data as { columns: string[]; rows: (string | number)[][] }
          patch((d) => ({ ...d, columns: t.columns, rows: t.rows }))
        } else {
          patch((d) => ({ ...d, [ev.name as 'findings' | 'stats' | 'chart' | 'text' | 'follow_ups']: ev.data }))
        }
      } else if (ev.type === 'session') {
        const sid = (ev.data as { session_id: string }).session_id
        if (!activeId && sid) {
          setActiveId(sid)
          writeJsonLS(LAST_SESSION_KEY, sid)
        }
      } else if (ev.type === 'done') {
        patch(() => ev.data as QaAskResp)
      }
    }

    const ac = new AbortController()
    abortRef.current = ac

    try {
      await qaApi.ask({ question, session_id: activeId, source_keys: selectedSources }, onEvent, ac.signal)
      setMessages((prev) => prev.map((m) => {
        if (m.id !== aiId) return m
        const full = (m.aiMeta ?? {}) as QaAskResp
        return { ...m, content: full.text ?? '', aiMeta: full, streaming: false }
      }))
      fetchSessions().catch(() => undefined)
    } catch (e) {
      // 主动中止（切会话/卸载）：不提示、不动占位（切会话时 messages 随即被历史覆盖）
      if (e instanceof DOMException && e.name === 'AbortError') return
      // 失败：移除占位卡片，保留用户消息并提示
      setMessages((prev) => prev.filter((m) => m.id !== aiId))
      showSnackbar(getApiErrorMsg(e) || '问数请求失败，请稍后重试', 'error')
    } finally {
      if (abortRef.current === ac) abortRef.current = null
      setSending(false)
    }
  }, [activeId, fetchSessions, selectedSources, sending, showSnackbar])

  return { messages, sending, activeId, send, loadMessages }
}
