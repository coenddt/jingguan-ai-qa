import { describe, expect, it } from 'vitest'
import { normalizeMarkdown } from './markdown'

describe('normalizeMarkdown', () => {
  it('空串/空输入原样返回', () => {
    expect(normalizeMarkdown('')).toBe('')
    expect(normalizeMarkdown(undefined as unknown as string)).toBe(undefined)
  })

  it('标题 # 与内容间补空格', () => {
    expect(normalizeMarkdown('#结论')).toBe('# 结论')
    expect(normalizeMarkdown('第一行\n##发现')).toBe('第一行\n## 发现')
    // 行内 # 不处理
    expect(normalizeMarkdown('a#b')).toBe('a#b')
  })

  it('引用 > 与列表 -/+ 补空格', () => {
    expect(normalizeMarkdown('>重点')).toBe('> 重点')
    expect(normalizeMarkdown('-条目')).toBe('- 条目')
    expect(normalizeMarkdown('+条目')).toBe('+ 条目')
  })
})