import { Link, useLocation } from 'react-router-dom'
import { MessageSquareText, Settings2, ShieldCheck, Sparkles, Cpu } from 'lucide-react'

const NAV = [
  { to: '/qa', label: '智能问数', icon: <MessageSquareText size={20} strokeWidth={1.5} /> },
  { to: '/config/app', label: '应用配置', icon: <Settings2 size={20} strokeWidth={1.5} /> },
  { to: '/config/model', label: '模型配置', icon: <Cpu size={20} strokeWidth={1.5} /> },
  { to: '/feedback', label: '回复校对', icon: <ShieldCheck size={20} strokeWidth={1.5} /> },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  return (
    <aside className="w-[220px] shrink-0 h-screen bg-gradient-to-b from-[#0f172a] to-[#1a3a6c] text-white/85 flex flex-col">
      <div className="flex items-center gap-2.5 px-5 py-6">
        <div className="w-9 h-9 rounded-xl gold-gradient flex items-center justify-center text-[#0f172a]">
          <Sparkles size={20} strokeWidth={1.5} />
        </div>
        <div>
          <div className="font-black text-white leading-tight">经管之星</div>
          <div className="text-[11px] text-white/50">AI 问数助手</div>
        </div>
      </div>
      <nav className="flex-1 px-3 space-y-1">
        {NAV.map((n) => {
          const active = pathname.startsWith(n.to) && (n.to !== '/config/app' || pathname === '/config/app') && (n.to !== '/config/model' || pathname === '/config/model')
          return (
            <Link key={n.to} to={n.to}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm whitespace-nowrap transition-colors ${
                active ? 'bg-white/10 text-white' : 'text-white/60 hover:bg-white/5 hover:text-white'}`}>
              {n.icon}
              {n.label}
            </Link>
          )
        })}
      </nav>
      <div className="px-5 py-4 text-[11px] text-white/40">让数据问答对话可及</div>
    </aside>
  )
}
