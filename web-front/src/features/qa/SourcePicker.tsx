/** 数据源选择弹窗：分组勾选 + 导入/模板入口 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Download, FileUp, History } from 'lucide-react'
import { qaApi } from '../../api/modules/qa'
import { importApi } from '../../api/modules/importApi'
import type { DataSourceGroup } from '../../types'
import ImportDialog from './ImportDialog'
import { useSnackbar } from '../../hooks/useSnackbar'
import Modal from '../../components/Modal'
import { downloadBlob } from '../../services/download'
import SourceGroupList from './SourceGroupList'

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

  const allKeys = useMemo(() => groups.flatMap((g) => g.items.map((i) => i.key)), [groups])
  const allSelected = allKeys.length > 0 && allKeys.every((k) => selected.includes(k))

  const toggle = useCallback((key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key])
  }, [onChange, selected])

  const downloadTemplate = useCallback(() => {
    importApi.downloadTemplate('commercial')
      .then(({ data }) => downloadBlob(data, 'commercial_template.xlsx'))
      .catch(() => showSnackbar('模板下载失败，请稍后重试', 'error'))
  }, [showSnackbar])

  const openImport = useCallback(() => setImportOpen(true), [])
  const closeImport = useCallback(() => setImportOpen(false), [])

  if (!open) return null

  return (
    <>
      <Modal open={open} onClose={onClose} boxClassName="max-w-2xl" showClose
        title={<h3 className="font-bold text-lg">数据源选择</h3>} headerClassName="mb-4"
        footerClassName="justify-between"
        footer={<>
          <div className="flex gap-2">
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={openImport}>
              <FileUp size={15} /> 导入
            </button>
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={downloadTemplate}>
              <Download size={15} /> 下载模板
            </button>
            <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={openImport}>
              <History size={15} /> 导入记录
            </button>
          </div>
          <button className="btn btn-primary whitespace-nowrap" onClick={onClose}>完成</button>
        </>}>
        <div className="text-xs text-gray-400 mb-3">
          {allSelected ? '已选择所有数据源' : `已选 ${selected.length} 个数据源`}
        </div>
        <SourceGroupList groups={groups} selected={selected} onToggle={toggle} />
      </Modal>
      <ImportDialog open={importOpen} onClose={closeImport} />
    </>
  )
}
