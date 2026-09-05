/** 会话列表项行（原型 qa-sb-item）：置顶标记/标题/悬停菜单 */

import { useCallback } from 'react'
import type { SessionItem } from '../../types'

interface Props {
  session: SessionItem
  active: boolean
  onSelect: (id: string) => void
  /** 打开右键/悬停菜单：上报目标会话与点击坐标，菜单位置/内容由 SessionList 状态渲染 */
  onMenu: (s: SessionItem, x: number, y: number) => void
}

export default function SessionItemRow({ session, active, onSelect, onMenu }: Props) {
  const openMenu = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    onMenu(session, e.clientX, e.clientY)
  }, [session, onMenu])

  return (
    <div className={`qa-sb-item ${session.pinned ? 'pinned' : ''} ${active ? 'active' : ''}`}
      onClick={() => onSelect(session.id)}>
      {session.pinned && <span className="qa-sbi-pin"><i className="fas fa-thumbtack" /></span>}
      <span className="qa-sbi-title">{session.title}</span>
      <button className="qa-sbi-menu" aria-label="会话操作" onClick={openMenu}><i className="fas fa-ellipsis-v" /></button>
    </div>
  )
}
