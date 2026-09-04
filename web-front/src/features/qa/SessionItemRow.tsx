/** 会话列表项行（原型 qa-sb-item）：置顶标记/标题/悬停菜单 */

import { useCallback } from 'react'
import type { SessionItem } from '../../types'

interface Props {
  session: SessionItem
  active: boolean
  onSelect: (id: string) => void
  onRename: (s: SessionItem) => void
  onDelete: (s: SessionItem) => void
}

export default function SessionItemRow({ session, active, onSelect, onRename, onDelete }: Props) {
  const openMenu = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    const menu = document.getElementById('qaCtxMenu')
    if (!menu) return
    menu.setAttribute('data-id', session.id)
    const x = Math.min(e.clientX, window.innerWidth - 150)
    const y = Math.min(e.clientY, window.innerHeight - 130)
    menu.style.left = `${x}px`
    menu.style.top = `${y}px`
    menu.classList.add('show')
    const pinBtn = menu.querySelector('#qaCtxPin')
    if (pinBtn) {
      pinBtn.innerHTML = `<i class="fas fa-thumbtack"></i> ${session.pinned ? '取消置顶' : '置顶'}`
    }
  }, [session.id, session.pinned])

  return (
    <div className={`qa-sb-item ${session.pinned ? 'pinned' : ''} ${active ? 'active' : ''}`}
      onClick={() => onSelect(session.id)}>
      {session.pinned && <span className="qa-sbi-pin"><i className="fas fa-thumbtack" /></span>}
      <span className="qa-sbi-title">{session.title}</span>
      <button className="qa-sbi-menu" onClick={openMenu}><i className="fas fa-ellipsis-v" /></button>
    </div>
  )
}
