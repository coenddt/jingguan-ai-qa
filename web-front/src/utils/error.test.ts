import { describe, expect, it } from 'vitest'
import { getApiErrorMsg } from './error'

describe('getApiErrorMsg', () => {
  it('提取 axios 响应体 detail 文案', () => {
    const e = { response: { data: { detail: '模型不存在' } } }
    expect(getApiErrorMsg(e)).toBe('模型不存在')
  })

  it('无 response/detail 返回 undefined', () => {
    expect(getApiErrorMsg('plain')).toBeUndefined()
    expect(getApiErrorMsg({ response: { data: {} } })).toBeUndefined()
    expect(getApiErrorMsg(undefined)).toBeUndefined()
  })
})