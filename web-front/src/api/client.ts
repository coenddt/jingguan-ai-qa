import axios from 'axios'
import type { AxiosError, AxiosRequestConfig } from 'axios'

export const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 60000,
})

interface RetryConfig extends AxiosRequestConfig {
  _retryCount?: number
}

export interface RetrySetting {
  maxRetries: number
  baseDelayMs: number
}

export const retrySetting: RetrySetting = { maxRetries: 2, baseDelayMs: 300 }

// 401 → 未登录/过期：广播事件，App.tsx 统一跳登录
http.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const cfg = error.config as RetryConfig | undefined
    // 断网降级重试：仅网络层失败（无响应体，非 4xx/5xx）× GET × 未超上限
    if (cfg && httpCanRetry(error, cfg._retryCount ?? 0)) {
      cfg._retryCount = (cfg._retryCount ?? 0) + 1
      await new Promise((r) => setTimeout(r, httpRetryDelay(cfg)))
      return http(cfg)
    }
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(error)
  },
)

/** 断网重试判定：网络/连接层失败（无 response 体），且仅安全幂等的 GET，且未超次数 */
export function httpCanRetry(error: AxiosError, retryCount: number, setting: RetrySetting = retrySetting): boolean {
  if (retryCount >= setting.maxRetries) return false
  if (error.response) return false // 有响应体：属于服务端业务/鉴权失败，禁止盲目重试
  return (error.config?.method ?? '').toLowerCase() === 'get'
}

/** 退避延迟 = baseDelay × 2^已重试次数 */
export function httpRetryDelay(config: { _retryCount?: number }, setting: RetrySetting = retrySetting): number {
  return setting.baseDelayMs * 2 ** (config._retryCount ?? 0)
}
