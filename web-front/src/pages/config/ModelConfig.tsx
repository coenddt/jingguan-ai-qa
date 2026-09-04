import { useEffect, useState } from 'react'
import { FlaskConical, Plus, Trash2 } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import { modelsApi } from '../../api/modules/models'
import { useModelStore } from '../../store/useModelStore'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useSnackbar } from '../../hooks/useSnackbar'
import Modal from '../../components/Modal'
import type { ModelItem } from '../../types'

export default function ModelConfig() {
  const { items: models, fetchMethod } = useModelStore()
  const [addOpen, setAddOpen] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('')
  const [testing, setTesting] = useState(false)
  const [testOk, setTestOk] = useState(false)
  const [delFor, setDelFor] = useState<ModelItem | null>(null)
  const [delLoading, setDelLoading] = useState(false)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('模型列表加载失败', 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resetAdd = () => {
    setAddOpen(false)
    setBaseUrl('')
    setApiKey('')
    setModelName('')
    setTestOk(false)
  }

  const runTest = async () => {
    setTesting(true)
    try {
      const { data } = await modelsApi.test({ baseUrl, apiKey, modelName })
      if (data.ok) {
        setTestOk(true)
        showSnackbar(`连接成功（${data.latency_ms ?? 0}ms），可添加`, 'success')
      } else {
        setTestOk(false)
        showSnackbar(`连接失败：${data.error || '未知错误'}`, 'error')
      }
    } catch {
      showSnackbar('测试请求失败', 'error')
    } finally {
      setTesting(false)
    }
  }

  const submitAdd = async () => {
    if (!testOk) return
    await modelsApi.add({ baseUrl, apiKey, modelName })
    resetAdd()
    await fetchMethod()
    showSnackbar('模型已添加', 'success')
  }

  const enable = async (m: ModelItem) => {
    await modelsApi.enable(m.id, true)
    await fetchMethod()
    showSnackbar(`已启用「${m.name}」`, 'success')
  }

  const submitDelete = async () => {
    if (!delFor) return
    setDelLoading(true)
    try {
      await modelsApi.remove(delFor.id)
      showSnackbar('模型已删除', 'success')
      setDelFor(null)
      await fetchMethod()
    } finally {
      setDelLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader title="模型配置" subtitle="OpenAI 兼容模型管理；DeepSeek 为默认启用项"
        actions={[{ label: '新增模型', icon: <Plus size={16} />, onClick: () => setAddOpen(true) }]} />

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <h3 className="font-black text-gray-700 mb-4">应用模型设置</h3>
        <div className="space-y-2">
          {models.map((m) => (
            <div key={m.id} className="flex items-center gap-3 bg-gray-50 rounded-xl px-4 py-3">
              <div className="flex-1 min-w-0">
                <div className="font-bold text-sm text-gray-700 flex items-center gap-2">
                  {m.name}
                  {m.enabled && <span className="badge badge-success badge-sm">启用中</span>}
                </div>
                <div className="text-xs text-gray-400 truncate">{m.baseUrl} · {m.modelName} · {m.apiKey || 'sk-***'}</div>
              </div>
              {!m.enabled && (
                <button className="btn btn-outline btn-xs whitespace-nowrap" onClick={() => enable(m)}>启用</button>
              )}
              <button className="btn btn-ghost btn-xs btn-square text-error" onClick={() => setDelFor(m)}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <Modal open={addOpen} onClose={resetAdd}
        title={<h3 className="font-bold text-lg">新增模型</h3>} headerClassName="mb-4">
            <div className="space-y-3">
              <div>
                <label className="text-sm font-bold text-gray-600 mb-1 block">Base URL</label>
                <input className="input input-bordered w-full" placeholder="https://api.deepseek.com/v1"
                  value={baseUrl} onChange={(e) => { setBaseUrl(e.target.value); setTestOk(false) }} />
              </div>
              <div>
                <label className="text-sm font-bold text-gray-600 mb-1 block">API Key</label>
                <input type="password" className="input input-bordered w-full" placeholder="sk-..."
                  value={apiKey} onChange={(e) => { setApiKey(e.target.value); setTestOk(false) }} />
              </div>
              <div>
                <label className="text-sm font-bold text-gray-600 mb-1 block">模型名称</label>
                <input className="input input-bordered w-full" placeholder="deepseek-chat"
                  value={modelName} onChange={(e) => { setModelName(e.target.value); setTestOk(false) }} />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <button className="btn btn-outline btn-sm whitespace-nowrap gap-1" disabled={!baseUrl || !apiKey || !modelName || testing} onClick={runTest}>
                {testing ? <span className="loading loading-spinner loading-xs" /> : <FlaskConical size={15} />} 测试连接
              </button>
              {testOk && <span className="badge badge-success badge-sm">连接成功</span>}
              <div className="ml-auto flex gap-2">
                <button className="btn btn-ghost btn-sm whitespace-nowrap" onClick={resetAdd}>取消</button>
                <button className="btn btn-primary btn-sm whitespace-nowrap" disabled={!testOk} onClick={submitAdd}>添加</button>
              </div>
            </div>
      </Modal>

      <ConfirmDialog open={!!delFor} title="删除模型" loading={delLoading}
        content={`确定删除模型「${delFor?.name ?? ''}」吗？`}
        onClose={() => setDelFor(null)} onConfirm={submitDelete} />
    </div>
  )
}
