/** 问数输入栏（原型 1:1）：表情/快捷提问/文本域/语音/发送（发送统一走 AskContext） */

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useSnackbar } from '../../hooks/useSnackbar'
import { useAsk } from './qaContext'
import EmojiPickerPanel from './EmojiPickerPanel'
import QuickAsk from './QuickAsk'

interface Props {
  sending: boolean
  sttEnabled: boolean
}

/** 浏览器语音识别实例最小类型（DOM lib 未收录 SpeechRecognition） */
interface SRResultItem { transcript: string }
interface SREvent { results: ArrayLike<ArrayLike<SRResultItem>> }
interface SRInstance {
  lang: string
  interimResults: boolean
  onresult: ((e: SREvent) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}
type SRCtor = new () => SRInstance

/** 浏览器语音识别（原型 qaVoiceInput 行为） */
function useVoiceInput(sttEnabled: boolean) {
  const { showSnackbar } = useSnackbar()
  const [listening, setListening] = useState(false)
  const recRef = useRef<SRInstance | null>(null)

  const start = useCallback((onText: (t: string) => void) => {
    if (!sttEnabled) {
      showSnackbar('语音转文字未开启，请前往 系统管理 → 应用配置 开启', 'warning')
      return
    }
    const w = window as unknown as { SpeechRecognition?: SRCtor; webkitSpeechRecognition?: SRCtor }
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition
    if (!SR) {
      showSnackbar('当前浏览器不支持语音识别，请使用 Chrome/Edge', 'warning')
      return
    }
    const rec = new SR()
    rec.lang = 'zh-CN'
    rec.interimResults = false
    rec.onresult = (e: SREvent) => {
      const txt = e.results[0][0].transcript
      if (txt) onText(txt)
    }
    rec.onerror = () => showSnackbar('语音识别失败，请重试', 'error')
    rec.onend = () => setListening(false)
    recRef.current = rec
    setListening(true)
    showSnackbar('正在聆听，请说话…', 'success')
    rec.start()
  }, [sttEnabled, showSnackbar])

  useEffect(() => () => {
    recRef.current?.stop()
  }, [])

  return { listening, start }
}

export default function InputBar({ sending, sttEnabled }: Props) {
  const [text, setText] = useState('')
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { listening, start } = useVoiceInput(sttEnabled)
  const ask = useAsk()

  const send = useCallback(() => {
    const t = text.trim()
    if (!t || sending) return
    ask(t)
    setText('')
    inputRef.current?.focus()
  }, [text, sending, ask])

  const onKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }, [send])

  const pickEmoji = useCallback((emoji: string) => {
    const el = inputRef.current
    if (!el) {
      setText((p) => p + emoji)
    } else {
      const s = el.selectionStart ?? text.length
      const e = el.selectionEnd ?? text.length
      setText(text.slice(0, s) + emoji + text.slice(e))
      requestAnimationFrame(() => {
        el.focus()
        const pos = s + emoji.length
        el.setSelectionRange(pos, pos)
      })
    }
  }, [text])

  const voiceInput = useCallback(() => {
    start((txt) => {
      setText((p) => (p ? p + ' ' : '') + txt)
      inputRef.current?.focus()
    })
  }, [start])

  return (
    <div className="qa-input-bar">
      <div className="qa-input-wrap">
        {/* 最前面：表情图标（展开选择常用 emoji） */}
        <button className="qa-emoji-btn" title="表情" aria-label="插入表情"
          style={emojiOpen ? { background: '#F3F4F6', color: '#3B82F6' } : undefined}
          onClick={() => { setEmojiOpen((v) => !v); setQuickOpen(false) }}>
          <i className={emojiOpen ? 'fas fa-face-smile' : 'far fa-face-smile'} />
        </button>
        <EmojiPickerPanel open={emojiOpen} onPick={pickEmoji} onClose={() => setEmojiOpen(false)} />

        {/* 快捷提问 */}
        <button className="qq-btn" title="快捷提问" aria-label="快捷提问"
          onClick={() => { setQuickOpen((v) => !v); setEmojiOpen(false) }}>
          <i className="fas fa-bolt" />
        </button>

        <textarea ref={inputRef} rows={1} placeholder="请写下您的想法…" value={text}
          onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown} disabled={sending} />

        <button className="qa-mic-btn" title="语音输入" aria-label="语音输入" disabled={!sttEnabled || sending} onClick={voiceInput}>
          <i className={listening ? 'fas fa-circle' : 'fas fa-microphone'}
            style={listening ? { color: '#F59E0B' } : undefined} />
        </button>

        <button className={`qa-send-btn ${text.trim() ? '' : 'op'}`} title="发送" aria-label="发送"
          disabled={!text.trim() || sending} onClick={send}>
          <i className={sending ? 'fas fa-spinner fa-spin' : 'fas fa-arrow-right'} />
        </button>

        {quickOpen && (
          <QuickAsk onClose={() => setQuickOpen(false)} />
        )}
      </div>
    </div>
  )
}
