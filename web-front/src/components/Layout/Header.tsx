/** 全局顶栏（原型 top-bar）：brand + 消息通知 + 头像下拉（个人信息/版本/退出登录） */

import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../api/modules/auth'

interface Props {
  user: string
}

export default function Header({ user }: Props) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const toggle = useCallback(() => setOpen((v) => !v), [])
  const close = useCallback(() => setOpen(false), [])

  const logout = useCallback(() => {
    authApi.logout()
      .catch(() => undefined)
      .finally(() => {
        localStorage.removeItem('jg_login')
        navigate('/login')
      })
  }, [navigate])

  return (
    <header className="pg-topbar">
      <div className="brand"><i className="fas fa-chart-line" /> 经管之星</div>
      <div className="top-right">
        <div className="icon-btn" title="消息通知"><i className="fas fa-bell" /><span className="badge-dot" /></div>
        <div className="avatar" onClick={toggle}>
          {user ? user.charAt(0) : '管'}
          <div className={`dropdown ${open ? 'show' : ''}`} onClick={(e) => e.stopPropagation()}>
            <div><i className="fas fa-user" /> 个人信息</div>
            <div style={{ color: '#9CA3AF', fontSize: 14, cursor: 'default' }}><i className="fas fa-code-branch" /> v1.0.0</div>
            <div style={{ borderTop: '1px solid #E5E7EB', color: '#E64398' }} onClick={logout}>
              <i className="fas fa-sign-out-alt" /> 退出登录
            </div>
          </div>
        </div>
      </div>
      {open && <div style={{ position: 'fixed', inset: 0, zIndex: 99 }} onClick={close} />}
    </header>
  )
}
