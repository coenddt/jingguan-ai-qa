/** 回复校对反馈弹窗（AiCard 使用） */

import { useCallback, useState, type ChangeEvent } from 'react'
import Modal from '../../../components/Modal'
import { feedbackApi } from '../../../api/modules/feedback'
import { useSnackbar } from '../../../hooks/useSnackbar'

interface Props {
  open: boolean
  sessionId: string
  question: string
  answer: string
  onClose: () => void
}

export default function AiFeedbackModal({ open, sessionId, question, answer, onClose }: Props) {
  const [text, setText] = useState('')
  const { showSnackbar } = useSnackbar()

  const changeText = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => setText(e.target.value), [])

  const close = useCallback(() => {
    setText('')
    onClose()
  }, [onClose])

  const submit = useCallback(() => {
    feedbackApi.create({ sessionId, question, answer, description: text })
      .then(() => {
        showSnackbar('反馈已提交，感谢校对', 'success')
        close()
      })
      .catch(() => showSnackbar('反馈提交失败，请稍后重试', 'error'))
  }, [sessionId, question, answer, text, showSnackbar, close])

  return (
    <Modal open={open} onClose={close}
      title={<h3 className="font-bold text-lg">回复校对</h3>} headerClassName="mb-3"
      footer={<>
        <button className="btn btn-ghost whitespace-nowrap" onClick={close}>取消</button>
        <button className="btn btn-primary whitespace-nowrap" disabled={!text.trim()} onClick={submit}>提交</button>
      </>}>
      <textarea className="textarea textarea-bordered w-full h-24" placeholder="描述问题（如数据不符/图表有误）"
        value={text} onChange={changeText} />
    </Modal>
  )
}
