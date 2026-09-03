import { http } from '../client'

export const authApi = {
  login: (username: string, password: string) =>
    http.post<{ ok: boolean; user: string }>('/auth/login', { username, password }),
  logout: () => http.post<{ ok: boolean }>('/auth/logout'),
  check: () => http.get<{ ok: boolean; user: string }>('/auth/check'),
}
