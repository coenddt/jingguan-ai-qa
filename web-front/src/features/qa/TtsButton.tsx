import { useRef, useState } from 'react'
import { Volume2, Square } from 'lucide-react'
import { ttsApi } from '../../api/modules/tts'
import { useSnackbar } from '../../hooks/useSnackbar'

export default function TtsButton({ text }: { text: string }) {
  const [loading, setLoading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const { showSnackbar } = useSnackbar()

  const play = async () => {
    if (playing) {
      audioRef.current?.pause()
      setPlaying(false)
      return
    }
    setLoading(true)
    try {
      const { data } = await ttsApi.synthesize(text)
      const url = URL.createObjectURL(data)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => setPlaying(false)
      audio.play()
      setPlaying(true)
    } catch {
      showSnackbar('语音合成失败，请稍后重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button className="btn btn-ghost btn-xs gap-1 text-gray-500 whitespace-nowrap" onClick={play} disabled={loading}>
      {playing ? <Square size={13} /> : <Volume2 size={14} />}
      {playing ? '停止' : '语音播报'}
    </button>
  )
}
