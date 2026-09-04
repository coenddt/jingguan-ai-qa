/** ③ 数据表格（含截断提示） */

interface Props {
  columns: string[]
  rows: (string | number)[][]
  totalCount: number
}

export default function AiDataTable({ columns, rows, totalCount }: Props) {
  if (!rows.length) return null
  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="table table-sm" style={{ minWidth: 750 }}>
          <thead>
            <tr>{columns.map((c) => <th key={c} className="whitespace-nowrap">{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j} className="whitespace-nowrap">{String(cell)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length >= 200 && (
        <div className="text-xs text-warning">共 {totalCount} 条已截断（上限 200 条）</div>
      )}
    </>
  )
}
