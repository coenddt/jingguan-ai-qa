/** 用户消息气泡：编辑 / 重新发送 / 收藏 / 复制 */

import { useCallback, useState } from 'react'
import { Check, Copy, Pencil, RefreshCcw, Star } from 'lucide-react'
import { useSnackbar } from '../../hooks/useSnackbar'
import { readFavorites, writeFavorites } from '../../services/favorites'
import { copyToClipboard } from '../../services/clipboard'
import ChatEditBox from './ChatEditBox'

interface Props {
  content: string
  onResend: (text: string) => void
}

export default function ChatMessage({ content, onResend }: Props) {
  const [editing, setEditing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [faved, setFaved] = useState(() => readFavorites().includes(content))
  const { showSnackbar } = useSnackbar()

  const handleCopy = useCallback(() => {
    copyToClipboard(content)
      .then(() => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
      })
      .catch(() => showSnackbar('复制失败，请稍后重试', 'error'))
  }, [content, showSnackbar])

  const toggleFav = useCallback(() => {
    const favs = readFavorites()
    const next = faved ? favs.filter((f) => f !== content) : [...favs, content]
    writeFavorites(next)
    setFaved(!faved)
    showSnackbar(faved ? '已取消收藏' : '已收藏', 'success')
  }, [content, faved, showSnackbar])

  const startEdit = useCallback(() => setEditing(true), [])
  const cancelEdit = useCallback(() => setEditing(false), [])
  const sendDraft = useCallback((draft: string) => {
    setEditing(false)
    onResend(draft)
  }, [onResend])
  const resend = useCallback(() => onResend(content), [content, onResend])

  if (editing) {
    return <ChatEditBox content={content} onCancel={cancelEdit} onSend={sendDraft} />
  }

  return (
    <div className="flex flex-col items-end group">
      <div className="bg-primary text-white rounded-2xl rounded-br-md px-4 py-2.5 max-w-[70%] text-sm leading-relaxed break-words">
        {content}
      </div>
      <div className="flex gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="收藏" onClick={toggleFav}>
          <Star size={13} className={faved ? 'fill-gold text-gold' : ''} />
        </button>
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="编辑" onClick={startEdit}>
          <Pencil size={13} />
        </button>
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="重新发送" onClick={resend}>
          <RefreshCcw size={13} />
        </button>
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="复制" onClick={handleCopy}>
          {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
        </button>
      </div>
    </div>
  )
}
