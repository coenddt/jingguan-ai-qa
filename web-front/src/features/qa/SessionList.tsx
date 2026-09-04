import { useState } from 'react'
import { MessageSquarePlus, MoreVertical, Pin, PinOff, SquarePen, Trash2, X } from 'lucide-react'
import type { SessionItem } from '../../types'
import { qaApi } from '../../api/modules/qa'
import ConfirmDialog from '../../components/ConfirmDialog'
import Modal from '../../components/Modal'
import { useSessionStore } from '../../store/useSessionStore'
import { useSnackbar } from '../../hooks/useSnackbar'
import { formatDateTime } from '../../utils/date'

interface Props {
  open: boolean
  activeId: string | null
  onClose: () => void
  onSelect: (id: string) => void
  onNew: () => void
}

export default function SessionList({ open, activeId, onClose, onSelect, onNew }: Props) {
  const { items: sessions, fetchMethod } = useSessionStore()
  const [menuFor, setMenuFor] = useState<string | null>(null)
  const [renameFor, setRenameFor] = useState<SessionItem | null>(null)
  const [renameText, setRenameText] = useState('')
  const [delFor, setDelFor] = useState<SessionItem | null>(null)
  const [delLoading, setDelLoading] = useState(false)
  const { showSnackbar } = useSnackbar()

  const togglePin = async (s: SessionItem) => {
    setMenuFor(null)
    await qaApi.patchSession(s.id, { pinned: !s.pinned })
    await fetchMethod()
  }

  const submitRename = async () => {
    if (!renameFor || !renameText.trim()) return
    await qaApi.patchSession(renameFor.id, { title: renameText.trim() })
    setRenameFor(null)
    await fetchMethod()
  }

  const submitDelete = async () => {
    if (!delFor) return
    setDelLoading(true)
    try {
      await qaApi.deleteSession(delFor.id)
      showSnackbar('会话已删除', 'success')
      setDelFor(null)
      await fetchMethod()
      if (activeId === delFor.id) onSelect('')
    } finally {
      setDelLoading(false)
    }
  }

  if (!open) return null
  return (
    <aside className="w-[240px] shrink-0 h-full bg-white border-r border-gray-200 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="font-bold text-gray-700 text-sm">历史会话</span>
        <button className="btn btn-ghost btn-xs btn-square" onClick={onClose}><X size={15} /></button>
      </div>
      <div className="px-3 py-2">
        <button className="btn btn-primary btn-sm w-full whitespace-nowrap gap-1" onClick={onNew}>
          <MessageSquarePlus size={15} /> 新建会话
        </button>
      </div>
      <div className="flex-1 overflow-auto px-2 pb-2 space-y-1">
        {sessions.map((s) => (
          <div key={s.id}
            className={`group relative rounded-xl px-3 py-2.5 cursor-pointer text-sm ${s.id === activeId ? 'bg-primary/10 text-primary' : 'hover:bg-gray-50 text-gray-600'}`}
            onClick={() => onSelect(s.id)}>
            <div className="flex items-center gap-1.5">
              {s.pinned && <Pin size={12} className="text-gold-deep shrink-0" />}
              <span className="font-bold truncate flex-1">{s.title}</span>
              <button className="btn btn-ghost btn-xs btn-square opacity-0 group-hover:opacity-100"
                onClick={(e) => { e.stopPropagation(); setMenuFor(menuFor === s.id ? null : s.id) }}>
                <MoreVertical size={14} />
              </button>
            </div>
            <div className="text-[11px] text-gray-400 mt-0.5">{formatDateTime(s.updatedAt)} · {s.msgCount} 条</div>
            {menuFor === s.id && (
              <div className="absolute right-2 top-9 z-20 bg-white border border-gray-200 rounded-xl shadow-lg py-1 w-32"
                onClick={(e) => e.stopPropagation()}>
                <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2"
                  onClick={() => togglePin(s)}>
                  {s.pinned ? <><PinOff size={13} /> 取消置顶</> : <><Pin size={13} /> 置顶</>}
                </button>
                <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2"
                  onClick={() => { setMenuFor(null); setRenameFor(s); setRenameText(s.title) }}>
                  <SquarePen size={13} /> 重命名
                </button>
                <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2 text-error"
                  onClick={() => { setMenuFor(null); setDelFor(s) }}>
                  <Trash2 size={13} /> 删除
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <Modal open={!!renameFor} onClose={() => setRenameFor(null)}
        title={<h3 className="font-bold text-lg">重命名会话</h3>} headerClassName="mb-3"
        footer={<>
          <button className="btn btn-ghost whitespace-nowrap" onClick={() => setRenameFor(null)}>取消</button>
          <button className="btn btn-primary whitespace-nowrap" onClick={submitRename}>保存</button>
        </>}>
            <input className="input input-bordered w-full" value={renameText} autoFocus
              onChange={(e) => setRenameText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitRename()} />
      </Modal>
      <ConfirmDialog open={!!delFor} title="删除会话" loading={delLoading}
        content={`确定删除「${delFor?.title ?? ''}」吗？会话内消息将一并删除。`}
        onClose={() => setDelFor(null)} onConfirm={submitDelete} />
    </aside>
  )
}
