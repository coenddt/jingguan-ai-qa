/** ③ 数据表格（原型 qa-ai-table） */

interface Props {
  columns: string[]
  rows: (string | number)[][]
  totalCount: number
}

export default function AiDataTable({ columns, rows, totalCount }: Props) {
  if (!rows.length) return null
  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table className="qa-ai-table">
          <thead>
            <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j}>{String(cell)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length >= 200 && (
        <div style={{ fontSize: 12, color: '#D97706', marginTop: 4 }}>共 {totalCount} 条已截断（上限 200 条）</div>
      )}
    </>
  )
}
