import { useCallback, useState } from 'react'
import { Filter, RotateCcw, Search } from 'lucide-react'

export interface SearchField {
  name: string
  label?: string
  type: 'text' | 'select' | 'date'
  placeholder?: string
  options?: { value: string; label: string }[]
}

interface Props {
  fields: SearchField[]
  onSearch: (values: Record<string, string>) => void
  onReset: () => void
  initialValues?: Record<string, string>
}

export default function SearchFilter({ fields, onSearch, onReset, initialValues = {} }: Props) {
  const [values, setValues] = useState<Record<string, string>>(initialValues)

  const change = useCallback((name: string, value: string) => {
    setValues((p) => ({ ...p, [name]: value }))
  }, [])

  const handleSearch = useCallback(() => onSearch(values), [onSearch, values])

  const handleReset = useCallback(() => {
    setValues(initialValues)
    onReset()
  }, [initialValues, onReset])

  return (
    <div className="p-1">
      <div className="grid grid-cols-12 gap-3 items-end">
        {fields.map((f) => (
          <div key={f.name} className="col-span-12 sm:col-span-6 lg:col-span-3">
            {f.type === 'text' && (
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input className="input input-bordered w-full pl-9 h-10 rounded-2xl bg-gray-50 border-gray-200 text-sm"
                  placeholder={f.placeholder}
                  value={values[f.name] || ''}
                  onChange={(e) => change(f.name, e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  autoComplete="off" />
              </div>
            )}
            {f.type === 'select' && (
              <div className="relative">
                <Filter size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 z-10" />
                <select className="select select-bordered w-full pl-8 h-10 rounded-2xl bg-gray-50 border-gray-200 text-sm font-medium"
                  value={values[f.name] || ''}
                  onChange={(e) => change(f.name, e.target.value)}>
                  {(f.options || []).map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
            {f.type === 'date' && (
              <input type="date" className="input input-bordered w-full h-10 rounded-2xl bg-gray-50 border-gray-200 text-sm"
                value={values[f.name] || ''}
                onChange={(e) => change(f.name, e.target.value)} />
            )}
          </div>
        ))}
        <div className="col-span-12 lg:col-auto flex gap-1.5 whitespace-nowrap">
          <button className="btn btn-primary whitespace-nowrap px-5 h-10 min-h-0 rounded-2xl font-bold" onClick={handleSearch}>
            <Search size={18} /> 检索
          </button>
          <button className="btn btn-ghost whitespace-nowrap px-4 h-10 min-h-0 rounded-2xl font-bold border border-gray-200 text-gray-500"
            onClick={handleReset}>
            <RotateCcw size={18} /> 重置
          </button>
        </div>
      </div>
    </div>
  )
}
