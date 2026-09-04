/** 用户消息气泡（原型 qa-user-msg）：编辑 / 重新发送 / 收藏 / 复制 */

import { useCallback, useState } from 'react'
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
    showSnackbar(faved ? '已取消收藏' : '问题已收藏', 'success')
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
    <div className="qa-user-msg">
      <div className="qa-user-bubble">{content}</div>
      <div className="qa-user-actions">
        <button data-title="收藏" onClick={toggleFav}>
          <i className="fas fa-star" style={faved ? { color: '#F59E0B' } : undefined} />
        </button>
        <button data-title="编辑" onClick={startEdit}>
          <i className="fas fa-pen" />
        </button>
        <button data-title="重新发送" onClick={resend}>
          <i className="fas fa-sync-alt" />
        </button>
        <button data-title="复制" onClick={handleCopy}>
          <i className={copied ? 'fas fa-check' : 'fas fa-copy'} style={copied ? { color: '#16A34A' } : undefined} />
        </button>
      </div>
    </div>
  )
}
