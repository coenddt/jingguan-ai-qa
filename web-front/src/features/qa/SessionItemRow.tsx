/** 会话列表项行：标题/置顶标记/元信息 + 悬停操作菜单 */

import { MoreVertical, Pin, PinOff, SquarePen, Trash2 } from 'lucide-react'
import type { SessionItem } from '../../types'
import { formatDateTime } from '../../utils/date'

interface Props {
  session: SessionItem
  active: boolean
  menuOpen: boolean
  onSelect: (id: string) => void
  onToggleMenu: (id: string) => void
  onTogglePin: (s: SessionItem) => void
  onRename: (s: SessionItem) => void
  onDelete: (s: SessionItem) => void
}

export default function SessionItemRow({
  session, active, menuOpen, onSelect, onToggleMenu, onTogglePin, onRename, onDelete,
}: Props) {
  return (
    <div
      className={`group relative rounded-xl px-3 py-2.5 cursor-pointer text-sm ${active ? 'bg-primary/10 text-primary' : 'hover:bg-gray-50 text-gray-600'}`}
      onClick={() => onSelect(session.id)}>
      <div className="flex items-center gap-1.5">
        {session.pinned && <Pin size={12} className="text-gold-deep shrink-0" />}
        <span className="font-bold truncate flex-1">{session.title}</span>
        <button className="btn btn-ghost btn-xs btn-square opacity-0 group-hover:opacity-100"
          onClick={(e) => { e.stopPropagation(); onToggleMenu(session.id) }}>
          <MoreVertical size={14} />
        </button>
      </div>
      <div className="text-[11px] text-gray-400 mt-0.5">{formatDateTime(session.updatedAt)} · {session.msgCount} 条</div>
      {menuOpen && (
        <div className="absolute right-2 top-9 z-20 bg-white border border-gray-200 rounded-xl shadow-lg py-1 w-32"
          onClick={(e) => e.stopPropagation()}>
          <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2"
            onClick={() => onTogglePin(session)}>
            {session.pinned ? <><PinOff size={13} /> 取消置顶</> : <><Pin size={13} /> 置顶</>}
          </button>
          <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2"
            onClick={() => onRename(session)}>
            <SquarePen size={13} /> 重命名
          </button>
          <button className="btn btn-ghost btn-sm w-full justify-start whitespace-nowrap gap-2 text-error"
            onClick={() => onDelete(session)}>
            <Trash2 size={13} /> 删除
          </button>
        </div>
      )}
    </div>
  )
}
