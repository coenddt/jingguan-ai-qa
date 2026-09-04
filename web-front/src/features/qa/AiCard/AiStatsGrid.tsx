/** ④ 数据统计（记录数/均值/最大/最小 四格） */

import type { QaStats } from '../../../types'

export default function AiStatsGrid({ stat }: { stat: QaStats }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="text-xs text-gray-400">记录数</div>
        <div className="text-lg font-extrabold text-primary">{stat.count}</div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="text-xs text-gray-400">均值</div>
        <div className="text-lg font-extrabold text-primary">{stat.avg}</div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="text-xs text-gray-400">最大值</div>
        <div className="text-lg font-extrabold text-gold-deep">{stat.max}<span className="text-xs font-medium text-gray-400 ml-1">{stat.max_of}</span></div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="text-xs text-gray-400">最小值</div>
        <div className="text-lg font-extrabold text-primary">{stat.min}<span className="text-xs font-medium text-gray-400 ml-1">{stat.min_of}</span></div>
      </div>
    </div>
  )
}
