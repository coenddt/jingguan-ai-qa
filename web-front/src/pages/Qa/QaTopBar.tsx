/** 问数页顶栏：会话列表开关 + 当前会话标题 */

import { PanelLeftOpen } from 'lucide-react'

interface Props {
  title: string
  listOpen: boolean
  onOpenList: () => void
}

export default function QaTopBar({ title, listOpen, onOpenList }: Props) {
  return (
    <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-200 bg-white/70">
      {!listOpen && (
        <button className="btn btn-ghost btn-sm btn-square" title="会话列表" onClick={onOpenList}>
          <PanelLeftOpen size={18} />
        </button>
      )}
      <span className="font-bold text-gray-700 text-sm">{title}</span>
    </div>
  )
}
