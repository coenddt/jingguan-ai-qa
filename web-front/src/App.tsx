import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import SnackbarAlert from './components/SnackbarAlert'
import ErrorBoundary from './components/ErrorBoundary'
import { SnackbarContext, useLocalSnackbar } from './hooks/useSnackbar'
import { authApi } from './api/modules/auth'
import Login from './pages/Login'

// 路由级懒加载：页面按需分包，降低首屏 bundle（Qa 含图表，单独 chunk）
const Qa = lazy(() => import('./pages/Qa'))
const AppConfig = lazy(() => import('./pages/config/AppConfig'))
const ModelConfig = lazy(() => import('./pages/config/ModelConfig'))
const Feedback = lazy(() => import('./pages/Feedback'))
const Profile = lazy(() => import('./pages/Profile'))

function Shell({ user }: { user: string }) {
  const location = useLocation()
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header user={user} />
        <main className="flex-1 overflow-auto bg-[#f8fafc]">
          <ErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<div className="p-8 text-sm text-slate-400">页面加载中…</div>}>
              <Routes>
                <Route path="/profile" element={<Profile user={user} />} />
                <Route path="/qa" element={<Qa />} />
                <Route path="/config/app" element={<AppConfig />} />
                <Route path="/config/model" element={<ModelConfig />} />
                <Route path="/feedback" element={<Feedback />} />
                <Route path="*" element={<Navigate to="/qa" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null)
  const [user, setUser] = useState('')
  const navigate = useNavigate()
  const { snackbar, showSnackbar, hideSnackbar } = useLocalSnackbar()

  // 首屏登录态校验：以后端 /auth/check 为准（localStorage 仅"意向"标记）
  useEffect(() => {
    authApi.check()
      .then(({ data }) => {
        setUser(data.user || '')
        setAuthed(true)
      })
      .catch(() => {
        setAuthed(false)
        navigate('/login', { replace: true })
      })
  }, [navigate])

  useEffect(() => {
    const onExpired = () => {
      localStorage.removeItem('jg_login')
      showSnackbar('登录已过期，请重新登录', 'warning')
      navigate('/login', { replace: true })
    }
    window.addEventListener('auth:expired', onExpired)
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [navigate, showSnackbar])

  return (
    <SnackbarContext.Provider value={{ showSnackbar, hideSnackbar }}>
      {authed === false ? (
        <Login />
      ) : (
        <Shell user={user} />
      )}
      <SnackbarAlert snackbar={snackbar} onClose={hideSnackbar} />
    </SnackbarContext.Provider>
  )
}
