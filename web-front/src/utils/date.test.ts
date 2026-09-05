import { describe, expect, it } from 'vitest'
import { formatDateTime, formatClock } from './date'

describe('formatDateTime', () => {
  it('合法时间格式化为 YYYY-MM-DD HH:mm', () => {
    expect(formatDateTime('2026-09-05T08:10:00')).toBe('2026-09-05 08:10')
  })

  it('空/无效返回 -', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('not-a-date')).toBe('-')
  })
})

describe('formatClock', () => {
  it('合法时间格式化为 HH:mm:ss', () => {
    expect(formatClock('2026-09-05T08:10:30')).toBe('08:10:30')
  })

  it('空/无效返回 -', () => {
    expect(formatClock('')).toBe('-')
    expect(formatClock('nope')).toBe('-')
  })
})