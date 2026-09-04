/** ① 分析过程（原型 aa-summary-bar + aa-inline-steps） */

import type { Step } from '../../../types'

interface Props {
  open: boolean
  onToggle: () => void
  steps: Step[]
}

export default function AiSteps({ open, onToggle, steps }: Props) {
  return (
    <div className="aa-wrap">
      <div className="aa-summary-bar" onClick={onToggle}>
        <i className="fas fa-microchip" /> 分析过程 <span className="arr">{open ? '▾' : '▸'}</span>
        <span style={{ marginLeft: 'auto', color: '#6B7280', fontSize: 13 }}>{open ? '点击收起' : '点击展开'}</span>
      </div>
      <div className={`aa-inline-steps ${open ? 'show' : ''}`}>
        {steps.map((s, i) => (
          <div key={i} className={`aa-step ${s.done ? 'done' : s.running ? 'running' : 'active'}`}>
            <div className="aa-step-icon">
              {s.done ? <i className="fas fa-check" /> : s.running ? <i className="fas fa-circle-notch fa-spin" /> : null}
            </div>
            <div className="aa-step-body">
              <div className="aa-step-title">{s.title}</div>
              {!!s.desc && (
                <div className={`aa-step-desc ${s.title.includes('SQL') || s.desc.includes('SELECT') ? 'code' : ''}`}>{s.desc}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
