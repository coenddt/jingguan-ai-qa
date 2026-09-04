/** 表情选择弹层（emoji-mart native 模式：系统字体渲染 + 数据/i18n 本地打包，零网络请求，国内环境无加载问题） */

import { useEffect, useRef } from 'react'
import Picker from '@emoji-mart/react'
import data from '@emoji-mart/data'
import zh from '@emoji-mart/data/i18n/zh.json'

interface Props {
  open: boolean
  onPick: (emoji: string) => void
  onClose: () => void
}

export default function EmojiPickerPanel({ open, onPick, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  // 点击弹层外部关闭
  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open, onClose])

  if (!open) return null

  return (
    <div ref={ref} className="emoji-pop">
      <Picker data={data} i18n={zh} set="native" theme="light"
        width={340} height={380} emojiSize={22} perLine={9}
        previewPosition="none" skinTonePosition="none" searchPosition="top"
        onEmojiSelect={(e: { native?: string }) => { if (e.native) onPick(e.native) }} />
    </div>
  )
}
