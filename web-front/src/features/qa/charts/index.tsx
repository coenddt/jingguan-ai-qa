/** AI 卡片图表块（option 构建逻辑在 services/chart；标题由外层 chart-desc 呈现） */

import ReactECharts from 'echarts-for-react'
import type { Chart } from '../../../types'
import { buildChartOption } from '../../../services/chart'

export default function ChartView({ chart }: { chart: Chart }) {
  const option = buildChartOption(chart)

  return (
    <div className="qa-chart-wrap" style={{ padding: 12, background: '#FAFBFC', borderRadius: 8 }}>
      <ReactECharts option={option} style={{ height: 320 }} notMerge />
    </div>
  )
}
