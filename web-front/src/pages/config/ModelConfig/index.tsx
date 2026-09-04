/** 模型配置页：模型列表 + 新增弹窗 + 删除确认 */

import { useCallback, useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import PageHeader from '../../../components/PageHeader'
import { modelsApi } from '../../../api/modules/models'
import { useModelStore } from '../../../store/useModelStore'
import ConfirmDialog from '../../../components/ConfirmDialog'
import { useSnackbar } from '../../../hooks/useSnackbar'
import type { ModelItem } from '../../../types'
import ModelList from './ModelList'
import AddModelModal from './AddModelModal'

export default function ModelConfig() {
  const models = useModelStore((s) => s.items)
  const fetchMethod = useModelStore((s) => s.fetchMethod)
  const [addOpen, setAddOpen] = useState(false)
  const [delFor, setDelFor] = useState<ModelItem | null>(null)
  const [delLoading, setDelLoading] = useState(false)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('模型列表加载失败', 'error'))
  }, [fetchMethod, showSnackbar])

  const openAdd = useCallback(() => setAddOpen(true), [])
  const closeAdd = useCallback(() => setAddOpen(false), [])

  const enable = useCallback((m: ModelItem) => {
    modelsApi.enable(m.id, true)
      .then(() => fetchMethod())
      .then(() => showSnackbar(`已启用「${m.name}」`, 'success'))
      .catch(() => showSnackbar('启用失败，请重试', 'error'))
  }, [fetchMethod, showSnackbar])

  const openDelete = useCallback((m: ModelItem) => setDelFor(m), [])
  const closeDelete = useCallback(() => setDelFor(null), [])

  const submitDelete = useCallback(() => {
    if (!delFor) return
    setDelLoading(true)
    modelsApi.remove(delFor.id)
      .then(() => {
        showSnackbar('模型已删除', 'success')
        setDelFor(null)
        return fetchMethod()
      })
      .catch(() => showSnackbar('删除失败，请重试', 'error'))
      .finally(() => setDelLoading(false))
  }, [delFor, fetchMethod, showSnackbar])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader title="模型配置" subtitle="OpenAI 兼容模型管理；支持 DeepSeek / 火山引擎方舟"
        actions={[{ label: '新增模型', icon: <Plus size={16} />, onClick: openAdd }]} />

      <ModelList models={models} onEnable={enable} onDelete={openDelete} />

      <AddModelModal open={addOpen} onClose={closeAdd} />

      <ConfirmDialog open={!!delFor} title="删除模型" loading={delLoading}
        content={`确定删除模型「${delFor?.name ?? ''}」吗？`}
        onClose={closeDelete} onConfirm={submitDelete} />
    </div>
  )
}
