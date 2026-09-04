/** 问数输入栏：快捷提问/语音/数据源 + 文本域 + 发送 */

import { useCallback, useRef, useState, type KeyboardEvent } from 'react'
import { Database, Mic, SendHorizonal, Zap } from 'lucide-react'

interface Props {
  sending: boolean
  sttEnabled: boolean
  selectedCount: number
  onSend: (text: string) => void
  onOpenSources: () => void
  onOpenQuickAsk: () => void
}

export default function InputBar({ sending, sttEnabled, selectedCount, onSend, onOpenSources, onOpenQuickAsk }: Props) {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const send = useCallback(() => {
    const t = text.trim()
    if (!t || sending) return
    onSend(t)
    setText('')
  }, [text, sending, onSend])

  const onKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }, [send])

  return (
    <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-3 flex items-end gap-2">
      <button className="btn btn-ghost btn-sm btn-square shrink-0" title="快捷提问" onClick={onOpenQuickAsk}>
        <Zap size={19} strokeWidth={1.5} className="text-gold-deep" />
      </button>
      <button className={`btn btn-ghost btn-sm btn-square shrink-0 ${sttEnabled ? '' : 'btn-disabled'}`}
        title={sttEnabled ? '语音输入' : '语音转文字未开启'} disabled={!sttEnabled}>
        <Mic size={19} strokeWidth={1.5} className="text-gray-400" />
      </button>
      <button className="btn btn-ghost btn-sm shrink-0 gap-1 whitespace-nowrap text-gray-500" title="数据源选择" onClick={onOpenSources}>
        <Database size={17} strokeWidth={1.5} />
        <span className="text-xs">{selectedCount > 0 ? `已选 ${selectedCount} 个数据源` : '数据源'}</span>
      </button>
      <textarea className="textarea textarea-bordered flex-1 min-h-[44px] max-h-32 resize-none text-sm"
        placeholder="请输入你的问题，Enter 发送 / Shift+Enter 换行" rows={1}
        value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown} disabled={sending} />
      <button className="btn btn-primary shrink-0 whitespace-nowrap gap-1" onClick={send} disabled={!text.trim() || sending}>
        {sending ? <span className="loading loading-spinner loading-xs" /> : <SendHorizonal size={17} strokeWidth={1.5} />}
        发送
      </button>
    </div>
  )
}
