import { Check } from 'lucide-react'

interface StepDef {
  label: string
  desc?: string
}

export default function StepperIndicator({ steps = [], current = 0 }: { steps: StepDef[]; current?: number }) {
  if (!steps.length) return null
  return (
    <ul className="steps w-full">
      {steps.map((s, idx) => {
        const done = idx < current
        const active = idx === current
        return (
          <li key={idx} className={`step ${done ? 'step-success' : ''} ${active ? 'step-primary' : ''}`}>
            <div className="flex flex-col items-center">
              <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold ${
                done ? 'bg-success text-white' : active ? 'bg-primary text-white' : 'border-2 border-gray-300 text-gray-400'}`}>
                {done ? <Check size={16} strokeWidth={3} /> : idx + 1}
              </span>
              <span className="mt-1 text-sm">{s.label}</span>
              {!!s.desc && <span className="text-xs text-gray-400">{s.desc}</span>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
