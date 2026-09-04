import { useCallback, useRef, useState } from 'react'

export interface PagedQuery<F> {
  /** 0 起始页码 */
  page: number
  pageSize: number
  filters: F
}

interface Options<F> {
  pageSize?: number
  onError?: (message: string) => void
  errorMessage?: string
}

/** 分页列表状态 hook：items/total/page/rowsPerPage/loading/filters + 动作。
 *  所有动作内部显式传参调用 load，杜绝闭包旧值；失败统一走 onError */
export function usePagedList<T, F extends Record<string, string> = Record<string, string>>(
  fetcher: (q: PagedQuery<F>) => Promise<{ items: T[]; total: number }>,
  options?: Options<F>,
) {
  const [items, setItems] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(options?.pageSize ?? 10)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<F>({} as F)
  const optsRef = useRef(options)
  optsRef.current = options

  const load = useCallback(async (p: number, size: number, f: F) => {
    setLoading(true)
    try {
      const data = await fetcher({ page: p, pageSize: size, filters: f })
      setItems(data.items)
      setTotal(data.total)
    } catch {
      const opts = optsRef.current
      opts?.onError?.(opts.errorMessage ?? '列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [fetcher])

  const search = (f: F) => {
    setFilters(f)
    setPage(0)
    load(0, rowsPerPage, f)
  }

  const reset = () => {
    const f = {} as F
    setFilters(f)
    setPage(0)
    load(0, rowsPerPage, f)
  }

  const changePage = (p: number) => {
    setPage(p)
    load(p, rowsPerPage, filters)
  }

  const changeRowsPerPage = (n: number) => {
    setRowsPerPage(n)
    setPage(0)
    load(0, n, filters)
  }

  const refresh = () => load(page, rowsPerPage, filters)

  return { items, total, page, rowsPerPage, loading, filters, search, reset, changePage, changeRowsPerPage, refresh }
}
