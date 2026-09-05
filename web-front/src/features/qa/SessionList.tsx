/** 历史会话侧栏（原型 qa-sidebar 1:1）：近30天记录 + 开启新对话 + 会话列表 + 悬停菜单 */

import { useCallback, useEffect, useState } from 'react'
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

/** 悬停菜单状态：目标会话 + 定位坐标（状态驱动渲染，替代原 DOM class/data-id 操纵） */
interface CtxMenu {
  session: SessionItem
  x: number
  y: number
}

export default function SessionList({ open, activeId, onClose, onSelect, onNew }: Props) {
  const sessions = useSessionStore((s) => s.items)
  const handleActiveDeleted = useCallback(() => onSelect(''), [onSelect])
  const actions = useSessionActions(activeId, handleActiveDeleted)
  const [ctxMenu, setCtxMenu] = useState<CtxMenu | null>(null)

  const openCtxMenu = useCallback((session: SessionItem, x: number, y: number) => {
    setCtxMenu({ session, x: Math.min(x, window.innerWidth - 150), y: Math.min(y, window.innerHeight - 130) })
  }, [])

  // 点击菜单/触发按钮外部关闭悬停菜单
  useEffect(() => {
    if (!open || !ctxMenu) return
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement
      if (!t.closest('.qa-sb-ctx-menu') && !t.closest('.qa-sbi-menu')) setCtxMenu(null)
    }
    document.addEventListener('click', onDocClick)
    return () => document.removeEventListener('click', onDocClick)
  }, [open, ctxMenu])

  const ctxPin = useCallback(() => {
    if (ctxMenu) void actions.togglePin(ctxMenu.session)
    setCtxMenu(null)
  }, [ctxMenu, actions])

  const ctxRename = useCallback(() => {
    if (ctxMenu) actions.openRename(ctxMenu.session)
    setCtxMenu(null)
  }, [ctxMenu, actions])

  const ctxDelete = useCallback(() => {
    if (ctxMenu) actions.openDelete(ctxMenu.session)
    setCtxMenu(null)
  }, [ctxMenu, actions])

  if (!open) return null

  return (
    <aside className="qa-sidebar" style={{ borderRadius: 0 }}>
      <div className="qa-sb-top">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="qa-sb-collapse" title="收起侧栏" aria-label="收起侧栏" onClick={onClose}>
            <i className="fas fa-chevron-left" />
          </button>
          <span className="qa-sb-title">近30天记录</span>
        </div>
      </div>
      <button className="qa-sb-newchat" onClick={onNew}><i className="fas fa-plus" /> 开启新对话</button>
      <div className="qa-sb-list">
        {sessions.map((s) => (
          <SessionItemRow key={s.id} session={s} active={s.id === activeId}
            onSelect={onSelect} onMenu={openCtxMenu} />
        ))}
      </div>

      {/* 会话悬停菜单（原型 qaCtxMenu，状态驱动条件渲染） */}
      {ctxMenu && (
        <div className="qa-sb-ctx-menu show" style={{ left: ctxMenu.x, top: ctxMenu.y }}>
          <button className="ctx-item" onClick={ctxPin}>
            <i className="fas fa-thumbtack" /> {ctxMenu.session.pinned ? '取消置顶' : '置顶'}
          </button>
          <button className="ctx-item" onClick={ctxRename}><i className="fas fa-edit" /> 重命名</button>
          <button className="ctx-item ctx-danger" onClick={ctxDelete}><i className="fas fa-trash" /> 删除</button>
        </div>
      )}

      <Modal open={!!actions.renameFor} onClose={actions.closeRename}
        title={<h3 className="font-bold text-lg">重命名会话</h3>} headerClassName="mb-3"
        footer={<>
          <button className="btn btn-light whitespace-nowrap" onClick={actions.closeRename}>取消</button>
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
