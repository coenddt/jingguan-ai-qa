import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

export type SnackbarSeverity = 'success' | 'error' | 'warning' | 'info'

export interface SnackbarState {
  open: boolean
  message: string
  severity: SnackbarSeverity
}

const DURATION: Record<SnackbarSeverity, number> = {
  success: 3000,
  info: 3000,
  warning: 4000,
  error: 5000,
}

export const SnackbarContext = createContext<{
  showSnackbar: (message: string, severity?: SnackbarSeverity) => void
  hideSnackbar: () => void
}>({ showSnackbar: () => undefined, hideSnackbar: () => undefined })

export function useLocalSnackbar() {
  const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: '', severity: 'info' })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showSnackbar = useCallback((message: string, severity: SnackbarSeverity = 'info') => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setSnackbar({ open: true, message, severity })
    timerRef.current = setTimeout(() => setSnackbar((p) => ({ ...p, open: false })), DURATION[severity])
  }, [])

  const hideSnackbar = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setSnackbar((p) => ({ ...p, open: false }))
  }, [])

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }, [])

  return { snackbar, showSnackbar, hideSnackbar }
}

/** 公开 hook — Context 优先（全局单例），兜底局部 state */
export function useSnackbar() {
  const ctx = useContext(SnackbarContext)
  if (ctx) return { snackbar: null, showSnackbar: ctx.showSnackbar, hideSnackbar: ctx.hideSnackbar }
  return useLocalSnackbar()
}
