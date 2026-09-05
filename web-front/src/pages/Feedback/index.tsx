/** 回复校对页（原型 page-sys-feedback-user 1:1）：面包屑 + 卡片（标题行/筛选行/表格/分页） + 反馈处理弹窗 */

import { useCallback, useEffect, useState } from 'react'
import Breadcrumb from '../../components/Breadcrumb'
import { useSnackbar } from '../../hooks/useSnackbar'
import { usePagedList } from '../../hooks/usePagedList'
import { fetchFeedbackPage } from '../../services/feedback'
import type { FeedbackItem } from '../../types'
import FeedbackTable from './FeedbackTable'
import FeedbackDetailModal from './FeedbackDetailModal'

export default function Feedback() {
  const { showSnackbar } = useSnackbar()
  const {
    items, total, page, rowsPerPage, loading,
    search, changePage, changeRowsPerPage, refresh,
  } = usePagedList<FeedbackItem>(
    fetchFeedbackPage,
    { onError: showSnackbar, errorMessage: '反馈列表加载失败' },
  )
  const [kw, setKw] = useState('')
  const [userKw, setUserKw] = useState('')
  const [status, setStatus] = useState('')
  const [detail, setDetail] = useState<FeedbackItem | null>(null)

  useEffect(() => {
    refresh()
  }, [refresh])

  // 原型 oninput/onchange：输入即触发查询
  const changeKw = useCallback((v: string) => {
    setKw(v)
    void search({ search: v, userSearch: userKw, status })
  }, [search, userKw, status])

  const changeUserKw = useCallback((v: string) => {
    setUserKw(v)
    void search({ search: kw, userSearch: v, status })
  }, [search, kw, status])

  const changeStatus = useCallback((v: string) => {
    setStatus(v)
    void search({ search: kw, userSearch: userKw, status: v })
  }, [search, kw, userKw])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <Breadcrumb />
      <div className="pg-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px 0', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <span style={{ fontSize: 15, fontWeight: 600 }}>
              <i className="fas fa-exclamation-circle" style={{ color: 'var(--primary)' }} /> 回复校对
            </span>
            <span style={{ fontSize: 13, color: '#9CA3AF' }}>此列表为用户标注AI回复数据有误的信息数据</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <div className="pg-search" style={{ maxWidth: 180 }}>
                <i className="fas fa-search" />
                <input type="text" placeholder="搜索问题..." value={kw}
                  onChange={(e) => changeKw(e.target.value)} />
              </div>
              <div className="pg-search" style={{ maxWidth: 140 }}>
                <i className="fas fa-user" />
                <input type="text" placeholder="搜索用户..." value={userKw}
                  onChange={(e) => changeUserKw(e.target.value)} />
              </div>
              <select value={status} onChange={(e) => changeStatus(e.target.value)}
                style={{ height: 32, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 14, outline: 'none', background: '#fff', color: 'var(--text-body)' }}>
                <option value="">全部状态</option>
                <option value="待处理">待处理</option>
                <option value="已处理">已处理</option>
              </select>
            </div>
            <span style={{ fontSize: 14, color: 'var(--text-hint)', whiteSpace: 'nowrap' }}>
              <i className="fas fa-database" /> 共 <strong>{total}</strong> 条
            </span>
          </div>
        </div>
        <div style={{ padding: '12px 20px 16px' }}>
          <FeedbackTable items={items} loading={loading} total={total} page={page}
            rowsPerPage={rowsPerPage} onPageChange={changePage} onRowsPerPageChange={changeRowsPerPage}
            onHandle={setDetail} />
        </div>
      </div>

      <FeedbackDetailModal detail={detail} onClose={() => setDetail(null)} onSaved={refresh} />
    </div>
  )
}
