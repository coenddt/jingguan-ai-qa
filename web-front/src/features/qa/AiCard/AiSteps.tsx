/** ① 分析过程（原型 aa-summary-bar + aa-inline-steps） */

import type { Step } from '../../../types'
import { formatClock } from '../../../utils/date'

interface Props {
  open: boolean
  onToggle: () => void
  steps: Step[]
  /** 显示每步时间戳与耗时（日志详情用，聊天页不展示） */
  showTime?: boolean
}

export default function AiSteps({ open, onToggle, steps, showTime }: Props) {
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
              {showTime && !!s.ts && (
                <div className="aa-step-time"><i className="far fa-clock" /> {formatClock(s.ts)} · {s.elapsed ?? 0}ms</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
