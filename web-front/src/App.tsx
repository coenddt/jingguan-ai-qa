import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import SnackbarAlert from './components/SnackbarAlert'
import { SnackbarContext, useLocalSnackbar } from './hooks/useSnackbar'
import { authApi } from './api/modules/auth'
import Login from './pages/Login'
import Qa from './pages/Qa'
import AppConfig from './pages/config/AppConfig'
import ModelConfig from './pages/config/ModelConfig'
import Feedback from './pages/Feedback'
import Profile from './pages/Profile'

function Shell({ user }: { user: string }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header user={user} />
        <main className="flex-1 overflow-auto bg-[#f8fafc]">
          <Routes>
            <Route path="/profile" element={<Profile user={user} />} />
            <Route path="/qa" element={<Qa />} />
            <Route path="/config/app" element={<AppConfig />} />
            <Route path="/config/model" element={<ModelConfig />} />
            <Route path="/feedback" element={<Feedback />} />
            <Route path="*" element={<Navigate to="/qa" replace />} />
          </Routes>
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
