import { useState } from 'react'
import { Check, Copy, Pencil, RefreshCcw, Star, X } from 'lucide-react'
import { useSnackbar } from '../../hooks/useSnackbar'
import { readFavorites, writeFavorites } from '../../utils/favorites'

interface Props {
  content: string
  onResend: (text: string) => void
}

export default function ChatMessage({ content, onResend }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(content)
  const [copied, setCopied] = useState(false)
  const [faved, setFaved] = useState(readFavorites().includes(content))
  const { showSnackbar } = useSnackbar()

  const copy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const toggleFav = () => {
    const favs = readFavorites()
    const next = faved ? favs.filter((f) => f !== content) : [...favs, content]
    writeFavorites(next)
    setFaved(!faved)
    showSnackbar(faved ? '已取消收藏' : '已收藏', 'success')
  }

  if (editing) {
    return (
      <div className="flex justify-end">
        <div className="bg-white border border-gray-200 rounded-2xl p-3 max-w-[70%] space-y-2">
          <textarea className="textarea textarea-bordered w-full h-24 text-sm" value={draft}
            onChange={(e) => setDraft(e.target.value)} autoFocus />
          <div className="flex gap-2 justify-end">
            <button className="btn btn-ghost btn-xs whitespace-nowrap" onClick={() => { setEditing(false); setDraft(content) }}>
              <X size={13} /> 取消
            </button>
            <button className="btn btn-primary btn-xs whitespace-nowrap" disabled={!draft.trim()}
              onClick={() => { setEditing(false); onResend(draft.trim()) }}>
              重新发送
            </button>
          </div>
        </div>
      </div>
    )
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
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="编辑" onClick={() => setEditing(true)}>
          <Pencil size={13} />
        </button>
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="重新发送" onClick={() => onResend(content)}>
          <RefreshCcw size={13} />
        </button>
        <button className="btn btn-ghost btn-xs btn-square text-gray-400" title="复制" onClick={copy}>
          {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
        </button>
      </div>
    </div>
  )
}
