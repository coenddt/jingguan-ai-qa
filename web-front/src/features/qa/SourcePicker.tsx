import { useEffect, useState } from 'react'
import { Download, FileUp, History, X } from 'lucide-react'
import { qaApi } from '../../api/modules/qa'
import { importApi } from '../../api/modules/importApi'
import type { DataSourceGroup } from '../../types'
import ImportDialog from './ImportDialog'
import { useSnackbar } from '../../hooks/useSnackbar'

interface Props {
  open: boolean
  selected: string[]
  onChange: (keys: string[]) => void
  onClose: () => void
}

export default function SourcePicker({ open, selected, onChange, onClose }: Props) {
  const [groups, setGroups] = useState<DataSourceGroup[]>([])
  const [importOpen, setImportOpen] = useState(false)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    if (!open) return
    qaApi.getSources().then(({ data }) => setGroups(data)).catch(() => showSnackbar('数据源加载失败', 'error'))
  }, [open, showSnackbar])

  if (!open) return null
  const allKeys = groups.flatMap((g) => g.items.map((i) => i.key))
  const toggle = (key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key])
  }
  const allSelected = allKeys.length > 0 && allKeys.every((k) => selected.includes(k))

  const downloadTemplate = async () => {
    const { data } = await importApi.downloadTemplate('commercial')
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'commercial_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <dialog className="modal modal-open" onClick={onClose}>
      <div className="modal-box max-w-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-lg">数据源选择</h3>
          <button className="btn btn-ghost btn-xs btn-square" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="text-xs text-gray-400 mb-3">
          {allSelected ? '已选择所有数据源' : `已选 ${selected.length} 个数据源`}
        </div>
        <div className="space-y-4">
          {groups.map((g) => (
            <div key={g.group}>
              <div className="text-sm font-bold text-gray-700 mb-2">{g.group}</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {g.items.map((item) => (
                  <label key={item.key} className="flex items-start gap-2.5 bg-gray-50 rounded-xl p-3 cursor-pointer hover:bg-gray-100">
                    <input type="checkbox" className="checkbox checkbox-primary checkbox-sm mt-0.5"
                      checked={selected.includes(item.key)} onChange={() => toggle(item.key)} />
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-gray-700">{item.name}</div>
                      {item.label && <div className="text-xs text-gray-400 truncate">{item.label}</div>}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="modal-action justify-between">
          <div className="flex gap-2">
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={() => setImportOpen(true)}>
              <FileUp size={15} /> 导入
            </button>
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={downloadTemplate}>
              <Download size={15} /> 下载模板
            </button>
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={() => setImportOpen(true)}>
              <History size={15} /> 导入记录
            </button>
          </div>
          <button className="btn btn-primary whitespace-nowrap" onClick={onClose}>完成</button>
        </div>
      </div>
      <ImportDialog open={importOpen} onClose={() => setImportOpen(false)} />
    </dialog>
  )
}
