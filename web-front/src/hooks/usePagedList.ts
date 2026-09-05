import { useCallback, useEffect, useRef, useState } from 'react'
import type { PageFilters, PagedQuery } from '../types'

interface Options {
  pageSize?: number
  onError?: (message: string) => void
  errorMessage?: string
}

/** 分页列表状态 hook：items/total/page/rowsPerPage/loading/filters + 动作。
 *  fetcher/options 走 ref（保证动作引用稳定，调用方可安全作为 useEffect 依赖）；
 *  所有动作显式传参调用 load，杜绝闭包旧值；失败统一走 onError */
export function usePagedList<T, F extends PageFilters = PageFilters>(
  fetcher: (q: PagedQuery<F>) => Promise<{ items: T[]; total: number }>,
  options?: Options,
) {
  const [items, setItems] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(options?.pageSize ?? 10)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<F>({} as F)
  const fetcherRef = useRef(fetcher)
  const optsRef = useRef(options)
  const stateRef = useRef({ page, rowsPerPage, filters })
  // 三个 ref 统一在 effect 中同步（渲染期写 ref 属 React 反模式）；初始值由 useRef 惰性承担，
  // 动作仅从事件回调触发（此时 effect 已 flush），读到的恒为最新值
  useEffect(() => {
    fetcherRef.current = fetcher
    optsRef.current = options
    stateRef.current = { page, rowsPerPage, filters }
  })

  const load = useCallback(async (p: number, size: number, f: F) => {
    setLoading(true)
    try {
      const data = await fetcherRef.current({ page: p, pageSize: size, filters: f })
      setItems(data.items)
      setTotal(data.total)
    } catch {
      const opts = optsRef.current
      opts?.onError?.(opts.errorMessage ?? '列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const search = useCallback((f: F) => {
    setFilters(f)
    setPage(0)
    return load(0, stateRef.current.rowsPerPage, f)
  }, [load])

  const reset = useCallback(() => {
    const f = {} as F
    setFilters(f)
    setPage(0)
    return load(0, stateRef.current.rowsPerPage, f)
  }, [load])

  const changePage = useCallback((p: number) => {
    setPage(p)
    return load(p, stateRef.current.rowsPerPage, stateRef.current.filters)
  }, [load])

  const changeRowsPerPage = useCallback((n: number) => {
    setRowsPerPage(n)
    setPage(0)
    return load(0, n, stateRef.current.filters)
  }, [load])

  const refresh = useCallback(
    () => load(stateRef.current.page, stateRef.current.rowsPerPage, stateRef.current.filters),
    [load],
  )

  return { items, total, page, rowsPerPage, loading, filters, search, reset, changePage, changeRowsPerPage, refresh }
}
