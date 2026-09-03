import type { ReactNode } from 'react'

export default function LoadingOverlay({ loading, children, message = '加载中...' }: {
  loading: boolean
  children: ReactNode
  message?: string
}) {
  return (
    <div className="relative w-full h-full">
      {children}
      {loading && (
        <div className="absolute inset-0 z-50 bg-white/50 backdrop-blur-sm flex items-center justify-center rounded-inherit">
          <div className="flex flex-col items-center gap-3">
            <span className="loading loading-spinner loading-lg text-primary" />
            <span className="text-xs font-bold text-primary tracking-wider">{message}</span>
          </div>
        </div>
      )}
    </div>
  )
}
