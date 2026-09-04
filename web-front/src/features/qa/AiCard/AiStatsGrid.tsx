/** ④ 数据统计（原型 dot-li 行式：总记录数/平均值/最大值/最小值） */

import type { QaStats } from '../../../types'

export default function AiStatsGrid({ stat }: { stat: QaStats }) {
  return (
    <div className="mod-body" style={{ fontSize: 15 }}>
      <div className="dot-li">总记录数：{stat.count} 条</div>
      <div className="dot-li">平均值：{stat.avg}</div>
      <div className="dot-li">最大值：{stat.max}（{stat.max_of}）</div>
      <div className="dot-li">最小值：{stat.min}（{stat.min_of}）</div>
    </div>
  )
}
