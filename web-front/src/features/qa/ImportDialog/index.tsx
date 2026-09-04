/** 台账导入弹窗：上传表单 + 导入记录 */

import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react'
import { Upload } from 'lucide-react'
import type { ImportLogItem } from '../../../types'
import Modal from '../../../components/Modal'
import { useSnackbar } from '../../../hooks/useSnackbar'
import { usePagedList } from '../../../hooks/usePagedList'
import { fetchImportLogPage, uploadLedger } from '../../../services/importLog'
import ImportLogTable from './ImportLogTable'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ImportDialog({ open, onClose }: Props) {
  const [type, setType] = useState('commercial')
  const [year, setYear] = useState(2026)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const { showSnackbar } = useSnackbar()
  const {
    items: logs, total, page, rowsPerPage, loading, changePage, changeRowsPerPage, refresh,
  } = usePagedList<ImportLogItem>(
    fetchImportLogPage,
    { pageSize: 5, onError: showSnackbar, errorMessage: '导入记录加载失败' },
  )

  useEffect(() => {
    if (open) refresh()
  }, [open, refresh])

  const changeType = useCallback((e: ChangeEvent<HTMLSelectElement>) => setType(e.target.value), [])
  const changeYear = useCallback((e: ChangeEvent<HTMLSelectElement>) => setYear(Number(e.target.value)), [])
  const changeFile = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
  }, [])

  const submit = useCallback(() => {
    if (!file) return
    setUploading(true)
    uploadLedger(file, type, year)
      .then((data) => {
        if (data.ok) {
          showSnackbar(`导入${data.status}：成功 ${data.success}/${data.total} 条`, 'success')
          onClose()
          refresh()
        } else {
          showSnackbar(`导入失败：${data.errors?.[0] || data.status}`, 'error')
        }
      })
      .catch(() => showSnackbar('导入失败（文件解析或校验未通过）', 'error'))
      .finally(() => {
        setUploading(false)
        if (fileRef.current) fileRef.current.value = ''
        setFile(null)
      })
  }, [file, type, year, showSnackbar, onClose, refresh])

  if (!open) return null

  return (
    <Modal open={open} onClose={onClose} boxClassName="max-w-2xl"
      title={<h3 className="font-bold text-lg">台账导入</h3>} headerClassName="mb-4">
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <label className="text-xs font-bold text-gray-500 mb-1 block">台账类型</label>
          <select className="select select-bordered w-full" value={type} onChange={changeType}>
            <option value="commercial">商业签约台账</option>
            <option value="ppl">项目储备台账</option>
            <option value="goal">经营目标台账</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-bold text-gray-500 mb-1 block">年份</label>
          <select className="select select-bordered w-full" value={year} onChange={changeYear}>
            <option value={2025}>2025</option>
            <option value={2026}>2026</option>
          </select>
        </div>
        <div className="flex items-end">
          <label className="btn btn-primary cursor-pointer whitespace-nowrap gap-1 w-full">
            <Upload size={16} /> 选择文件
            <input type="file" accept=".xlsx" className="hidden" ref={fileRef} onChange={changeFile} />
          </label>
        </div>
      </div>
      {file && <div className="text-xs text-gray-500 mb-2">已选择：{file.name}</div>}
      <button className="btn btn-gold w-full whitespace-nowrap mb-5" disabled={!file || uploading} onClick={submit}>
        {uploading ? <span className="loading loading-spinner loading-xs" /> : '确认导入'}
      </button>

      <h4 className="font-bold text-gray-700 text-sm mb-2">导入记录</h4>
      <ImportLogTable logs={logs} loading={loading} total={total} page={page} rowsPerPage={rowsPerPage}
        onPageChange={changePage} onRowsPerPageChange={changeRowsPerPage} />
    </Modal>
  )
}
