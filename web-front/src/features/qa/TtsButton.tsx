/** 语音播放按钮（原型 icon-only：fa-volume-up，播放中 fa-stop，加载中 fa-spinner 且点击=停止，状态机在 useTts） */

import { useTts } from '../../hooks/useTts'

export default function TtsButton({ text }: { text: string }) {
  const { loading, playing, toggle } = useTts(text)

  const title = loading ? '停止加载' : playing ? '停止播放' : '语音播放'
  return (
    <button data-title={title} aria-label={title} onClick={toggle}>
      <i className={`fas ${loading ? 'fa-spinner fa-spin' : playing ? 'fa-stop' : 'fa-volume-up'}`} />
    </button>
  )
}
