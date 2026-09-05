import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readJsonLS, writeJsonLS } from './localStorage'

// jsdom 环境未提供标准 Storage：注入内存版 stub
function stubLocalStorage() {
  let store = new Map<string, string>()
  const storage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => { store.set(k, String(v)) },
    clear: () => { store = new Map() },
  } as unknown as Storage
  vi.stubGlobal('localStorage', storage)
}

describe('localStorage', () => {
  beforeEach(() => {
    stubLocalStorage()
    localStorage.clear()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('readJsonLS 读到合法 JSON 返回解析值', () => {
    writeJsonLS('k', { a: 1 })
    expect(readJsonLS<{ a: number }>('k', { a: 0 })).toEqual({ a: 1 })
  })

  it('键不存在返回 fallback', () => {
    expect(readJsonLS('missing', 'fb')).toBe('fb')
  })

  it('损坏 JSON 返回 fallback 而非抛错', () => {
    localStorage.setItem('bad', '{oops')
    expect(readJsonLS('bad', 0)).toBe(0)
  })
})