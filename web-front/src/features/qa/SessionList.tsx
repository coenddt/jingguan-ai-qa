/** 历史会话侧栏：列表 + 重命名弹窗 + 删除确认 */

import { useCallback } from 'react'
import { MessageSquarePlus, X } from 'lucide-react'
import type { SessionItem } from '../../types'
import ConfirmDialog from '../../components/ConfirmDialog'
import Modal from '../../components/Modal'
import { useSessionStore } from '../../store/useSessionStore'
import { useSessionActions } from '../../hooks/useSessionActions'
import SessionItemRow from './SessionItemRow'

interface Props {
  open: boolean
  activeId: string | null
  onClose: () => void
  onSelect: (id: string) => void
  onNew: () => void
}

export default function SessionList({ open, activeId, onClose, onSelect, onNew }: Props) {
  const sessions = useSessionStore((s) => s.items)
  const handleActiveDeleted = useCallback(() => onSelect(''), [onSelect])
  const actions = useSessionActions(activeId, handleActiveDeleted)

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
          <SessionItemRow key={s.id} session={s} active={s.id === activeId} menuOpen={actions.menuFor === s.id}
            onSelect={onSelect} onToggleMenu={actions.toggleMenu} onTogglePin={actions.togglePin}
            onRename={actions.openRename} onDelete={actions.openDelete} />
        ))}
      </div>

      <Modal open={!!actions.renameFor} onClose={actions.closeRename}
        title={<h3 className="font-bold text-lg">重命名会话</h3>} headerClassName="mb-3"
        footer={<>
          <button className="btn btn-ghost whitespace-nowrap" onClick={actions.closeRename}>取消</button>
          <button className="btn btn-primary whitespace-nowrap" onClick={actions.submitRename}>保存</button>
        </>}>
        <input className="input input-bordered w-full" value={actions.renameText} autoFocus
          onChange={(e) => actions.changeRenameText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void actions.submitRename() }} />
      </Modal>
      <ConfirmDialog open={!!actions.delFor} title="删除会话" loading={actions.delLoading}
        content={`确定删除「${actions.delFor?.title ?? ''}」吗？会话内消息将一并删除。`}
        onClose={actions.closeDelete} onConfirm={actions.submitDelete} />
    </aside>
  )
}
