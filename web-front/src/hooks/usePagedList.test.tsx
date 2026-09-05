import { describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { usePagedList } from './usePagedList'

const items = Array.from({ length: 3 }, (_, i) => ({ id: i }))

describe('usePagedList', () => {
  it('挂载不触发请求，初始为空列表', () => {
    const fetcher = vi.fn(async () => ({ items, total: 3 }))
    const { result } = renderHook(() => usePagedList(fetcher))
    expect(fetcher).not.toHaveBeenCalled()
    expect(result.current.items).toEqual([])
    expect(result.current.total).toBe(0)
    expect(result.current.loading).toBe(false)
  })

  it('search 携带 page0/pageSize/filters 并落数据', async () => {
    const fetcher = vi.fn(async (q: { page: number; pageSize: number }) =>
      ({ items: q.page === 0 ? items : [], total: 3 }))
    const { result } = renderHook(() => usePagedList(fetcher, { pageSize: 5 }))
    await act(async () => {
      await result.current.search({ kw: 'x' })
    })
    expect(fetcher).toHaveBeenLastCalledWith({ page: 0, pageSize: 5, filters: { kw: 'x' } })
    expect(result.current.items).toEqual(items)
    expect(result.current.total).toBe(3)
    expect(result.current.loading).toBe(false)
  })

  it('changePage 用当前 filters 请求新页', async () => {
    const fetcher = vi.fn(async (q: { page: number; pageSize: number }) =>
      ({ items: [{ id: 99 }], total: 3 }))
    const { result } = renderHook(() => usePagedList(fetcher, { pageSize: 5 }))
    await act(async () => { await result.current.search({ kw: 'x' }) })
    await act(async () => { await result.current.changePage(1) })
    expect(fetcher).toHaveBeenLastCalledWith({ page: 1, pageSize: 5, filters: { kw: 'x' } })
    expect(result.current.items).toEqual([{ id: 99 }])
  })

  it('changeRowsPerPage 重置 page 为 0', async () => {
    const fetcher = vi.fn(async () => ({ items, total: 3 }))
    const { result } = renderHook(() => usePagedList(fetcher, { pageSize: 5 }))
    await act(async () => { await result.current.search({}) })
    await act(async () => { await result.current.changePage(1) })
    expect(result.current.page).toBe(1)
    await act(async () => { await result.current.changeRowsPerPage(20) })
    expect(result.current.page).toBe(0)
    expect(fetcher).toHaveBeenLastCalledWith({ page: 0, pageSize: 20, filters: {} })
  })

  it('请求失败触发 onError 且异常不外抛', async () => {
    const onError = vi.fn()
    const fetcher = vi.fn(async () => { throw new Error('boom') })
    const { result } = renderHook(() => usePagedList(fetcher, { onError, errorMessage: '加载失败' }))
    await act(async () => { await result.current.search({}) })
    expect(onError).toHaveBeenCalledWith('加载失败')
    expect(result.current.loading).toBe(false)
  })

  it('refresh 复用当前页码/每页/筛选', async () => {
    const fetcher = vi.fn(async () => ({ items, total: 3 }))
    const { result } = renderHook(() => usePagedList(fetcher, { pageSize: 5 }))
    await act(async () => { await result.current.search({ kw: 'y' }) })
    await act(async () => { await result.current.refresh() })
    expect(fetcher).toHaveBeenLastCalledWith({ page: 0, pageSize: 5, filters: { kw: 'y' } })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })
})