/** 语音播报按钮（状态机在 useTts） */

import { Volume2, Square } from 'lucide-react'
import { useTts } from '../../hooks/useTts'

export default function TtsButton({ text }: { text: string }) {
  const { loading, playing, toggle } = useTts(text)

  return (
    <button className="btn btn-ghost btn-xs gap-1 text-gray-500 whitespace-nowrap" onClick={toggle} disabled={loading}>
      {playing ? <Square size={13} /> : <Volume2 size={14} />}
      {playing ? '停止' : '语音播报'}
    </button>
  )
}
