import type { ReactNode } from 'react'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export interface PageAction {
  label: string
  icon?: ReactNode
  variant?: 'outlined' | 'primary'
  onClick?: () => void
}

interface Props {
  title: string
  subtitle?: string
  onRefresh?: () => void
  onBack?: () => void
  actions?: PageAction[]
  extra?: ReactNode
}

export default function PageTitle({ title, subtitle, onRefresh, onBack, actions = [], extra }: Props) {
  const navigate = useNavigate()
  return (
    <div className="mb-4">
      <div className="flex justify-between items-start flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-1.5 mb-0.5">
            <h2 className="text-2xl font-black tracking-tight text-primary">{title}</h2>
            {!!onRefresh && (
              <div className="tooltip" data-tip="刷新">
                <button onClick={onRefresh} aria-label="刷新"
                  className="btn btn-ghost btn-xs btn-square bg-black/[0.03] hover:bg-primary hover:text-white">
                  <RotateCcw size={16} />
                </button>
              </div>
            )}
          </div>
          {!!subtitle && <p className="text-sm font-medium text-gray-500">{subtitle}</p>}
        </div>
        <div className="flex gap-2 items-center">
          {!!onBack && (
            <button onClick={() => (typeof onBack === 'function' ? onBack() : navigate(-1))} aria-label="返回"
              className="btn btn-ghost btn-sm btn-square rounded-xl hover:bg-primary hover:text-white">
              <ArrowLeft size={18} />
            </button>
          )}
          {actions.map((a) => (
            <button key={a.label} onClick={a.onClick}
              className={`btn whitespace-nowrap px-5 font-bold text-sm ${
                a.variant === 'outlined' ? 'btn-light' : 'btn-primary'}`}>
              {a.icon}
              {a.label}
            </button>
          ))}
          {extra}
        </div>
      </div>
    </div>
  )
}
