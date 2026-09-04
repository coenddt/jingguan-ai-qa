/** 图表域纯业务函数：由 Chart 契约构建 ECharts option */

import type { EChartsOption } from 'echarts'
import type { Chart } from '../types'

const COLORS = ['#1a3a6c', '#2c5282', '#d4af37', '#b48a32', '#5b7db1', '#94a3b8', '#0ea5e9', '#16a34a', '#d97706', '#dc2626']

const base = {
  tooltip: { trigger: 'axis' as const },
  grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
  color: COLORS,
}

export function buildChartOption(chart: Chart): EChartsOption {
  const { x, series } = chart
  if (chart.type === 'pie') {
    return {
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
  }
  if (chart.type === 'bar_h') {
    return {
      ...base,
      xAxis: { type: 'value' as const },
      yAxis: { type: 'category' as const, data: x },
      series: [{ type: 'bar', data: series, barMaxWidth: 26, itemStyle: { color: '#2c5282' } }],
    }
  }
  if (chart.type === 'line') {
    return {
      ...base,
      xAxis: { type: 'category' as const, data: x, boundaryGap: false },
      yAxis: { type: 'value' as const },
      series: [{ type: 'line', data: series, smooth: true, symbolSize: 7, lineStyle: { width: 3, color: '#1a3a6c' } }],
    }
  }
  return {
    ...base,
    xAxis: { type: 'category' as const, data: x, axisLabel: { rotate: x.length > 8 ? 30 : 0 } },
    yAxis: { type: 'value' as const },
    series: [{ type: 'bar', data: series, barMaxWidth: 42, itemStyle: { color: '#1a3a6c' } }],
  }
}
