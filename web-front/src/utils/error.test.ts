import { describe, expect, it } from 'vitest'
import { getApiErrorMsg, getErrorMessage } from './error'

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

describe('getErrorMessage（错因透出，供失败态 snackbar）', () => {
  it('优先后端 detail（axios 结构）', () => {
    const e = { response: { data: { detail: '模型不存在' } } }
    expect(getErrorMessage(e)).toBe('模型不存在')
  })

  it('普通 Error.message 兜底透出（SSE 流内 error 事件 message 场景）', () => {
    expect(getErrorMessage(new Error('模型调用失败：请求超时'))).toBe('模型调用失败：请求超时')
  })

  it('两者皆无时返回 undefined（触发调用侧兜底文案）', () => {
    expect(getErrorMessage('plain')).toBeUndefined()
    expect(getErrorMessage(undefined)).toBeUndefined()
  })
})