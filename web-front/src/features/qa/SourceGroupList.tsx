/** 数据源分组勾选列表（SourcePicker 使用） */

import type { DataSourceGroup } from '../../types'

interface Props {
  groups: DataSourceGroup[]
  selected: string[]
  onToggle: (key: string) => void
}

export default function SourceGroupList({ groups, selected, onToggle }: Props) {
  return (
    <div className="space-y-4">
      {groups.map((g) => (
        <div key={g.group}>
          <div className="text-sm font-bold text-gray-700 mb-2">{g.group}</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {g.items.map((item) => (
              <label key={item.key} className="flex items-start gap-2.5 bg-gray-50 rounded-xl p-3 cursor-pointer hover:bg-gray-100">
                <input type="checkbox" className="checkbox checkbox-primary checkbox-sm mt-0.5"
                  checked={selected.includes(item.key)} onChange={() => onToggle(item.key)} />
                <div className="min-w-0">
                  <div className="text-sm font-bold text-gray-700">{item.name}</div>
                  {item.label && <div className="text-xs text-gray-400 truncate">{item.label}</div>}
                </div>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
