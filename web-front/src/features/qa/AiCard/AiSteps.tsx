/** ① 分析过程（可折叠步骤列表） */

import { Check } from 'lucide-react'
import type { ChangeEvent } from 'react'
import type { Step } from '../../../types'

interface Props {
  open: boolean
  onChange: (e: ChangeEvent<HTMLInputElement>) => void
  steps: Step[]
}

export default function AiSteps({ open, onChange, steps }: Props) {
  return (
    <div className="collapse collapse-arrow bg-base-100 border border-gray-200 rounded-xl">
      <input type="checkbox" checked={open} onChange={onChange} />
      <div className="collapse-title text-sm font-bold text-gray-600 pr-2">分析过程</div>
      <div className="collapse-content">
        <ul className="space-y-2">
          {steps.map((s, i) => (
            <li key={i} className="flex gap-2 text-sm">
              {s.done && <Check size={16} className="text-success shrink-0 mt-0.5" />}
              <div>
                <span className="font-bold text-gray-700">{s.title}</span>
                {s.desc && <div className="text-gray-500 break-all">{s.desc}</div>}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
