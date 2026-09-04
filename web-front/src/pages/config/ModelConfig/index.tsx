/** 模型配置页（原型 page-sys-model 1:1）：应用模型设置卡片 + 模型选择 + 新增模型弹窗 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import Breadcrumb from '../../../components/Breadcrumb'
import { modelsApi } from '../../../api/modules/models'
import { useModelStore } from '../../../store/useModelStore'
import { useSnackbar } from '../../../hooks/useSnackbar'
import AddModelModal from './AddModelModal'

export default function ModelConfig() {
  const models = useModelStore((s) => s.items)
  const fetchMethod = useModelStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()
  const [addOpen, setAddOpen] = useState(false)
  const [selected, setSelected] = useState('')

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('模型列表加载失败', 'error'))
  }, [fetchMethod, showSnackbar])

  // 默认选中当前启用模型
  useEffect(() => {
    setSelected((prev) => prev || models.find((m) => m.enabled)?.id || '')
  }, [models])

  const changeSelect = useCallback((v: string) => {
    if (v === '__add__') {
      setAddOpen(true)
      return
    }
    setSelected(v)
  }, [])

  const saveConfig = useCallback(() => {
    if (!selected) {
      showSnackbar('请先选择模型', 'error')
      return
    }
    const name = models.find((m) => m.id === selected)?.name || ''
    modelsApi.enable(selected, true)
      .then(() => fetchMethod())
      .then(() => showSnackbar(`配置已保存，智能问数将使用「${name}」`, 'success'))
      .catch(() => showSnackbar('保存失败，请重试', 'error'))
  }, [selected, models, fetchMethod, showSnackbar])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Breadcrumb />
      <div className="pg-card">
        <div className="model-config">
          <div className="mc-title"><i className="fas fa-cube" />应用模型设置</div>
          <div className="mc-subtitle">选择AI问答使用的LLM模型</div>

          <div className="mc-card">
            <div className="mc-card-hdr">
              <span className="mc-card-title"><i className="fas fa-robot" />智能问数模型</span>
              <select value={selected} onChange={(e) => changeSelect(e.target.value)}>
                <option value="">-- 选择模型 --</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
                <option value="__add__" style={{ color: 'var(--primary)', fontWeight: 600 }}>── 新增模型 ──</option>
              </select>
            </div>
            <div className="mc-card-body">用于智能问数、经营指标问答、台账数据分析</div>
          </div>

          <div className="mc-actions">
            <button className="btn btn-light btn-sm whitespace-nowrap gap-1" onClick={saveConfig}>
              <i className="fas fa-save" /> 保存配置
            </button>
          </div>
        </div>
      </div>

      <AddModelModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  )
}
