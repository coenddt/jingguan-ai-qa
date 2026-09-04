/** 反馈列表表格块（原型 tableFeedback 1:1：序号/用户/问题/反馈时间/状态/操作，操作列 sticky 右侧「处理」） */

import type { FeedbackItem } from '../../types'
import CustomTablePagination from '../../components/CustomTablePagination'
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
  onHandle: (f: FeedbackItem) => void
}

export default function FeedbackTable({ items, loading, total, page, rowsPerPage, onPageChange, onRowsPerPageChange, onHandle }: Props) {
  return (
    <>
      <div className="pg-table-wrap">
        <table className="pg-data-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>序号</th>
              <th style={{ width: 100 }}>用户</th>
              <th style={{ width: '30%' }}>问题</th>
              <th style={{ width: 160 }}>反馈时间</th>
              <th style={{ width: 80 }}>状态</th>
              <th style={{ width: 100, position: 'sticky', right: 0, background: '#F8FAFC', boxShadow: '-2px 0 4px rgba(0,0,0,.04)' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? <TableSkeleton columns={6} /> :
              items.length ? items.map((f, i) => (
                <tr key={f.id}>
                  <td style={{ textAlign: 'center' }}>{page * rowsPerPage + i + 1}</td>
                  <td className="whitespace-nowrap">{f.userName}</td>
                  <td className="whitespace-normal break-words">{f.question}</td>
                  <td className="whitespace-nowrap">{formatDateTime(f.createdAt)}</td>
                  <td>
                    <span className={`tag whitespace-nowrap ${f.status === '已处理' ? 'tag-green' : 'tag-orange'}`}>{f.status}</span>
                  </td>
                  <td style={{ position: 'sticky', right: 0, background: '#fff' }}>
                    <button className="btn btn-text btn-xs whitespace-nowrap" onClick={() => onHandle(f)}>处理</button>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#9CA3AF', fontSize: 14, padding: 40 }}>暂无反馈数据</td></tr>
              )}
          </tbody>
        </table>
      </div>
      <CustomTablePagination total={total} page={page} rowsPerPage={rowsPerPage}
        onPageChange={onPageChange} onRowsPerPageChange={onRowsPerPageChange} />
    </>
  )
}

