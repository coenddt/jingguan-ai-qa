/** AI 回复反馈弹窗（原型 optimizeModal 1:1 还原） */

import { useCallback } from 'react'
import Modal from '../../../components/Modal'
import { feedbackApi } from '../../../api/modules/feedback'
import { useSnackbar } from '../../../hooks/useSnackbar'

/** 原型提交文案：数据有误，实际数据与AI回复不一致 */
const FEEDBACK_DESC = '数据有误，实际数据与AI回复不一致'

interface Props {
  open: boolean
  sessionId: string
  question: string
  answer: string
  onClose: () => void
}

export default function AiFeedbackModal({ open, sessionId, question, answer, onClose }: Props) {
  const { showSnackbar } = useSnackbar()

  const close = useCallback(() => {
    onClose()
  }, [onClose])

  const submit = useCallback(() => {
    feedbackApi.create({ sessionId, question, answer, description: FEEDBACK_DESC })
      .then(() => {
        showSnackbar('您的数据问题反馈已提交，我们将尽快核查，感谢反馈', 'success')
        close()
      })
      .catch(() => showSnackbar('反馈提交失败，请稍后重试', 'error'))
  }, [sessionId, question, answer, showSnackbar, close])

  return (
    <Modal open={open} onClose={close} boxClassName="max-w-[480px]"
      title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-frown mr-1.5" style={{ color: '#2563EB' }} />AI回复反馈</h3>}
      showClose>
      <div style={{ fontSize: 15, color: '#374151', marginBottom: 14, lineHeight: 1.6 }}>请问你是对哪里不满意呢？</div>
      <button className="btn btn-light w-full whitespace-nowrap" style={{ height: 44, fontSize: 15 }} onClick={submit}>
        <i className="fas fa-exclamation-triangle mr-1" /> 数据有误，提交反馈
      </button>
    </Modal>
  )
}
