import { useState, type FormEvent } from 'react'
import { Sparkles } from 'lucide-react'
import { authApi } from '../api/modules/auth'
import { useSnackbar } from '../hooks/useSnackbar'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { showSnackbar } = useSnackbar()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username || !password) return
    setLoading(true)
    try {
      await authApi.login(username, password)
      localStorage.setItem('jg_login', '1')
      // 整页刷新：让 App 重新执行 /auth/check 以更新登录态（Cookie 已由后端签发）
      window.location.href = '/qa'
    } catch {
      showSnackbar('用户名或密码错误', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f172a] dot-grid flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl gold-gradient flex items-center justify-center text-[#0f172a] mb-4">
            <Sparkles size={28} strokeWidth={1.5} />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">经管之星·AI问数助手</h1>
          <p className="text-white/50 text-sm mt-2">自然语言进，text-to-query 出，结果直观可见</p>
        </div>
        <form onSubmit={submit} className="glass-card rounded-2xl p-8 space-y-4">
          <div>
            <label className="text-sm font-bold text-gray-600 mb-1 block">用户名</label>
            <input className="input input-bordered w-full bg-white" value={username}
              onChange={(e) => setUsername(e.target.value)} autoComplete="username" placeholder="请输入用户名" />
          </div>
          <div>
            <label className="text-sm font-bold text-gray-600 mb-1 block">密码</label>
            <input type="password" className="input input-bordered w-full bg-white" value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="请输入密码" />
          </div>
          <button type="submit" disabled={loading}
            className="btn btn-gold w-full whitespace-nowrap rounded-xl py-3 text-base">
            {loading ? <span className="loading loading-spinner loading-sm" /> : '登 录'}
          </button>
        </form>
      </div>
    </div>
  )
}
