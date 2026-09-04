import { Link as RouterLink, useLocation } from 'react-router-dom'

const ROUTE_LABELS: Record<string, string> = {
  config: '系统管理',
  app: '应用配置',
  model: '模型配置',
  feedback: '回复校对',
  profile: '个人信息',
}

export default function Breadcrumb() {
  const location = useLocation()
  const segs = location.pathname.split('/').filter(Boolean)
  return (
    <div className="breadcrumbs text-sm">
      <ul>
        {segs.map((s, i) => {
          const last = i === segs.length - 1
          const label = ROUTE_LABELS[s] || s
          return (
            <li key={s} className={last ? 'text-xs font-bold text-primary' : ''}>
              {last ? label : (
                <RouterLink to={`/${segs.slice(0, i + 1).join('/')}`}
                  className="text-xs font-semibold text-gray-500 hover:text-primary">
                  {label}
                </RouterLink>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
