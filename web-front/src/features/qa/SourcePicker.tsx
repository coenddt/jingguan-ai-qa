/** 数据源选择弹窗（原型 qaFilePickerModal 1:1）：全选/取消全选 + 分组勾选 + 确定 */

import { useCallback, useEffect, useMemo, useState } from 'react'
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
      <Modal open={open} onClose={onClose} boxClassName="max-w-[420px]" showClose
        title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-paperclip mr-2" />选择数据源</h3>}
        headerClassName="mb-2"
        footer={<>
          <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={openImport}>
            <i className="fas fa-upload" /> 导入
          </button>
          <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={downloadTemplate}>
            <i className="fas fa-download" /> 下载模板
          </button>
          <button className="btn btn-ghost btn-sm whitespace-nowrap gap-1" onClick={openImport}>
            <i className="fas fa-history" /> 导入记录
          </button>
          <button className="btn btn-primary whitespace-nowrap" onClick={onClose}>确定</button>
        </>}
        footerClassName="justify-between">
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <button className="btn btn-text btn-xs whitespace-nowrap" style={{ fontSize: 14 }}
            onClick={() => onChange(allKeys)}>全选</button>
          <button className="btn btn-text btn-xs whitespace-nowrap" style={{ fontSize: 14 }}
            onClick={() => onChange([])}>取消全选</button>
        </div>
        <div style={{ maxHeight: 320, overflowY: 'auto' }}>
          <SourceGroupList groups={groups} selected={selected} onToggle={toggle} />
        </div>
      </Modal>
      <ImportDialog open={importOpen} onClose={closeImport} />
    </>
  )
}
