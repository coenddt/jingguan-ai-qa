import { useEffect, useState } from 'react'
import { RefreshCcw } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import SearchFilter from '../components/SearchFilter'
import Modal from '../components/Modal'
import CustomTablePagination from '../components/CustomTablePagination'
import EmptyTableRow from '../components/EmptyTableRow'
import TableSkeleton from '../components/TableSkeleton'
import MarkdownView from '../components/MarkdownView'
import { feedbackApi } from '../api/modules/feedback'
import { useSnackbar } from '../hooks/useSnackbar'
import { usePagedList } from '../hooks/usePagedList'
import { formatDateTime } from '../utils/date'
import type { FeedbackItem } from '../types'

export default function Feedback() {
  const { showSnackbar } = useSnackbar()
  const {
    items, total, page, rowsPerPage, loading, search, reset, changePage, changeRowsPerPage, refresh,
  } = usePagedList<FeedbackItem>(
    async ({ page, pageSize, filters }) => {
      const { data } = await feedbackApi.list({
        page: page + 1, pageSize,
        search: filters.search || undefined, userSearch: filters.userSearch || undefined,
        status: filters.status || undefined,
      })
      return data
    },
    { onError: showSnackbar, errorMessage: '反馈列表加载失败' },
  )
  const [detail, setDetail] = useState<FeedbackItem | null>(null)
  const [remark, setRemark] = useState('')

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const markDone = async () => {
    if (!detail) return
    await feedbackApi.update(detail.id, { status: '已处理', remark })
    showSnackbar('已标记处理完成', 'success')
    setDetail(null)
    setRemark('')
    refresh()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader title="回复校对" subtitle="用户反馈的处理工作台"
        onRefresh={refresh} />
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
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 mt-4 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table" style={{ minWidth: 850 }}>
            <thead>
              <tr>
                <th className="w-[160px]">时间</th>
                <th className="w-[110px]">用户</th>
                <th className="min-w-[140px] max-w-[280px]">问题</th>
                <th className="w-[90px]">状态</th>
                <th className="w-[100px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <TableSkeleton columns={5} /> :
                items.length ? items.map((f) => (
                  <tr key={f.id}>
                    <td className="text-xs text-gray-400 whitespace-nowrap">{formatDateTime(f.createdAt)}</td>
                    <td className="whitespace-nowrap">{f.userName}</td>
                    <td className="min-w-[140px] max-w-[280px] whitespace-normal break-words">{f.question}</td>
                    <td>
                      <span className={`badge badge-sm whitespace-nowrap ${f.status === '已处理' ? 'badge-success' : 'badge-warning'}`}>
                        {f.status}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-outline btn-xs whitespace-nowrap"
                        onClick={() => { setDetail(f); setRemark(f.remark) }}>查看</button>
                    </td>
                  </tr>
                )) : <EmptyTableRow colSpan={5} message="暂无反馈记录" />}
            </tbody>
          </table>
        </div>
        <CustomTablePagination total={total} page={page} rowsPerPage={rowsPerPage}
          onPageChange={changePage}
          onRowsPerPageChange={changeRowsPerPage} />
      </div>

      <Modal open={!!detail} onClose={() => setDetail(null)}
        title={<h3 className="font-bold text-lg">反馈详情</h3>} headerClassName="mb-3"
        boxClassName="max-w-xl"
        footer={<>
          <button className="btn btn-ghost whitespace-nowrap" onClick={() => setDetail(null)}>关闭</button>
          <button className="btn btn-primary whitespace-nowrap" onClick={markDone}>标记已处理</button>
        </>}>
        {detail && (
          <>
            <div className="text-sm text-gray-500 space-y-2 mb-3">
              <div><span className="font-bold text-gray-700">原问题：</span>{detail.question}</div>
              <div><span className="font-bold text-gray-700">用户描述：</span>{detail.description || '-'}</div>
            </div>
            <div className="bg-gray-50 rounded-xl p-4 max-h-56 overflow-auto mb-3">
              <MarkdownView content={detail.answer || '-'} />
            </div>
            <textarea className="textarea textarea-bordered w-full h-20 text-sm" placeholder="处理备注"
              value={remark} onChange={(e) => setRemark(e.target.value)} />
          </>
        )}
      </Modal>
    </div>
  )
}
