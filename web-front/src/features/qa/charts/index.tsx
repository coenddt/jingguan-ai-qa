/** AI 卡片图表块（option 构建逻辑在 services/chart） */

import ReactECharts from 'echarts-for-react'
import type { Chart } from '../../../types'
import { buildChartOption } from '../../../services/chart'

export default function ChartView({ chart }: { chart: Chart }) {
  const option = buildChartOption(chart)

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-1">
        <h4 className="font-bold text-gray-700">{chart.title}</h4>
        {!!chart.unit && <span className="text-xs text-gray-400">单位：{chart.unit}</span>}
      </div>
      <ReactECharts option={option} style={{ height: 320 }} notMerge />
    </div>
  )
}
