import { useEffect, useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { importApi } from '../../api/modules/importApi'
import EmptyTableRow from '../../components/EmptyTableRow'
import TableSkeleton from '../../components/TableSkeleton'
import CustomTablePagination from '../../components/CustomTablePagination'
import { useSnackbar } from '../../hooks/useSnackbar'
import { formatDateTime } from '../../utils/date'

interface Props {
  open: boolean
  onClose: () => void
}

const TYPE_LABEL: Record<string, string> = { commercial: '商业台账', ppl: '项目储备', goal: '经营目标' }

export default function ImportDialog({ open, onClose }: Props) {
  const [type, setType] = useState('commercial')
  const [year, setYear] = useState(2026)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [logs, setLogs] = useState<{ id: string; type: string; year: number; fileName: string; status: string; detail: string; createdAt: string }[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(5)
  const [loading, setLoading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const { showSnackbar } = useSnackbar()

  const loadLogs = async (p = page, size = rowsPerPage, t = '') => {
    setLoading(true)
    try {
      const { data } = await importApi.listLog({ page: p + 1, pageSize: size, type: t || undefined })
      setLogs(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    loadLogs(page, rowsPerPage)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  if (!open) return null

  const submit = async () => {
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await importApi.upload(form, { type, year })
      if (data.ok) {
        showSnackbar(`导入${data.status}：成功 ${data.success}/${data.total} 条`, 'success')
        onClose()
      } else {
        showSnackbar(`导入失败：${data.errors?.[0] || data.status}`, 'error')
      }
    } catch {
      showSnackbar('导入失败（文件解析或校验未通过）', 'error')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
      setFile(null)
    }
  }

  return (
    <dialog className="modal modal-open" onClick={onClose}>
      <div className="modal-box max-w-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-4">台账导入</h3>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div>
            <label className="text-xs font-bold text-gray-500 mb-1 block">台账类型</label>
            <select className="select select-bordered w-full" value={type}
              onChange={(e) => setType(e.target.value)}>
              <option value="commercial">商业签约台账</option>
              <option value="ppl">项目储备台账</option>
              <option value="goal">经营目标台账</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 mb-1 block">年份</label>
            <select className="select select-bordered w-full" value={year}
              onChange={(e) => setYear(Number(e.target.value))}>
              <option value={2025}>2025</option>
              <option value={2026}>2026</option>
            </select>
          </div>
          <div className="flex items-end">
            <label className="btn btn-primary cursor-pointer whitespace-nowrap gap-1 w-full">
              <Upload size={16} /> 选择文件
              <input type="file" accept=".xlsx" className="hidden" ref={fileRef}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
          </div>
        </div>
        {file && <div className="text-xs text-gray-500 mb-2">已选择：{file.name}</div>}
        <button className="btn btn-gold w-full whitespace-nowrap mb-5" disabled={!file || uploading} onClick={submit}>
          {uploading ? <span className="loading loading-spinner loading-xs" /> : '确认导入'}
        </button>

        <h4 className="font-bold text-gray-700 text-sm mb-2">导入记录</h4>
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="table table-sm">
            <thead>
              <tr>
                <th className="w-[90px]">类型</th>
                <th className="w-[70px]">年份</th>
                <th className="min-w-[140px] max-w-[220px]">文件</th>
                <th className="w-[100px]">状态</th>
                <th className="w-[140px]">时间</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <TableSkeleton columns={5} rows={3} /> :
                logs.length ? logs.map((l) => (
                  <tr key={l.id}>
                    <td>{TYPE_LABEL[l.type] || l.type}</td>
                    <td>{l.year}</td>
                    <td className="whitespace-normal break-words">{l.fileName}</td>
                    <td><span className={`badge badge-sm whitespace-nowrap ${l.status === '成功' ? 'badge-success' : l.status === '部分成功' ? 'badge-warning' : 'badge-error'}`}>{l.status}</span></td>
                    <td className="text-xs text-gray-400">{formatDateTime(l.createdAt)}</td>
                  </tr>
                )) : <EmptyTableRow colSpan={5} message="暂无导入记录" />}
            </tbody>
          </table>
        </div>
        <CustomTablePagination total={total} page={page} rowsPerPage={rowsPerPage}
          onPageChange={setPage} onRowsPerPageChange={(n: number) => { setRowsPerPage(n); setPage(0) }} />
      </div>
    </dialog>
  )
}
