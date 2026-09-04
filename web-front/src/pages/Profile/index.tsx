/** 个人信息页：展示当前登录账号信息（信息从简，页面保留） */

import Breadcrumb from '../../components/Breadcrumb'

interface Props {
  user: string
}

const ROLE = { name: '系统管理员', color: '#2563EB', bg: '#E8F0FE' }

export default function Profile({ user }: Props) {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      <Breadcrumb />
      <div className="pg-card">
        <div className="flex items-center gap-2 text-lg font-bold text-[#1F2937] mb-6">
          <i className="fas fa-user-circle" style={{ color: ROLE.color }} />
          <span>个人信息</span>
        </div>

        {/* 头像 + 基本身份 */}
        <div className="flex items-center gap-4 mb-6">
          <div
            className="flex items-center justify-center rounded-full text-2xl font-bold text-white"
            style={{ width: 72, height: 72, background: ROLE.color }}
          >
            {user ? user.charAt(0).toUpperCase() : '管'}
          </div>
          <div>
            <div className="text-xl font-bold text-[#1F2937]">{user || 'admin'}</div>
            <span className="mt-1 inline-block px-2 py-0.5 rounded-full text-xs font-semibold"
              style={{ color: ROLE.color, background: ROLE.bg }}>
              {ROLE.name}
            </span>
          </div>
        </div>

        {/* 字段明细 */}
        <dl className="divide-y divide-[#F1F5F9]">
          {[
            { label: '用户名', value: user || 'admin', icon: 'fa-user' },
            { label: '角色', value: ROLE.name, icon: 'fa-shield-alt' },
            { label: '系统', value: '经管之星·AI问数助手', icon: 'fa-chart-line' },
            { label: '版本', value: 'v1.0.0', icon: 'fa-code-branch' },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between py-3">
              <dt className="flex items-center gap-2 text-sm text-[#6B7280]">
                <i className={`fas ${item.icon}`} style={{ width: 16, color: '#9CA3AF' }} />
                {item.label}
              </dt>
              <dd className="text-sm font-semibold text-[#1F2937]">{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}