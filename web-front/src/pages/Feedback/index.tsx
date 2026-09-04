/** 回复校对页：反馈列表 + 详情处理 */

import { useCallback, useEffect, useState } from 'react'
import PageHeader from '../../components/PageHeader'
import SearchFilter from '../../components/SearchFilter'
import { feedbackApi } from '../../api/modules/feedback'
import { useSnackbar } from '../../hooks/useSnackbar'
import { usePagedList } from '../../hooks/usePagedList'
import { fetchFeedbackPage } from '../../services/feedback'
import type { ChangeEvent } from 'react'
import type { FeedbackItem } from '../../types'
import FeedbackTable from './FeedbackTable'
import FeedbackDetailModal from './FeedbackDetailModal'

export default function Feedback() {
  const { showSnackbar } = useSnackbar()
  const {
    items, total, page, rowsPerPage, loading, search, reset, changePage, changeRowsPerPage, refresh,
  } = usePagedList<FeedbackItem>(
    fetchFeedbackPage,
    { onError: showSnackbar, errorMessage: '反馈列表加载失败' },
  )
  const [detail, setDetail] = useState<FeedbackItem | null>(null)
  const [remark, setRemark] = useState('')

  useEffect(() => {
    refresh()
  }, [refresh])

  const openDetail = useCallback((f: FeedbackItem) => {
    setDetail(f)
    setRemark(f.remark)
  }, [])

  const closeDetail = useCallback(() => setDetail(null), [])

  const changeRemark = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => setRemark(e.target.value), [])

  const markDone = useCallback(() => {
    if (!detail) return
    feedbackApi.update(detail.id, { status: '已处理', remark })
      .then(() => {
        showSnackbar('已标记处理完成', 'success')
        setDetail(null)
        setRemark('')
        refresh()
      })
      .catch(() => showSnackbar('处理失败，请稍后重试', 'error'))
  }, [detail, remark, refresh, showSnackbar])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader title="回复校对" subtitle="用户反馈的处理工作台" onRefresh={refresh} />
      <SearchFilter
        fields={[
          { name: 'search', type: 'text', placeholder: '搜索问题内容' },
          { name: 'userSearch', type: 'text', placeholder: '搜索用户' },
          { name: 'status', type: 'select', label: '状态', options: [
            { value: '', label: '全部' }, { value: '待处理', label: '待处理' }, { value: '已处理', label: '已处理' },
          ] },
        ]}
        onSearch={search}
        onReset={reset}
      />
      <FeedbackTable items={items} loading={loading} total={total} page={page} rowsPerPage={rowsPerPage}
        onPageChange={changePage} onRowsPerPageChange={changeRowsPerPage} onView={openDetail} />

      <FeedbackDetailModal detail={detail} remark={remark} onChangeRemark={changeRemark}
        onMarkDone={markDone} onClose={closeDetail} />
    </div>
  )
}
