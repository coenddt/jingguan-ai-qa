/** 新增模型弹窗（原型 mcAddModelModal 1:1：Base URL/API Key/Model Name + 测试连接 + 取消/添加；平台选择为后端必需字段） */

import { useCallback } from 'react'
import Modal from '../../../components/Modal'
import { LLM_PLATFORMS } from '../../../api/modules/models'
import { useModelForm } from '../../../hooks/useModelForm'

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', height: 40, padding: '0 12px', border: '1px solid var(--border)', borderRadius: 6,
  fontSize: 15, outline: 'none', background: 'var(--bg-muted)', color: 'var(--text-body)', boxSizing: 'border-box',
}

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4,
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function AddModelModal({ open, onClose }: Props) {
  const {
    platform, baseUrl, apiKey, modelName, testing, testOk, canTest,
    changePlatform, changeBaseUrl, changeApiKey, changeModelName,
    runTest, submitAdd, resetAdd,
  } = useModelForm()

  const handleClose = useCallback(() => {
    resetAdd()
    onClose()
  }, [resetAdd, onClose])

  const required = <span style={{ color: 'var(--danger)' }}> *</span>

  return (
    <Modal open={open} onClose={handleClose} boxClassName="max-w-[480px]" showClose
      title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-plus-circle mr-1.5" style={{ color: 'var(--primary)' }} />新增模型</h3>}
      footerClassName="justify-between"
      footer={<>
        <button className="btn btn-light btn-sm whitespace-nowrap gap-1" disabled={!canTest || testing} onClick={runTest}>
          {testing ? <span className="loading loading-spinner loading-xs" /> : <i className="fas fa-plug" />} 测试连接
        </button>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-light whitespace-nowrap" onClick={handleClose}>取消</button>
          <button className="btn btn-primary whitespace-nowrap" disabled={!testOk || !baseUrl || !apiKey || !modelName} onClick={submitAdd}>添加</button>
        </div>
      </>}>
      <div style={{ marginBottom: 14 }}>
        <label style={LABEL_STYLE}>平台{required}</label>
        <select style={FIELD_STYLE} value={platform} onChange={(e) => changePlatform(e.target.value)}>
          {LLM_PLATFORMS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>
      <div style={{ marginBottom: 14 }}>
        <label style={LABEL_STYLE}>Base URL{required}</label>
        <input type="text" style={FIELD_STYLE} placeholder="https://api.openai.com/v1"
          value={baseUrl} onChange={(e) => changeBaseUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 14 }}>
        <label style={LABEL_STYLE}>API Key{required}</label>
        <input type="password" style={FIELD_STYLE} placeholder="sk-..."
          value={apiKey} onChange={(e) => changeApiKey(e.target.value)} />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={LABEL_STYLE}>Model Name{required}</label>
        <input type="text" style={FIELD_STYLE} placeholder="gpt-4o"
          value={modelName} onChange={(e) => changeModelName(e.target.value)} />
      </div>
      {testOk && <div style={{ fontSize: 15, color: '#16A34A', minHeight: 20, marginTop: 4 }}>连接成功，可添加</div>}
    </Modal>
  )
}
