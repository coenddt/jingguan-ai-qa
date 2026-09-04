/** 问数聊天流：messages/activeId/sending + loadMessages/send（SSE 流式：步骤/结果块逐个 patch） */

import { useCallback, useEffect, useState } from 'react'
import { qaApi } from '../api/modules/qa'
import type { QaStreamEvent } from '../api/modules/qa'
import { useSessionStore } from '../store/useSessionStore'
import { onQaAsk } from '../services/qa'
import { getApiErrorMsg } from '../utils/error'
import { useSnackbar } from './useSnackbar'
import type { MsgItem, QaAskResp, Step } from '../types'

export function useQaChat(selectedSources: string[]) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<MsgItem[]>([])
  const [sending, setSending] = useState(false)
  const fetchSessions = useSessionStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()

  /** 切换会话 / 开新会话（id 为空即新会话） */
  const loadMessages = useCallback(async (id: string | null) => {
    setActiveId(id || null)
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
        if (!activeId && sid) setActiveId(sid)
      } else if (ev.type === 'done') {
        patch(() => ev.data as QaAskResp)
      }
    }

    try {
      await qaApi.ask({ question, session_id: activeId, source_keys: selectedSources }, onEvent)
      setMessages((prev) => prev.map((m) => {
        if (m.id !== aiId) return m
        const full = (m.aiMeta ?? {}) as QaAskResp
        return { ...m, content: full.text ?? '', aiMeta: full, streaming: false }
      }))
      fetchSessions().catch(() => undefined)
    } catch (e) {
      // 失败：移除占位卡片，保留用户消息并提示
      setMessages((prev) => prev.filter((m) => m.id !== aiId))
      showSnackbar(getApiErrorMsg(e) || '问数请求失败，请稍后重试', 'error')
    } finally {
      setSending(false)
    }
  }, [activeId, fetchSessions, selectedSources, sending, showSnackbar])

  // 追问 chips / 快捷提问统一入口（全局事件）
  useEffect(() => onQaAsk((q) => { void send(q) }), [send])

  return { messages, sending, activeId, send, loadMessages }
}
