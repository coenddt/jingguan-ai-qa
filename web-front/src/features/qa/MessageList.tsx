/** 聊天消息区：用户消息 / AI 卡片 / AI 纯文本气泡 + 发送中指示 + 自动滚底 */

import { useEffect, useRef } from 'react'
import type { MsgItem } from '../../types'
import ChatMessage from './ChatMessage'
import AiCard from './AiCard'

interface Props {
  messages: MsgItem[]
  sending: boolean
  onResend: (text: string) => void
}

export default function MessageList({ messages, sending, onResend }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  return (
    <div className="max-w-[900px] mx-auto space-y-5">
      {messages.map((m, i) => m.role === 'user' ? (
        <ChatMessage key={m.id} content={m.content} onResend={onResend} />
      ) : m.aiMeta ? (
        <AiCard key={m.id} resp={m.aiMeta} question={messages[i - 1]?.content || ''} />
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
  )
}
