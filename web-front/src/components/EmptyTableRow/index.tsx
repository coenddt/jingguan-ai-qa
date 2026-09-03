import { FileSearch, Inbox } from 'lucide-react'

export default function EmptyTableRow({ colSpan, message = '暂无数据' }: { colSpan: number; message?: string }) {
  return (
    <tr>
      <td colSpan={colSpan} align="center" className="py-14 border-none">
        <div className="flex flex-col items-center gap-3">
          <div className="p-3 rounded-2xl bg-black/[0.015] text-gray-300 flex border border-dashed border-gray-200 relative">
            <FileSearch size={56} strokeWidth={1} />
            <div className="absolute -bottom-2 -right-2 p-1 bg-white rounded-full shadow-sm flex">
              <Inbox size={18} color="#b48a32" />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-400">{message}</p>
        </div>
      </td>
    </tr>
  )
}
