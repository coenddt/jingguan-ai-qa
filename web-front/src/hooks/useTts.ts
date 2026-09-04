/** TTS 播放状态机：loading/playing + toggle（TtsButton 使用） */

import { useCallback, useEffect, useRef, useState } from 'react'
import { synthesizeAudio } from '../services/tts'
import { useSnackbar } from './useSnackbar'

export function useTts(text: string) {
  const [loading, setLoading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const { showSnackbar } = useSnackbar()

  const toggle = useCallback(async () => {
    if (playing) {
      audioRef.current?.pause()
      setPlaying(false)
      return
    }
    setLoading(true)
    try {
      const audio = await synthesizeAudio(text)
      audioRef.current = audio
      audio.onended = () => setPlaying(false)
      await audio.play()
      setPlaying(true)
    } catch {
      showSnackbar('语音合成失败，请稍后重试', 'error')
    } finally {
      setLoading(false)
    }
  }, [playing, text, showSnackbar])

  // 卸载时停止播放
  useEffect(() => () => { audioRef.current?.pause() }, [])

  return { loading, playing, toggle }
}
