import { describe, expect, it } from 'vitest'
import type { AxiosError } from 'axios'
import { httpCanRetry, httpRetryDelay, retrySetting } from './client'

/** 构造最小 AxiosError 状对象 */
function err(method: string, hasResponse: boolean): AxiosError {
  return {
    config: { method },
    response: hasResponse ? ({ data: {}, status: 500 } as unknown as AxiosError['response']) : undefined,
    isAxiosError: true,
    name: 'AxiosError',
    message: 'err',
  } as AxiosError
}

describe('client 断网重试策略', () => {
  it('GET 网络层失败（无响应体）且未超限 → 允许重试', () => {
    expect(httpCanRetry(err('get', false), 0, { maxRetries: 2, baseDelayMs: 1 })).toBe(true)
    expect(httpCanRetry(err('GET', false), 0, { maxRetries: 2, baseDelayMs: 1 })).toBe(true)
  })

  it('已达最大重试次数 → 不允许再重试', () => {
    expect(httpCanRetry(err('get', false), retrySetting.maxRetries, retrySetting)).toBe(false)
  })

  it('有响应体的失败（业务/鉴权）→ 不盲目重试', () => {
    expect(httpCanRetry(err('get', true), 0, retrySetting)).toBe(false)
  })

  it('非 GET（含写操作 POST/PATCH）→ 不重试，避免重复提交', () => {
    expect(httpCanRetry(err('post', false), 0, retrySetting)).toBe(false)
    expect(httpCanRetry(err('delete', false), 0, retrySetting)).toBe(false)
    expect(httpCanRetry(err('patch', false), 0, retrySetting)).toBe(false)
  })

  it('退避延迟随重试次数指数增长', () => {
    expect(httpRetryDelay({ _retryCount: 0 }, { maxRetries: 3, baseDelayMs: 300 })).toBe(300)
    expect(httpRetryDelay({ _retryCount: 1 }, { maxRetries: 3, baseDelayMs: 300 })).toBe(600)
    expect(httpRetryDelay({ _retryCount: 2 }, { maxRetries: 3, baseDelayMs: 300 })).toBe(1200)
  })
})