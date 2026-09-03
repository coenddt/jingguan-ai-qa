import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { Chart } from '../../../types'

const COLORS = ['#1a3a6c', '#2c5282', '#d4af37', '#b48a32', '#5b7db1', '#94a3b8', '#0ea5e9', '#16a34a', '#d97706', '#dc2626']

const base = {
  tooltip: { trigger: 'axis' as const },
  grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
  color: COLORS,
}

export default function ChartView({ chart }: { chart: Chart }) {
  const { x, series, title, unit } = chart
  let option: EChartsOption
  if (chart.type === 'pie') {
    option = {
      ...base,
      tooltip: { trigger: 'item' as const },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie',
        radius: ['38%', '65%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}: {d}%' },
        data: x.map((name, i) => ({ name, value: series[i] })),
      }],
    }
  } else if (chart.type === 'bar_h') {
    option = {
      ...base,
      xAxis: { type: 'value' as const },
      yAxis: { type: 'category' as const, data: x },
      series: [{ type: 'bar', data: series, barMaxWidth: 26, itemStyle: { color: '#2c5282' } }],
    }
  } else if (chart.type === 'line') {
    option = {
      ...base,
      xAxis: { type: 'category' as const, data: x, boundaryGap: false },
      yAxis: { type: 'value' as const },
      series: [{ type: 'line', data: series, smooth: true, symbolSize: 7, lineStyle: { width: 3, color: '#1a3a6c' } }],
    }
  } else {
    option = {
      ...base,
      xAxis: { type: 'category' as const, data: x, axisLabel: { rotate: x.length > 8 ? 30 : 0 } },
      yAxis: { type: 'value' as const },
      series: [{ type: 'bar', data: series, barMaxWidth: 42, itemStyle: { color: '#1a3a6c' } }],
    }
  }
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-1">
        <h4 className="font-bold text-gray-700">{title}</h4>
        {!!unit && <span className="text-xs text-gray-400">单位：{unit}</span>}
      </div>
      <ReactECharts option={option} style={{ height: 320 }} notMerge />
    </div>
  )
}
