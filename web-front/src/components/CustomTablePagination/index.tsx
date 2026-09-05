import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Props {
  total: number
  page: number
  rowsPerPage: number
  onPageChange: (page: number) => void
  onRowsPerPageChange: (n: number) => void
}

export default function CustomTablePagination({ total, page, rowsPerPage, onPageChange, onRowsPerPageChange }: Props) {
  const totalPages = Math.ceil(total / rowsPerPage) || 1
  return (
    <div className="border-t border-gray-200 bg-black/[0.01] px-4 py-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-500">
          <span>每页显示</span>
          <select className="select select-bordered select-sm w-20 font-bold"
            value={rowsPerPage}
            onChange={(e) => onRowsPerPageChange(Number(e.target.value))}>
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
          </select>
        </div>
        <div className="text-sm font-semibold text-gray-500">
          {total === 0 ? '0 条' : `${page * rowsPerPage + 1}-${Math.min((page + 1) * rowsPerPage, total)} / 共 ${total} 条`}
        </div>
        <div className="join">
          <button className="join-item btn btn-sm btn-light whitespace-nowrap" aria-label="上一页" disabled={page === 0}
            onClick={() => onPageChange(page - 1)}>
            <ChevronLeft size={16} />
          </button>
          {[...Array(totalPages)].map((_, i) => (
            <button key={i}
              className={`join-item btn btn-sm whitespace-nowrap ${i === page ? 'btn-active btn-primary' : 'btn-light'}`}
              onClick={() => onPageChange(i)}>
              {i + 1}
            </button>
          ))}
          <button className="join-item btn btn-sm btn-light whitespace-nowrap" aria-label="下一页" disabled={page >= totalPages - 1}
            onClick={() => onPageChange(page + 1)}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
