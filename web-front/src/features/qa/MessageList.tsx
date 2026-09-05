/** 聊天消息区（原型 chatMessages）：用户消息 / AI 卡片 / AI 纯文本气泡 + 自动滚底（近底才滚） */

import { useEffect, useRef, type RefObject } from 'react'
import type { MsgItem } from '../../types'
import ChatMessage from './ChatMessage'
import AiCard from './AiCard'

interface Props {
  messages: MsgItem[]
  sending: boolean
  /** 滚动容器（Qa 页传入），用于判定用户是否处于底部 */
  scrollRef: RefObject<HTMLDivElement | null>
}

/** 距底阈值（px）：超过视为用户已上滑回看，不打断 */
const NEAR_BOTTOM = 80

export default function MessageList({ messages, sending, scrollRef }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el && el.scrollHeight - el.scrollTop - el.clientHeight > NEAR_BOTTOM) return
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending, scrollRef])

  return (
    <div className="max-w-[900px] mx-auto space-y-5 pb-2">
      {messages.map((m, i) => m.role === 'user' ? (
        <ChatMessage key={m.id} content={m.content} />
      ) : m.aiMeta ? (
        <AiCard key={m.id} resp={m.aiMeta} question={messages[i - 1]?.content || ''} streaming={m.streaming} createdAt={m.createdAt} />
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
