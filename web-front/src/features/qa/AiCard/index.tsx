/** AI 回答结构化卡片：分析过程 → 数据发现 → 表格 → 统计 → 图表 → 结论 → 页脚 → 追问 */

import { useCallback, useState, type ChangeEvent } from 'react'
import type { QaAskResp } from '../../../types'
import MarkdownView from '../../../components/MarkdownView'
import ChartView from '../charts'
import { useSnackbar } from '../../../hooks/useSnackbar'
import { buildAiCardCopyText } from '../../../services/qa'
import { copyToClipboard } from '../../../services/clipboard'
import AiSteps from './AiSteps'
import AiDataTable from './AiDataTable'
import AiStatsGrid from './AiStatsGrid'
import AiCardFooter from './AiCardFooter'
import AiFollowUps from './AiFollowUps'
import AiFeedbackModal from './AiFeedbackModal'

interface Props {
  resp: QaAskResp
  question: string
}

export default function AiCard({ resp, question }: Props) {
  const [openSteps, setOpenSteps] = useState(false)
  const [copied, setCopied] = useState(false)
  const [fbOpen, setFbOpen] = useState(false)
  const { showSnackbar } = useSnackbar()

  const changeSteps = useCallback((e: ChangeEvent<HTMLInputElement>) => setOpenSteps(e.target.checked), [])

  const handleCopy = useCallback(() => {
    copyToClipboard(buildAiCardCopyText(resp))
      .then(() => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
      })
      .catch(() => showSnackbar('复制失败，请稍后重试', 'error'))
  }, [resp, showSnackbar])

  const openFeedback = useCallback(() => setFbOpen(true), [])
  const closeFeedback = useCallback(() => setFbOpen(false), [])

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4 max-w-[860px]">
      {/* ① 分析过程 */}
      <AiSteps open={openSteps} onChange={changeSteps} steps={resp.steps} />

      {/* ② 数据发现 */}
      {!!resp.findings.length && (
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          {resp.findings.map((f, i) => <li key={i}>{f}</li>)}
        </ul>
      )}

      {/* ③ 数据表格 */}
      <AiDataTable columns={resp.columns} rows={resp.rows} totalCount={resp.stats.count} />

      {/* ④ 数据统计 */}
      <AiStatsGrid stat={resp.stats} />

      {/* ⑤ 数据可视化 */}
      {resp.chart && <ChartView chart={resp.chart} />}

      {/* ⑥ 结论 */}
      <MarkdownView content={resp.text} />

      {/* 页脚 */}
      <AiCardFooter resp={resp} copied={copied} onCopy={handleCopy} onFeedback={openFeedback} />

      {/* ⑦ 追问 chips */}
      <AiFollowUps followUps={resp.follow_ups} />

      {/* 反馈弹窗 */}
      <AiFeedbackModal open={fbOpen} sessionId={resp.session_id} question={question} answer={resp.text}
        onClose={closeFeedback} />
    </div>
  )
}
