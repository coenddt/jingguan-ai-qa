/** 问数输入栏（原型 1:1）：表情/快捷提问/文本域/语音/发送（发送统一走 AskContext） */

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useSnackbar } from '../../hooks/useSnackbar'
import { useAsk } from './qaContext'
import { ASR_PROCESSOR_NAME, getAsrWorkletUrl } from './asrWorklet'
import EmojiPickerPanel from './EmojiPickerPanel'
import QuickAsk from './QuickAsk'

interface Props {
  sending: boolean
  sttEnabled: boolean
}

/** 语音识别结果回调 */
interface VoiceHandlers {
  onPartial: (partial: string) => void
  onDone: (finalText: string) => void
}

/**
 * 语音输入 → 后端（豆包语音识别 2.0 双向流式）
 * AudioContext(16k)采集 PCM int16 → 原生 WebSocket 上行 → 后端转发火山，
 * 识别文本后端实时下行，流式累积（final=true 固化 / final=false 中间稿）。
 * 本 hook 只产出"识别文本"：final 结果通过 onDone 回调，流式中间稿经 onPartial 回调，
 * 是否拼接手打内容由调用方（InputBar）决定。
 */
function useVoiceInput(sttEnabled: boolean) {
  const { showSnackbar } = useSnackbar()
  const [listening, setListening] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const srcRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const nodeRef = useRef<AudioWorkletNode | null>(null)
  const mediaRef = useRef<MediaStream | null>(null)
  const confirmedRef = useRef('')
  const interimRef = useRef('')
  const handlersRef = useRef<VoiceHandlers | null>(null)
  const timerRef = useRef<number | null>(null)

  const stopAll = useCallback(() => {
    const ws = wsRef.current
    wsRef.current = null
    try { if (ws && ws.readyState <= WebSocket.OPEN) ws.close() } catch { /* noop */ }
    const node = nodeRef.current
    if (node) { try { node.port.close(); node.disconnect() } catch { /* noop */ } }
    nodeRef.current = null
    const src = srcRef.current
    if (src) { try { src.disconnect() } catch { /* noop */ } }
    srcRef.current = null
    const ctx = ctxRef.current
    ctxRef.current = null
    if (ctx && ctx.state !== 'closed') { try { void ctx.close() } catch { /* noop */ } }
    const media = mediaRef.current
    mediaRef.current = null
    if (media) { media.getTracks().forEach((t) => t.stop()) }
    if (timerRef.current != null) { window.clearTimeout(timerRef.current); timerRef.current = null }
    setListening(false)
  }, [])

  const flushFinal = useCallback(() => {
    const all = (confirmedRef.current + interimRef.current).trim()
    const h = handlersRef.current
    if (h && all) h.onDone(all)
    confirmedRef.current = ''
    interimRef.current = ''
    handlersRef.current = null
  }, [])

  const stop = useCallback(() => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ action: 'end' })) } catch { /* noop */ }
    }
    // 立即收尾：先固化已收到的识别结果（onDone 回填），再关录音/连接。
    // 不延迟 —— 延迟期间 listening 仍为 true，用户再次点击无法立刻重新开始，
    // 且残留定时器在重新开始后会误关新会话。
    flushFinal()
    stopAll()
  }, [flushFinal, stopAll])

  const startRecording = useCallback((handlers: VoiceHandlers) => {
    if (!sttEnabled) {
      showSnackbar('语音转文字未开启，请前往 系统管理 → 应用配置 开启', 'warning')
      return
    }
    stopAll()
    confirmedRef.current = ''
    interimRef.current = ''
    handlersRef.current = handlers
    setListening(true)
    showSnackbar('正在聆听，请说话…', 'success')

    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/asr/ws`
    let ws: WebSocket
    try { ws = new WebSocket(wsUrl) } catch {
      flushFinal(); stopAll(); showSnackbar('语音识别连接失败，请重试', 'error'); return
    }
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onmessage = (ev) => {
      if (typeof ev.data !== 'string') return
      let m: { type?: string; text?: string; final?: boolean; detail?: string } = {}
      try { m = JSON.parse(ev.data) } catch { return }
      if (m.type === 'transcript' && typeof m.text === 'string') {
        if (m.final) { confirmedRef.current += m.text; interimRef.current = '' }
        else { interimRef.current = m.text }
        handlersRef.current?.onPartial(confirmedRef.current + interimRef.current)
      } else if (m.type === 'done') {
        flushFinal(); stopAll()
      } else if (m.type === 'error') {
        flushFinal(); stopAll()
        showSnackbar(m.detail || '语音识别服务连接失败，请重试', 'error')
      }
    }
    ws.onerror = () => {
      flushFinal(); stopAll()
      showSnackbar('语音识别服务连接失败，请重试', 'error')
    }
    ws.onclose = () => { if (wsRef.current === ws) wsRef.current = null }

    // 获取麦克风 + 用 16k AudioContext 让浏览器自动降采样；就绪后再发 start
    void navigator.mediaDevices.getUserMedia({ audio: true }).then(async (stream) => {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ctx = new Ctx({ sampleRate: 16000 })
      // 用 AudioWorkletNode（替代已弃用的 ScriptProcessorNode）：Blob URL 内嵌处理器，
      // 音频线程内转 PCM int16 后经 node.port 下行，主线程上行 WS。
      await ctx.audioWorklet.addModule(getAsrWorkletUrl())
      // addModule 为异步；若期间已停录（ws 已被 stopAll 置空），直接回收本次资源
      if (wsRef.current !== ws) {
        try { ctx.close() } catch { /* noop */ }
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      const node = new AudioWorkletNode(ctx, ASR_PROCESSOR_NAME)
      node.port.onmessage = (e) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(e.data as ArrayBuffer)
      }
      ctxRef.current = ctx
      const src = ctx.createMediaStreamSource(stream)
      srcRef.current = src
      nodeRef.current = node
      mediaRef.current = stream
      src.connect(node)
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'start' }))
    }).catch(() => {
      flushFinal(); stopAll()
      showSnackbar('无法访问麦克风，请检查浏览器权限', 'error')
    })

    // 长时间无人说话自动收尾，避免无限录音
    timerRef.current = window.setTimeout(() => { if (wsRef.current) stop() }, 60000)
  }, [sttEnabled, showSnackbar, flushFinal, stopAll, stop])

  useEffect(() => () => { stopAll() }, [stopAll])

  return { listening, stop, start: startRecording }
}

export default function InputBar({ sending, sttEnabled }: Props) {
  const [text, setText] = useState('')
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { listening, start, stop } = useVoiceInput(sttEnabled)
  const ask = useAsk()

  const send = useCallback(() => {
    const t = text.trim()
    if (!t || sending) return
    // 先停语音：flushFinal 固化识别文本且清空语音回调，避免发送后晚到的 transcript/done
    // 把识别文字再次写回输入框（用户看到"没发出去"的假象）。
    stop()
    ask(t)
    setText('')
    inputRef.current?.focus()
  }, [text, sending, ask, stop])

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
    if (listening) { stop(); return }
    // 记录点击时的既有内容，识别期间流式拼接显示，结束保留手打 + 识别
    const base = text.trim()
    start({
      onPartial: (partial) => {
        setText(base ? `${base} ${partial}` : partial)
        inputRef.current?.focus()
      },
      onDone: (finalText) => {
        setText(base ? `${base} ${finalText}` : finalText)
        inputRef.current?.focus()
      },
    })
  }, [listening, stop, start, text])

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
