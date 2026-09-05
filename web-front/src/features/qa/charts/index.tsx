/** AI 卡片图表块（option 构建逻辑在 services/chart）。原生 echarts 渲染（弃用 echarts-for-react，规避其与 echarts 6 的 peer 约束） */

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { Chart } from '../../../types'
import { buildChartOption } from '../../../services/chart'

export default function ChartView({ chart }: { chart: Chart }) {
  const boxRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  // 实例惰性创建（组件内部无 SSR，DOM 可用）；图表变化时整体替换配置（notMerge 语义）
  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    if (!chartRef.current) chartRef.current = echarts.init(el)
    chartRef.current.setOption(buildChartOption(chart), { notMerge: true })
  }, [chart])

  // 窗口缩放自适应；卸载时销毁实例、释放 ZRender 资源
  useEffect(() => {
    const onResize = () => chartRef.current?.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chartRef.current?.dispose()
      chartRef.current = null
    }
  }, [])

  return (
    <div className="qa-chart-wrap" style={{ padding: 12, background: '#FAFBFC', borderRadius: 8 }}>
      <div ref={boxRef} style={{ height: 320 }} />
    </div>
  )
}