/** TTS 播放状态机：loading/playing + toggle（TtsButton 使用）
 *  加载中点击 = 停止（中止加载，不可重复触发播放）；开始加载 1s 后仍未开播给弱提示 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { synthesizeAudio } from '../services/tts'
import { useSnackbar } from './useSnackbar'

/** 加载弱提示阈值：超过该时长仍未开播则提示用户语音加载可能较慢 */
const SLOW_HINT_MS = 1000

export function useTts(text: string) {
  const [loading, setLoading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { showSnackbar } = useSnackbar()

  const toggle = useCallback(async () => {
    if (playing) {
      audioRef.current?.pause()
      setPlaying(false)
      return
    }
    if (loading) {
      // 加载中：点击 = 停止（中止加载），不可重复触发播放
      abortRef.current?.abort()
      audioRef.current?.pause() // 中止加载尾声已就绪的音频（play() 被打断的报错由下方 catch 静默收敛）
      return
    }
    setLoading(true)
    const controller = new AbortController()
    abortRef.current = controller
    const slowTimer = setTimeout(() => {
      showSnackbar('语音加载可能有点慢，请稍候片刻', 'info')
    }, SLOW_HINT_MS)
    slowTimerRef.current = slowTimer
    try {
      const audio = await synthesizeAudio(text, controller.signal)
      if (controller.signal.aborted) {
        URL.revokeObjectURL(audio.src)
        return
      }
      audioRef.current = audio
      audio.onended = () => setPlaying(false)
      await audio.play()
      if (controller.signal.aborted) {
        audio.pause()
        setPlaying(false)
        return
      }
      setPlaying(true)
    } catch {
      // 主动停止（abort/打断 play）不算失败；仅真实失败才提示
      if (!controller.signal.aborted) showSnackbar('语音合成失败，请稍后重试', 'error')
    } finally {
      if (slowTimerRef.current) {
        clearTimeout(slowTimerRef.current)
        slowTimerRef.current = null
      }
      abortRef.current = null
      setLoading(false)
    }
  }, [playing, loading, text, showSnackbar])

  // 卸载时中止加载并停止播放
  useEffect(() => () => {
    abortRef.current?.abort()
    if (slowTimerRef.current) clearTimeout(slowTimerRef.current)
    audioRef.current?.pause()
  }, [])

  return { loading, playing, toggle }
}
