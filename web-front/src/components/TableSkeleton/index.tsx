export default function TableSkeleton({ columns = 5, rows = 5 }: { columns?: number; rows?: number }) {
  return (
    <>
      {[...Array(rows)].map((_, i) => (
        <tr key={i}>
          {[...Array(columns)].map((_, j) => (
            <td key={j}>
              <div className={`skeleton h-6 ${j === columns - 1 ? 'w-[40%]' : 'w-[80%]'}`} />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}
