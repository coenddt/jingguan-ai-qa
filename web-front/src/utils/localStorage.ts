/** localStorage JSON 读写统一出口：解析失败/空值回退 fallback */

export function readJsonLS<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export function writeJsonLS(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value))
}
