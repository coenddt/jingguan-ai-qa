import { useCallback, useEffect, useRef, useState } from 'react'
import { PanelLeftOpen } from 'lucide-react'
import { qaApi } from '../api/modules/qa'
import { useConfigStore } from '../store/useConfigStore'
import { useSessionStore } from '../store/useSessionStore'
import type { DataSourceGroup, MsgItem, QaAskResp } from '../types'
import SessionList from '../features/qa/SessionList'
import Welcome from '../features/qa/Welcome'
import ChatMessage from '../features/qa/ChatMessage'
import AiCard from '../features/qa/AiCard'
import InputBar from '../features/qa/InputBar'
import SourcePicker from '../features/qa/SourcePicker'
import QuickAsk from '../features/qa/QuickAsk'
import { useSnackbar } from '../hooks/useSnackbar'

const SOURCES_KEY = 'jg_sources'

function loadSelectedSources(): string[] {
  try {
    return JSON.parse(localStorage.getItem(SOURCES_KEY) || '[]') as string[]
  } catch {
    return []
  }
}

export default function Qa() {
  const { sessions, fetchMethod } = useSessionStore()
  const { config, fetchMethod: fetchConfig } = useConfigStore()
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<MsgItem[]>([])
  const [sending, setSending] = useState(false)
  const [listOpen, setListOpen] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const [selectedSources, setSelectedSources] = useState<string[]>(loadSelectedSources)
  const [sourceGroups, setSourceGroups] = useState<DataSourceGroup[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const { showSnackbar } = useSnackbar()

  // 启动期初始化：会话列表 + 应用配置 + 数据源定义（防重锁在 store 内）
  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('会话列表加载失败', 'error'))
    fetchConfig().catch(() => showSnackbar('应用配置加载失败', 'error'))
    qaApi.getSources().then(({ data }) => setSourceGroups(data)).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    localStorage.setItem(SOURCES_KEY, JSON.stringify(selectedSources))
  }, [selectedSources])

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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const send = useCallback(async (question: string) => {
    if (sending) return
    setSending(true)
    setListOpen(false) // 发送首条消息时侧栏自动收起
    const now = Date.now()
    setMessages((prev) => [...prev, {
      id: `local-u-${now}`, role: 'user', content: question,
    }])
    try {
      const { data } = await qaApi.ask({
        question,
        session_id: activeId,
        source_keys: selectedSources,
      })
      const resp: QaAskResp = data
      const aiMsg: MsgItem = {
        id: `local-a-${now}`, role: 'ai', content: resp.text, aiMeta: resp,
      }
      setMessages((prev) => [...prev, aiMsg])
      if (!activeId && resp.session_id) setActiveId(resp.session_id)
      fetchMethod().catch(() => undefined)
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMessages((prev) => prev.filter((m) => m.id !== `local-u-${now}`))
      showSnackbar(detail || '问数请求失败，请稍后重试', 'error')
    } finally {
      setSending(false)
    }
  }, [activeId, fetchMethod, selectedSources, sending, showSnackbar])

  // 追问 chips / 快捷提问统一入口
  useEffect(() => {
    const handler = (e: Event) => send((e as CustomEvent<string>).detail)
    window.addEventListener('qa:ask', handler)
    return () => window.removeEventListener('qa:ask', handler)
  }, [send])

  const selectedCount = selectedSources.length

  return (
    <div className="h-full flex">
      <SessionList open={listOpen} activeId={activeId} onClose={() => setListOpen(false)}
        onSelect={(id) => { loadMessages(id || null); setListOpen(false) }} onNew={() => { loadMessages(null); setListOpen(false) }} />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-200 bg-white/70">
          {!listOpen && (
            <button className="btn btn-ghost btn-sm btn-square" title="会话列表" onClick={() => setListOpen(true)}>
              <PanelLeftOpen size={18} />
            </button>
          )}
          <span className="font-bold text-gray-700 text-sm">
            {sessions.find((s) => s.id === activeId)?.title || '新对话'}
          </span>
        </div>

        <div className="flex-1 overflow-auto px-5 py-5">
          {messages.length === 0 && !sending ? (
            <Welcome onAsk={send} />
          ) : (
            <div className="max-w-[900px] mx-auto space-y-5">
              {messages.map((m) => m.role === 'user' ? (
                <ChatMessage key={m.id} content={m.content} onResend={send} />
              ) : m.aiMeta ? (
                <AiCard key={m.id} resp={m.aiMeta} question={messages[messages.indexOf(m) - 1]?.content || ''} />
              ) : (
                <div key={m.id} className="bg-white rounded-2xl border border-gray-200 p-4 max-w-[860px]">
                  <p className="text-sm text-gray-600 whitespace-pre-wrap">{m.content}</p>
                </div>
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <span className="loading loading-spinner loading-sm" /> 正在分析数据，请稍候...
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="px-5 pb-5">
          <div className="max-w-[900px] mx-auto">
            <InputBar sending={sending} sttEnabled={config.stt} selectedCount={selectedCount}
              onSend={send} onOpenSources={() => setSourceOpen(true)} onOpenQuickAsk={() => setQuickOpen(true)} />
          </div>
        </div>
      </div>

      <SourcePicker open={sourceOpen} selected={selectedSources} onChange={setSelectedSources}
        onClose={() => setSourceOpen(false)} />
      <QuickAsk open={quickOpen} onClose={() => setQuickOpen(false)} onAsk={send} />
    </div>
  )
}
