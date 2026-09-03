import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AlertTriangle, HelpCircle, Loader2 } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  onConfirm: () => Promise<void> | void
  title?: string
  content?: ReactNode
  confirmText?: string
  cancelText?: string
  confirmColor?: 'error' | 'primary'
  loading?: boolean
}

export default function ConfirmDialog({
  open, onClose, onConfirm, title = '确认操作',
  content, confirmText = '确认执行', cancelText = '取消',
  confirmColor = 'error', loading = false,
}: Props) {
  if (!open) return null
  const isError = confirmColor === 'error'
  const dialog = (
    <dialog className="modal modal-open" onClick={loading ? undefined : onClose}>
      <div className="modal-box rounded-2xl max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2.5 pb-2 pt-1">
          <div className={`p-1.5 rounded-2xl flex shadow-sm ${isError ? 'bg-error/15 text-error' : 'bg-primary/15 text-primary'}`}>
            {isError ? <AlertTriangle size={26} /> : <HelpCircle size={26} />}
          </div>
          <h3 className="text-xl font-black text-primary tracking-tight">{title}</h3>
        </div>
        <div className="pb-4 px-1">
          {content || <p className="text-gray-500 font-medium leading-relaxed">您确定要执行此操作吗？此操作可能无法撤销。</p>}
        </div>
        <div className="modal-action mt-0 px-1 pb-1 gap-2 flex">
          <button onClick={onClose} disabled={loading}
            className="btn btn-outline flex-1 whitespace-nowrap font-bold text-gray-500">
            {cancelText}
          </button>
          <button
            onClick={async () => {
              await onConfirm()
              if (!loading) onClose()
            }}
            disabled={loading}
            className={`btn flex-[1.5] whitespace-nowrap font-bold ${isError ? 'btn-error' : 'btn-primary'}`}
          >
            {loading ? <><Loader2 size={14} className="animate-spin" /> 处理中</> : confirmText}
          </button>
        </div>
      </div>
    </dialog>
  )
  return typeof document !== 'undefined' ? createPortal(dialog, document.body) : dialog
}
