/** 聊天消息区（原型 chatMessages）：用户消息 / AI 卡片 / AI 纯文本气泡 + 发送中指示 + 自动滚底 */

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
    <div className="max-w-[900px] mx-auto space-y-5 pb-2">
      {messages.map((m, i) => m.role === 'user' ? (
        <ChatMessage key={m.id} content={m.content} onResend={onResend} />
      ) : m.aiMeta ? (
        <AiCard key={m.id} resp={m.aiMeta} question={messages[i - 1]?.content || ''} streaming={m.streaming} />
      ) : (
        <div key={m.id} className="qa-ai-msg">
          <div className="qa-ai-avatar"><i className="fas fa-robot" /></div>
          <div className="qa-ai-card">
            <p className="text-sm text-gray-600 whitespace-pre-wrap">{m.content}</p>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
