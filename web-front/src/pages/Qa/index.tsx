/** 智能问数主页：会话侧栏 + 聊天区 + 输入栏 + 数据源/快捷提问弹窗 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useConfigStore } from '../../store/useConfigStore'
import { useSessionStore } from '../../store/useSessionStore'
import { useSnackbar } from '../../hooks/useSnackbar'
import { useQaChat } from '../../hooks/useQaChat'
import { readJsonLS, writeJsonLS } from '../../utils/localStorage'
import SessionList from '../../features/qa/SessionList'
import Welcome from '../../features/qa/Welcome'
import MessageList from '../../features/qa/MessageList'
import InputBar from '../../features/qa/InputBar'
import SourcePicker from '../../features/qa/SourcePicker'
import QuickAsk from '../../features/qa/QuickAsk'
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
  const [quickOpen, setQuickOpen] = useState(false)
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

  // 发送首条消息时侧栏自动收起
  useEffect(() => {
    if (sending) setListOpen(false)
  }, [sending])

  const activeTitle = useMemo(
    () => sessions.find((s) => s.id === activeId)?.title || '新对话',
    [sessions, activeId],
  )

  const openList = useCallback(() => setListOpen(true), [])
  const closeList = useCallback(() => setListOpen(false), [])
  const openSources = useCallback(() => setSourceOpen(true), [])
  const closeSources = useCallback(() => setSourceOpen(false), [])
  const openQuickAsk = useCallback(() => setQuickOpen(true), [])
  const closeQuickAsk = useCallback(() => setQuickOpen(false), [])

  const handleSelect = useCallback((id: string) => {
    void loadMessages(id || null)
    setListOpen(false)
  }, [loadMessages])

  const handleNew = useCallback(() => {
    void loadMessages(null)
    setListOpen(false)
  }, [loadMessages])

  return (
    <div className="h-full flex">
      <SessionList open={listOpen} activeId={activeId} onClose={closeList}
        onSelect={handleSelect} onNew={handleNew} />

      <div className="flex-1 flex flex-col min-w-0">
        <QaTopBar title={activeTitle} listOpen={listOpen} onOpenList={openList} />

        <div className="flex-1 overflow-auto px-5 py-5">
          {messages.length === 0 && !sending ? (
            <Welcome onAsk={send} />
          ) : (
            <MessageList messages={messages} sending={sending} onResend={send} />
          )}
        </div>

        <div className="px-5 pb-5">
          <div className="max-w-[900px] mx-auto">
            <InputBar sending={sending} sttEnabled={sttEnabled} selectedCount={selectedSources.length}
              onSend={send} onOpenSources={openSources} onOpenQuickAsk={openQuickAsk} />
          </div>
        </div>
      </div>

      <SourcePicker open={sourceOpen} selected={selectedSources} onChange={setSelectedSources}
        onClose={closeSources} />
      <QuickAsk open={quickOpen} onClose={closeQuickAsk} onAsk={send} />
    </div>
  )
}
