import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import type { SnackbarState } from '../../hooks/useSnackbar'

interface Props {
  snackbar: SnackbarState
  onClose: () => void
}

const ICONS = {
  success: <CheckCircle2 size={18} />,
  error: <AlertCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
} as const

export default function SnackbarAlert({ snackbar, onClose }: Props) {
  if (!snackbar.open) return null
  const alertClass = {
    success: 'alert-success',
    error: 'alert-error',
    warning: 'alert-warning',
    info: 'alert-info',
  }[snackbar.severity]
  return (
    <div className="toast toast-top toast-center z-[100]">
      <div className={`alert ${alertClass} shadow-lg rounded-2xl px-5 py-3 font-bold flex items-center gap-2`}>
        {ICONS[snackbar.severity]}
        <span>{snackbar.message}</span>
        <button className="btn btn-ghost btn-xs btn-square ml-2 whitespace-nowrap" aria-label="关闭提示" onClick={onClose}>
          <X size={14} />
        </button>
      </div>
    </div>
  )
}
