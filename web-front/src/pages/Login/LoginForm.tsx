/** 登录表单块（Login 页使用） */

import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react'
import { authApi } from '../../api/modules/auth'
import { useSnackbar } from '../../hooks/useSnackbar'

export default function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { showSnackbar } = useSnackbar()

  const submit = useCallback((e: FormEvent) => {
    e.preventDefault()
    if (!username || !password || loading) return
    setLoading(true)
    authApi.login(username, password)
      .then(() => {
        localStorage.setItem('jg_login', '1')
        // 整页刷新：让 App 重新执行 /auth/check 以更新登录态（Cookie 已由后端签发）
        window.location.href = '/qa'
      })
      .catch(() => showSnackbar('用户名或密码错误', 'error'))
      .finally(() => setLoading(false))
  }, [username, password, loading, showSnackbar])

  return (
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
  )
}
