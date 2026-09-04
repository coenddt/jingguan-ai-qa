import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  title?: ReactNode
  /** 标题行间距类，如 'mb-4' */
  headerClassName?: string
  /** 右上角关闭按钮（默认不显示） */
  showClose?: boolean
  children: ReactNode
  footer?: ReactNode
  /** modal-action 追加类，如 'justify-between' */
  footerClassName?: string
  /** modal-box 宽度类，如 'max-w-2xl' */
  boxClassName?: string
}

/** 通用弹窗骨架：遮罩点击关闭 / box 内阻止冒泡 / Portal 挂 body（支持嵌套弹窗） */
export default function Modal({
  open, onClose, title, headerClassName = '', showClose = false,
  children, footer, footerClassName = '', boxClassName = '',
}: Props) {
  if (!open) return null
  const dialog = (
    <dialog className="modal modal-open" onClick={onClose}>
      <div className={`modal-box ${boxClassName}`.trim()} onClick={(e) => e.stopPropagation()}>
        {(title || showClose) && (
          <div className={`flex items-center justify-between gap-2 ${headerClassName}`.trim()}>
            {title}
            {showClose && (
              <button className="btn btn-ghost btn-xs btn-square" aria-label="关闭" onClick={onClose}>
                <X size={16} />
              </button>
            )}
          </div>
        )}
        {children}
        {footer && <div className={`modal-action ${footerClassName}`.trim()}>{footer}</div>}
      </div>
    </dialog>
  )
  return typeof document !== 'undefined' ? createPortal(dialog, document.body) : dialog
}
