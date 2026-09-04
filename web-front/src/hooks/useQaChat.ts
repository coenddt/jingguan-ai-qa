/** 问数聊天流：messages/activeId/sending + loadMessages/send（含 qa:ask 全局事件订阅） */

import { useCallback, useEffect, useState } from 'react'
import { qaApi } from '../api/modules/qa'
import { useSessionStore } from '../store/useSessionStore'
import { onQaAsk } from '../services/qa'
import { getApiErrorMsg } from '../utils/error'
import { useSnackbar } from './useSnackbar'
import type { MsgItem } from '../types'

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
    setMessages((prev) => [...prev, { id: localId, role: 'user', content: question }])
    try {
      const { data } = await qaApi.ask({
        question,
        session_id: activeId,
        source_keys: selectedSources,
      })
      const aiMsg: MsgItem = { id: `local-a-${now}`, role: 'ai', content: data.text, aiMeta: data }
      setMessages((prev) => [...prev, aiMsg])
      if (!activeId && data.session_id) setActiveId(data.session_id)
      fetchSessions().catch(() => undefined)
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== localId))
      showSnackbar(getApiErrorMsg(e) || '问数请求失败，请稍后重试', 'error')
    } finally {
      setSending(false)
    }
  }, [activeId, fetchSessions, selectedSources, sending, showSnackbar])

  // 追问 chips / 快捷提问统一入口（全局事件）
  useEffect(() => onQaAsk((q) => { void send(q) }), [send])

  return { messages, sending, activeId, send, loadMessages }
}
