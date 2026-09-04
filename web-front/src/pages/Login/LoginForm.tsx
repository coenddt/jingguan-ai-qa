/** 登录表单（原型 login-right 表单 1:1：图标输入框 + 主色登录按钮 + 行内错误提示） */

import { useCallback, useState, type FormEvent } from 'react'
import { authApi } from '../../api/modules/auth'

export default function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = useCallback((e: FormEvent) => {
    e.preventDefault()
    if (!username || !password || loading) return
    setLoading(true)
    setError('')
    authApi.login(username, password)
      .then(() => {
        localStorage.setItem('jg_login', '1')
        // 整页刷新：让 App 重新执行 /auth/check 以更新登录态（Cookie 已由后端签发）
        window.location.href = '/qa'
      })
      .catch(() => setError('用户名或密码错误'))
      .finally(() => setLoading(false))
  }, [username, password, loading])

  return (
    <form onSubmit={submit}>
      <div className="form-group">
        <label>用户名</label>
        <div className="input-wrap">
          <i className="fas fa-user" />
          <input value={username} onChange={(e) => setUsername(e.target.value)}
            autoComplete="username" placeholder="请输入用户名" />
        </div>
      </div>
      <div className="form-group">
        <label>密码</label>
        <div className="input-wrap">
          <i className="fas fa-lock" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password" placeholder="请输入密码" />
        </div>
        {error && <div className="error-msg">{error}</div>}
      </div>
      <button type="submit" className="btn-login" disabled={loading || !username || !password}>
        {loading ? <span className="loading loading-spinner loading-sm" /> : <><i className="fas fa-sign-in-alt" /> 登 录</>}
      </button>
    </form>
  )
}
