/** 导入记录表格块（ImportDialog 使用） */

import type { ImportLogItem } from '../../../types'
import EmptyTableRow from '../../../components/EmptyTableRow'
import TableSkeleton from '../../../components/TableSkeleton'
import CustomTablePagination from '../../../components/CustomTablePagination'
import { formatDateTime } from '../../../utils/date'

const TYPE_LABEL: Record<string, string> = { commercial: '商业台账', ppl: '项目储备', goal: '经营目标' }

interface Props {
  logs: ImportLogItem[]
  loading: boolean
  total: number
  page: number
  rowsPerPage: number
  onPageChange: (page: number) => void
  onRowsPerPageChange: (n: number) => void
}

export default function ImportLogTable({ logs, loading, total, page, rowsPerPage, onPageChange, onRowsPerPageChange }: Props) {
  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="table table-sm" style={{ minWidth: 850 }}>
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
        onPageChange={onPageChange} onRowsPerPageChange={onRowsPerPageChange} />
    </>
  )
}
