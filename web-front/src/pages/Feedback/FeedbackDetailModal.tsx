/** 反馈处理弹窗（原型 feedbackRemarkModal 1:1：左栏 用户提问/AI回复，右栏 处理状态/处理备注，底部 取消/确认） */

import { useCallback, useEffect, useState } from 'react'
import type { FeedbackItem } from '../../types'
import Modal from '../../components/Modal'
import { feedbackApi } from '../../api/modules/feedback'
import { useSnackbar } from '../../hooks/useSnackbar'

interface Props {
  detail: FeedbackItem | null
  onClose: () => void
  onSaved: () => void
}

const LABEL: React.CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--text-body)', display: 'block', marginBottom: 6 }
const FIELD: React.CSSProperties = {
  width: '100', padding: '0 10px', border: '1px solid #D1D5DB', borderRadius: 6,
  fontSize: 14, outline: 'none', background: '#FAFBFC', color: 'var(--text-body)', boxSizing: 'border-box',
}

export default function FeedbackDetailModal({ detail, onClose, onSaved }: Props) {
  const { showSnackbar } = useSnackbar()
  const [status, setStatus] = useState('待处理')
  const [remark, setRemark] = useState('')
  const [saving, setSaving] = useState(false)

  // 打开时回填当前反馈的处理状态与备注
  useEffect(() => {
    if (detail) {
      setStatus(detail.status || '待处理')
      setRemark(detail.remark || '')
    }
  }, [detail])

  const changeStatus = useCallback((v: string) => setStatus(v), [])
  const changeRemark = useCallback((v: string) => setRemark(v), [])

  const submit = useCallback(() => {
    if (!detail) return
    setSaving(true)
    feedbackApi.update(detail.id, { status, remark: remark.trim() })
      .then(() => {
        showSnackbar('处理已保存', 'success')
        onClose()
        onSaved()
      })
      .catch(() => showSnackbar('保存失败，请重试', 'error'))
      .finally(() => setSaving(false))
  }, [detail, status, remark, showSnackbar, onClose, onSaved])

  return (
    <Modal open={!!detail} onClose={onClose} boxClassName="max-w-[720px]" showClose
      title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-pen mr-1.5" style={{ color: '#2563EB' }} />反馈处理</h3>}
      footer={<>
        <button className="btn btn-light whitespace-nowrap" onClick={onClose}>取消</button>
        <button className="btn btn-primary whitespace-nowrap" disabled={saving} onClick={submit}>
          <i className="fas fa-check" /> 确认
        </button>
      </>}>
      {detail && (
        <div style={{ display: 'flex', gap: 20 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>用户提问</label>
              <div style={{ background: '#F9FAFB', padding: '10px 12px', borderRadius: 8, fontSize: 15, color: '#374151', lineHeight: 1.5 }}>
                {detail.question}
              </div>
            </div>
            <div>
              <label style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>AI回复</label>
              <div style={{ background: '#FFF8F0', border: '1px solid #FDE68A', borderRadius: 8, padding: '10px 12px', fontSize: 15, color: '#92400E', lineHeight: 1.5, maxHeight: 200, overflow: 'auto' }}>
                {detail.answer || '（暂无AI回复数据）'}
              </div>
            </div>
          </div>
          <div style={{ width: 220, flexShrink: 0 }}>
            <div style={{ marginBottom: 14 }}>
              <label style={LABEL}>处理状态</label>
              <select value={status} onChange={(e) => changeStatus(e.target.value)}
                style={{ ...FIELD, height: 36 }}>
                <option value="待处理">待处理</option>
                <option value="已处理">已处理</option>
              </select>
            </div>
            <div>
              <label style={LABEL}>处理备注</label>
              <textarea value={remark} onChange={(e) => changeRemark(e.target.value)} placeholder="请填写处理备注…"
                style={{ width: '100%', height: 180, padding: 10, border: '1px solid #D1D5DB', borderRadius: 6, fontSize: 15, resize: 'vertical', outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit', background: '#FAFBFC', color: 'var(--text-body)' }} />
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}
