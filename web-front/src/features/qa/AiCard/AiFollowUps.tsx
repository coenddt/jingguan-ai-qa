/** ⑦ 追问建议 chips（原型 fu-chip：文字 + → 箭头，点击经 AskContext 触发问数） */

import { useAsk } from '../qaContext'

export default function AiFollowUps({ followUps }: { followUps: string[] }) {
  const ask = useAsk()
  if (!followUps.length) return null
  return (
    <div className="qa-followup">
      {followUps.map((f) => (
        <button key={f} className="fu-chip" onClick={() => ask(f)}>
          {f}<span className="arr">→</span>
        </button>
      ))}
    </div>
  )
}
