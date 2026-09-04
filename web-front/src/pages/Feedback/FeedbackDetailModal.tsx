/** 反馈详情处理弹窗（Feedback 页使用，受控：remark 由页面持有） */

import { type ChangeEvent } from 'react'
import type { FeedbackItem } from '../../types'
import Modal from '../../components/Modal'
import MarkdownView from '../../components/MarkdownView'

interface Props {
  detail: FeedbackItem | null
  remark: string
  onChangeRemark: (e: ChangeEvent<HTMLTextAreaElement>) => void
  onMarkDone: () => void
  onClose: () => void
}

export default function FeedbackDetailModal({ detail, remark, onChangeRemark, onMarkDone, onClose }: Props) {
  return (
    <Modal open={!!detail} onClose={onClose}
      title={<h3 className="font-bold text-lg">反馈详情</h3>} headerClassName="mb-3"
      boxClassName="max-w-xl"
      footer={<>
        <button className="btn btn-ghost whitespace-nowrap" onClick={onClose}>关闭</button>
        <button className="btn btn-primary whitespace-nowrap" onClick={onMarkDone}>标记已处理</button>
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
            value={remark} onChange={onChangeRemark} />
        </>
      )}
    </Modal>
  )
}
