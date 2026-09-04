/** 应用模型列表卡片（ModelConfig 页使用） */

import { Trash2 } from 'lucide-react'
import type { ModelItem } from '../../../types'

interface Props {
  models: ModelItem[]
  onEnable: (m: ModelItem) => void
  onDelete: (m: ModelItem) => void
}

export default function ModelList({ models, onEnable, onDelete }: Props) {
  return (
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
              <button className="btn btn-outline btn-xs whitespace-nowrap" onClick={() => onEnable(m)}>启用</button>
            )}
            <button className="btn btn-ghost btn-xs btn-square text-error" onClick={() => onDelete(m)}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
