import axios from 'axios'
import type { AxiosError } from 'axios'

export const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 60000,
})

// 401 → 未登录/过期：广播事件，App.tsx 统一跳登录
http.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(err)
  },
)
