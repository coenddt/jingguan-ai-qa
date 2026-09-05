/** 全局侧边栏（原型 sidebar）：智能问数 / 系统管理(应用配置、模型配置) / 反馈管理(回复校对)，可收起 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface NavLeaf {
  to: string
  label: string
  icon: string
}

interface NavGroup {
  label: string
  icon: string
  children: NavLeaf[]
}

const LEAF_QA: NavLeaf = { to: '/qa', label: '智能问数', icon: 'fa-robot' }
const GROUP_SYS: NavGroup = {
  label: '系统管理', icon: 'fa-cog',
  children: [
    { to: '/config/app', label: '应用配置', icon: 'fa-sliders' },
    { to: '/config/model', label: '模型配置', icon: 'fa-cube' },
  ],
}
const GROUP_FB: NavGroup = {
  label: '反馈管理', icon: 'fa-flag',
  children: [{ to: '/feedback', label: '回复校对', icon: 'fa-exclamation-circle' }],
}

export default function Sidebar() {
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [openGroups, setOpenGroups] = useState<string[]>([])

  // 当前路由所属分组自动展开
  useEffect(() => {
    const inSys = pathname.startsWith('/config')
    const inFb = pathname.startsWith('/feedback')
    setOpenGroups(() => {
      const next: string[] = []
      if (inSys) next.push(GROUP_SYS.label)
      if (inFb) next.push(GROUP_FB.label)
      return next
    })
  }, [pathname])

  const toggleGroup = useCallback((label: string) => {
    setOpenGroups((prev) => (prev.includes(label) ? prev.filter((g) => g !== label) : [...prev, label]))
  }, [])

  const qaActive = pathname.startsWith('/qa')

  return (
    <aside className={`pg-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-menu">
        <Link to={LEAF_QA.to} className={`menu-item ${qaActive ? 'active' : ''}`}>
          <i className={`fas ${LEAF_QA.icon}`} /><span>{LEAF_QA.label}</span>
        </Link>

        {[GROUP_SYS, GROUP_FB].map((g) => {
          const childActive = g.children.some((c) => pathname.startsWith(c.to))
          const open = openGroups.includes(g.label)
          return (
            <div key={g.label}>
              <div className={`menu-item has-sub ${childActive ? 'active' : ''}`} onClick={() => toggleGroup(g.label)}>
                <i className={`fas ${g.icon}`} /><span>{g.label}</span>
                <i className={`fas fa-chevron-right arrow ${open ? 'open' : ''}`} />
              </div>
              <div className={`sub-menu ${open ? 'open' : ''}`}>
                {g.children.map((c) => (
                  <Link key={c.to} to={c.to}
                    className={`menu-item ${pathname.startsWith(c.to) ? 'active' : ''}`}>
                    <i className={`fas ${c.icon}`} /><span>{c.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          )
        })}
      </div>
      <div className="sidebar-footer">
        <button className="sidebar-toggle" title="收起/展开侧边栏" aria-label="收起/展开侧边栏" onClick={() => setCollapsed((v) => !v)}>
          <i className="fas fa-chevron-left" />
        </button>
      </div>
    </aside>
  )
}
