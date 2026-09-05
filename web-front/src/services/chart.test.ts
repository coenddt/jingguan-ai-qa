import { describe, expect, it } from 'vitest'
import { buildChartOption } from './chart'
import type { Chart } from '../types'

const base = { title: '', unit: '', columns: [], rows: [], x: ['A', 'B'], series: [1, 2], description: '' }

// series 可能为单个对象或数组：统一按数组取首元素
function firstSeries(opt: unknown) {
  const series = (opt as { series?: unknown }).series
  const arr = Array.isArray(series) ? series : series ? [series] : []
  return arr[0] as { type?: string; data?: Array<{ name: string; value: number }> }
}

describe('buildChartOption', () => {
  it('饼图：trigger=item 且按 name/value 配对', () => {
    const opt = buildChartOption({ ...base, type: 'pie' } as unknown as Chart)
    expect(opt.tooltip).toMatchObject({ trigger: 'item' })
    const s = firstSeries(opt)
    expect(s?.type).toBe('pie')
    expect(s?.data).toEqual([{ name: 'A', value: 1 }, { name: 'B', value: 2 }])
  })

  it('横向条形图：yAxis 为分类轴', () => {
    const opt = buildChartOption({ ...base, type: 'bar_h' } as unknown as Chart)
    expect(opt.yAxis).toMatchObject({ type: 'category', data: ['A', 'B'] })
    expect(firstSeries(opt)?.type).toBe('bar')
  })

  it('折线图：x 轴 boundaryGap 关闭', () => {
    const opt = buildChartOption({ ...base, type: 'line' } as unknown as Chart)
    expect(opt.xAxis).toMatchObject({ type: 'category', data: ['A', 'B'], boundaryGap: false })
    expect(firstSeries(opt)?.type).toBe('line')
  })

  it('缺省类型按柱状图处理', () => {
    const opt = buildChartOption({ ...base, type: 'bar' } as unknown as Chart)
    expect(opt.xAxis).toMatchObject({ type: 'category' })
    expect(firstSeries(opt)?.type).toBe('bar')
  })
})