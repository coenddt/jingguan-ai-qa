/** 聊天消息区（原型 chatMessages）：用户消息 / AI 卡片 / AI 纯文本气泡 + 自动滚底（用户上滑回看时暂停） */

import { useCallback, useEffect, useLayoutEffect, useRef, type RefObject } from 'react'
import type { MsgItem } from '../../types'
import ChatMessage from './ChatMessage'
import AiCard from './AiCard'

interface Props {
  messages: MsgItem[]
  sending: boolean
  /** 滚动容器（Qa 页传入），用于读取滚动位置 / 定位到底部 */
  scrollRef: RefObject<HTMLDivElement | null>
}

/** 距底阈值（px）：滚动条在此范围内视为仍处于底部，自动跟底继续生效 */
const NEAR_BOTTOM = 80

export default function MessageList({ messages, sending, scrollRef }: Props) {
  /** 消息列表内容容器：观察高度变化，捕获懒图表 / 异步图像等「不改变 messages 却长高」的渲染 */
  const listRef = useRef<HTMLDivElement>(null)
  const initedRef = useRef(false)
  const prevLenRef = useRef(0)
  const prevLastIdRef = useRef<string | undefined>(undefined)
  /** 用户是否已主动上滑离开底部：为 true 时新内容不再自动贴底（不打断回看） */
  const userScrolledRef = useRef(false)

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [scrollRef])
  const nearBottom = useCallback(() => {
    const el = scrollRef.current
    return !!el && el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM
  }, [scrollRef])

  // 跟踪用户滚动：滚离底部 → 暂停自动跟底；滚回底部附近 → 恢复
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const onScroll = () => { userScrolledRef.current = !nearBottom() }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [scrollRef, nearBottom])

  // 懒加载图表 / markdown 图像等异步内容长高（不改变 messages 引用）：用户未上滑时强制回贴绝对底部
  useEffect(() => {
    const root = listRef.current
    if (!root) return
    const ro = new ResizeObserver(() => {
      if (!userScrolledRef.current) scrollToBottom()
    })
    ro.observe(root)
    return () => ro.disconnect()
  }, [scrollToBottom])

  useLayoutEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const last = messages[messages.length - 1]
    const lastId = last?.id
    // 新问题：从上次长度起新增的首条是用户消息（useQaChat 一次追加 user + ai 占位两条）
    const newAsk = messages.length > prevLenRef.current && messages[prevLenRef.current]?.role === 'user'
    // 会话切换：最后一条消息 id 与上次不同（历史整表替换，非新增）
    const switched = !!lastId && prevLastIdRef.current !== undefined && lastId !== prevLastIdRef.current
    prevLenRef.current = messages.length
    prevLastIdRef.current = lastId

    // ① 进入会话 / 切会话：无条件贴底（新会话需看底部；异步图表/图像长高由 ResizeObserver 兜底）
    if (!initedRef.current || switched) {
      initedRef.current = true
      userScrolledRef.current = false
      scrollToBottom()
      return
    }
    // ② 开始新问题（用户刚发送）：无条件贴底，并恢复自动跟底
    if (newAsk) {
      userScrolledRef.current = false
      scrollToBottom()
      return
    }
    // ③ 流式回复逐步到达 / 内容变化：用户未主动上滑则持续贴底
    if (!userScrolledRef.current) {
      scrollToBottom()
    }
  }, [messages, sending, scrollRef, scrollToBottom, nearBottom])

  return (
    <div ref={listRef} className="max-w-[900px] mx-auto space-y-5 pb-2">
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
    </div>
  )
}
