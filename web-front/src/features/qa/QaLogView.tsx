/** 问数日志视图（原型 qaLogView）：时间/用户/关键字筛选 + 会话记录表 + 会话详情弹窗 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { MsgItem, SessionItem } from '../../types'
import { qaApi } from '../../api/modules/qa'
import { useSessionStore } from '../../store/useSessionStore'
import { useModelStore } from '../../store/useModelStore'
import { useSnackbar } from '../../hooks/useSnackbar'
import { copyToClipboard } from '../../services/clipboard'
import Modal from '../../components/Modal'
import { formatDateTime } from '../../utils/date'

const TIME_OPTIONS = [
  { value: 7, label: '过去7天' },
  { value: 30, label: '过去30天' },
  { value: 90, label: '过去90天' },
  { value: 0, label: '全部' },
]

interface Props {
  onBack: () => void
  onOpenSession: (id: string) => void
}

export default function QaLogView({ onBack, onOpenSession }: Props) {
  const sessions = useSessionStore((s) => s.items)
  const fetchSessions = useSessionStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()
  const [days, setDays] = useState(7)
  const [userF, setUserF] = useState('all')
  const [kw, setKw] = useState('')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    fetchSessions().catch(() => showSnackbar('日志加载失败，请稍后重试', 'error'))
  }, [fetchSessions, showSnackbar])

  const users = useMemo(
    () => Array.from(new Set(sessions.map((s) => s.userName).filter(Boolean))),
    [sessions],
  )

  const rows = useMemo(() => {
    const now = Date.now()
    return sessions.filter((s) => {
      if (days > 0 && new Date(s.createdAt || s.updatedAt).getTime() < now - days * 86400_000) return false
      if (userF !== 'all' && s.userName !== userF) return false
      if (kw && !s.title.toLowerCase().includes(kw.toLowerCase())) return false
      return true
    })
  }, [sessions, days, userF, kw])

  const refresh = useCallback(() => {
    setTick((v) => v + 1)
    fetchSessions().catch(() => showSnackbar('日志刷新失败，请稍后重试', 'error'))
  }, [fetchSessions, showSnackbar])

  return (
    <div className="flex flex-col flex-1 min-h-0" key={tick}>
      {/* 独立头部（原型 qa-chat-hdr）：日志标题 + 返回 */}
      <div className="qa-chat-hdr">
        <span className="qa-chat-title"><i className="fas fa-clock" style={{ color: 'var(--primary)', marginRight: 4 }} /> 日志</span>
        <div className="qa-chat-actions">
          <button className="btn btn-text btn-sm whitespace-nowrap" onClick={onBack}>
            <i className="fas fa-arrow-left" /> 返回
          </button>
        </div>
      </div>
      <div className="qa-log-filters">
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {TIME_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={userF} onChange={(e) => setUserF(e.target.value)}>
          <option value="all">全部用户</option>
          {users.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        <div className="pg-search" style={{ maxWidth: 200 }}>
          <i className="fas fa-search" />
          <input type="text" placeholder="搜索标题..." value={kw} onChange={(e) => setKw(e.target.value)} />
        </div>
        <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1 text-gray-500" onClick={refresh}>
          <i className="fas fa-sync-alt" /> 刷新
        </button>
        <span className="qa-log-count">共 <strong>{rows.length}</strong> 条</span>
      </div>
      <div className="flex-1 overflow-auto px-5 pb-4">
        <div className="pg-table-wrap">
          <table className="pg-data-table">
            <thead>
              <tr>
                <th style={{ width: 200 }}>标题</th>
                <th style={{ width: 80 }}>用户</th>
                <th style={{ width: 60 }}>消息数</th>
                <th style={{ width: 80 }}>用户反馈</th>
                <th style={{ width: 80 }}>管理员反馈</th>
                <th style={{ width: 140 }}>更新时间</th>
                <th style={{ width: 140 }}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 50).map((s) => (
                <tr key={s.id} className="row-click" onClick={() => onOpenSession(s.id)}>
                  <td>{s.title}</td>
                  <td>{s.userName}</td>
                  <td>{s.msgCount}</td>
                  <td>{s.userFeedback || '-'}</td>
                  <td>{s.adminFeedback || '-'}</td>
                  <td>{formatDateTime(s.updatedAt)}</td>
                  <td>{formatDateTime(s.createdAt)}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: '#9CA3AF' }}>暂无问数记录</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

/** 会话详情弹窗（原型 qa-detail-panel 头部 1:1：标题 + 可复制 ID + 模型徽标） */
export function QaDetailModal({ session, onClose }: { session: SessionItem | null; onClose: () => void }) {
  const [msgs, setMsgs] = useState<MsgItem[]>([])
  const models = useModelStore((s) => s.items)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    if (!session) {
      setMsgs([])
      return
    }
    qaApi.listMessages(session.id)
      .then(({ data }) => setMsgs(data))
      .catch(() => showSnackbar('会话消息加载失败', 'error'))
  }, [session, showSnackbar])

  const modelName = useMemo(
    () => models.find((m) => m.enabled)?.name || '',
    [models],
  )

  const copyId = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!session) return
    const el = e.currentTarget.querySelector('i')
    copyToClipboard(session.id).then(() => {
      if (el) {
        el.className = 'fas fa-check'
        window.setTimeout(() => { el.className = 'fas fa-copy' }, 1500)
      }
    }).catch(() => showSnackbar('复制失败，请稍后重试', 'error'))
  }, [session, showSnackbar])

  const copyText = useCallback((t: string, el: HTMLElement) => {
    copyToClipboard(t).then(() => {
      el.textContent = '已复制'
      window.setTimeout(() => { el.textContent = '' }, 1500)
    }).catch(() => showSnackbar('复制失败，请稍后重试', 'error'))
  }, [showSnackbar])

  if (!session) return null

  return (
    <Modal open onClose={onClose} boxClassName="max-w-3xl" showClose
      title={
        <div className="flex items-center justify-between flex-1 min-w-0 gap-3">
          <div className="min-w-0">
            <div className="qa-dh-title">{session.title}</div>
            <div className="qa-dh-id" title="点击复制" onClick={copyId}>
              <span>ID: {session.id}</span> <i className="fas fa-copy" style={{ fontSize: 12 }} />
            </div>
          </div>
          {!!modelName && <span className="qa-dh-model">{modelName}</span>}
        </div>
      }>
      <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
        {msgs.map((m) => m.role === 'user' ? (
          <div key={m.id} className="flex justify-end">
            <div className="qa-user-bubble" style={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
              <span style={{ flex: 1 }}>{m.content}</span>
              <span className="qa-copy-btn" title="复制" style={{ cursor: 'pointer', color: '#9CA3AF', fontSize: 13 }}
                onClick={(e) => copyText(m.content, e.currentTarget)}>
                <i className="fas fa-copy" />
              </span>
            </div>
          </div>
        ) : (
          <div key={m.id} className="flex gap-2.5">
            <div className="qa-ai-avatar" style={{ width: 28, height: 28, fontSize: 13 }}><i className="fas fa-robot" /></div>
            <div className="qa-ai-card" style={{ padding: '10px 14px' }}>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{m.content}</p>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  )
}
