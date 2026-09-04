/** 反馈列表表格块（Feedback 页使用） */

import type { FeedbackItem } from '../../types'
import CustomTablePagination from '../../components/CustomTablePagination'
import EmptyTableRow from '../../components/EmptyTableRow'
import TableSkeleton from '../../components/TableSkeleton'
import { formatDateTime } from '../../utils/date'

interface Props {
  items: FeedbackItem[]
  loading: boolean
  total: number
  page: number
  rowsPerPage: number
  onPageChange: (page: number) => void
  onRowsPerPageChange: (n: number) => void
  onView: (f: FeedbackItem) => void
}

export default function FeedbackTable({ items, loading, total, page, rowsPerPage, onPageChange, onRowsPerPageChange, onView }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 mt-4 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="table" style={{ minWidth: 850 }}>
          <thead>
            <tr>
              <th className="w-[160px]">时间</th>
              <th className="w-[110px]">用户</th>
              <th className="min-w-[140px] max-w-[280px]">问题</th>
              <th className="w-[90px]">状态</th>
              <th className="w-[100px]">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? <TableSkeleton columns={5} /> :
              items.length ? items.map((f) => (
                <tr key={f.id}>
                  <td className="text-xs text-gray-400 whitespace-nowrap">{formatDateTime(f.createdAt)}</td>
                  <td className="whitespace-nowrap">{f.userName}</td>
                  <td className="min-w-[140px] max-w-[280px] whitespace-normal break-words">{f.question}</td>
                  <td>
                    <span className={`badge badge-sm whitespace-nowrap ${f.status === '已处理' ? 'badge-success' : 'badge-warning'}`}>
                      {f.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn btn-outline btn-xs whitespace-nowrap" onClick={() => onView(f)}>查看</button>
                  </td>
                </tr>
              )) : <EmptyTableRow colSpan={5} message="暂无反馈记录" />}
          </tbody>
        </table>
      </div>
      <CustomTablePagination total={total} page={page} rowsPerPage={rowsPerPage}
        onPageChange={onPageChange} onRowsPerPageChange={onRowsPerPageChange} />
    </div>
  )
}
