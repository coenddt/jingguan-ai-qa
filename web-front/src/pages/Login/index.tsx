/** 登录页：品牌区 + 登录表单 */

import { Sparkles } from 'lucide-react'
import LoginForm from './LoginForm'

export default function Login() {
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
        <LoginForm />
      </div>
    </div>
  )
}
