/** 智能问数主页（原型 page-ai-qa）：会话侧栏 + 主区（对话/日志） + 输入栏 + 数据源弹窗 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useConfigStore } from '../../store/useConfigStore'
import { useSessionStore } from '../../store/useSessionStore'
import { useSnackbar } from '../../hooks/useSnackbar'
import { useQaChat } from '../../hooks/useQaChat'
import { readJsonLS, writeJsonLS } from '../../utils/localStorage'
import type { SessionItem } from '../../types'
import SessionList from '../../features/qa/SessionList'
import Welcome from '../../features/qa/Welcome'
import MessageList from '../../features/qa/MessageList'
import InputBar from '../../features/qa/InputBar'
import SourcePicker from '../../features/qa/SourcePicker'
import QaLogView, { QaDetailModal } from '../../features/qa/QaLogView'
import QaTopBar from './QaTopBar'

const SOURCES_KEY = 'jg_sources'

function loadSelectedSources(): string[] {
  return readJsonLS<string[]>(SOURCES_KEY, [])
}

export default function Qa() {
  const sessions = useSessionStore((s) => s.items)
  const fetchSessions = useSessionStore((s) => s.fetchMethod)
  const fetchConfig = useConfigStore((s) => s.fetchMethod)
  const sttEnabled = useConfigStore((s) => s.config.stt)
  const [listOpen, setListOpen] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(false)
  const [view, setView] = useState<'chat' | 'log'>('chat')
  const [detail, setDetail] = useState<SessionItem | null>(null)
  const [selectedSources, setSelectedSources] = useState<string[]>(loadSelectedSources)
  const { showSnackbar } = useSnackbar()
  const { messages, sending, activeId, send, loadMessages } = useQaChat(selectedSources)

  // 启动期初始化：会话列表 + 应用配置（防重锁在 store 内）
  useEffect(() => {
    fetchSessions().catch(() => showSnackbar('会话列表加载失败', 'error'))
    fetchConfig().catch(() => showSnackbar('应用配置加载失败', 'error'))
  }, [fetchSessions, fetchConfig, showSnackbar])

  // 数据源选择持久化
  useEffect(() => {
    writeJsonLS(SOURCES_KEY, selectedSources)
  }, [selectedSources])

  const activeTitle = useMemo(
    () => sessions.find((s) => s.id === activeId)?.title || 'AI 智能问数对话',
    [sessions, activeId],
  )

  const sourceLabel = useMemo(
    () => (selectedSources.length === 0 ? '已选择所有数据源' : `已选 ${selectedSources.length} 个数据源`),
    [selectedSources.length],
  )

  const openList = useCallback(() => setListOpen(true), [])
  const closeList = useCallback(() => setListOpen(false), [])
  const openSources = useCallback(() => setSourceOpen(true), [])
  const closeSources = useCallback(() => setSourceOpen(false), [])
  const backToChat = useCallback(() => setView('chat'), [])

  const handleSelect = useCallback((id: string) => {
    void loadMessages(id || null)
    setListOpen(false)
    setView('chat')
  }, [loadMessages])

  const handleNew = useCallback(() => {
    void loadMessages(null)
    setListOpen(false)
    setView('chat')
  }, [loadMessages])

  const openSession = useCallback((id: string) => {
    setDetail(sessions.find((s) => s.id === id) ?? null)
  }, [sessions])

  const closeDetail = useCallback(() => setDetail(null), [])

  return (
    <div className="h-full flex">
      <SessionList open={listOpen} activeId={activeId} onClose={closeList}
        onSelect={handleSelect} onNew={handleNew} />

      <div className="qa-main">
        {/* 原型 switchQaTab：日志视图隐藏顶栏与输入栏，由日志视图自带头部 */}
        {view === 'chat' && (
          <QaTopBar title={activeTitle} listOpen={listOpen} onOpenList={openList}
            sourceLabel={sourceLabel}
            onOpenSources={openSources} onSwitchView={setView} />
        )}

        {view === 'chat' ? (
          <>
            <div className="flex-1 overflow-y-auto min-h-0">
              {messages.length === 0 && !sending ? (
                <Welcome onAsk={send} />
              ) : (
                <div className="px-5 pt-5 pb-2">
                  <MessageList messages={messages} sending={sending} onResend={send} />
                </div>
              )}
            </div>
            <InputBar sending={sending} sttEnabled={sttEnabled} onSend={send} />
          </>
        ) : (
          <QaLogView onBack={backToChat} onOpenSession={openSession} />
        )}
      </div>

      <SourcePicker open={sourceOpen} selected={selectedSources} onChange={setSelectedSources}
        onClose={closeSources} />
      <QaDetailModal session={detail} onClose={closeDetail} />
    </div>
  )
}
