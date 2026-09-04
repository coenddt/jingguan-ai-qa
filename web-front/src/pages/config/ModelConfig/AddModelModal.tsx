/** 新增模型弹窗：表单 + 连接测试（表单状态机在 useModelForm） */

import { useCallback } from 'react'
import { FlaskConical } from 'lucide-react'
import Modal from '../../../components/Modal'
import { useModelForm } from '../../../hooks/useModelForm'

interface Props {
  open: boolean
  onClose: () => void
}

export default function AddModelModal({ open, onClose }: Props) {
  const {
    baseUrl, apiKey, modelName, testing, testOk, canTest,
    changeBaseUrl, changeApiKey, changeModelName,
    runTest, submitAdd, resetAdd,
  } = useModelForm()

  const handleClose = useCallback(() => {
    resetAdd()
    onClose()
  }, [resetAdd, onClose])

  return (
    <Modal open={open} onClose={handleClose}
      title={<h3 className="font-bold text-lg">新增模型</h3>} headerClassName="mb-4">
      <div className="space-y-3">
        <div>
          <label className="text-sm font-bold text-gray-600 mb-1 block">Base URL</label>
          <input className="input input-bordered w-full" placeholder="https://api.deepseek.com/v1"
            value={baseUrl} onChange={(e) => changeBaseUrl(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-bold text-gray-600 mb-1 block">API Key</label>
          <input type="password" className="input input-bordered w-full" placeholder="sk-..."
            value={apiKey} onChange={(e) => changeApiKey(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-bold text-gray-600 mb-1 block">模型名称</label>
          <input className="input input-bordered w-full" placeholder="deepseek-chat"
            value={modelName} onChange={(e) => changeModelName(e.target.value)} />
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4">
        <button className="btn btn-outline btn-sm whitespace-nowrap gap-1" disabled={!canTest || testing} onClick={runTest}>
          {testing ? <span className="loading loading-spinner loading-xs" /> : <FlaskConical size={15} />} 测试连接
        </button>
        {testOk && <span className="badge badge-success badge-sm">连接成功</span>}
        <div className="ml-auto flex gap-2">
          <button className="btn btn-ghost btn-sm whitespace-nowrap" onClick={handleClose}>取消</button>
          <button className="btn btn-primary btn-sm whitespace-nowrap" disabled={!testOk} onClick={submitAdd}>添加</button>
        </div>
      </div>
    </Modal>
  )
}
