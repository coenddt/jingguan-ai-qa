/** 全局页头：标语 + 退出登录 */

import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { authApi } from '../../api/modules/auth'

export default function Header() {
  const navigate = useNavigate()

  const logout = useCallback(() => {
    authApi.logout()
      .catch(() => undefined)
      .finally(() => {
        localStorage.removeItem('jg_login')
        navigate('/login')
      })
  }, [navigate])

  return (
    <header className="h-14 shrink-0 bg-white border-b border-gray-200 flex items-center justify-between px-5">
      <div className="text-sm font-bold text-gray-500">让数据问答对话可及——自然语言进，结果直观可见</div>
      <button className="btn btn-ghost btn-sm text-gray-500 whitespace-nowrap gap-1" onClick={logout}>
        <LogOut size={16} /> 退出登录
      </button>
    </header>
  )
}
