/** 语音播放按钮（原型 icon-only：fa-volume-up，播放中 fa-stop，状态机在 useTts） */

import { useTts } from '../../hooks/useTts'

export default function TtsButton({ text }: { text: string }) {
  const { loading, playing, toggle } = useTts(text)

  return (
    <button data-title="语音播放" aria-label="语音播放" disabled={loading} onClick={toggle}>
      <i className={`fas ${playing ? 'fa-stop' : 'fa-volume-up'}`} />
    </button>
  )
}
