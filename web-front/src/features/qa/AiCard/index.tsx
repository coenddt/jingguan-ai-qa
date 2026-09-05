/** AI 回答结构化卡片（原型 qa-ai-card 1:1）：分析过程 → 数据发现 → 数据表格 → 数据统计 → 数据可视化 → 结论 → 页脚 → 追问
 *  流式：streaming 时按块到达顺序渲染，未到达的块显示生成中占位 */

import { lazy, Suspense, useCallback, useState } from 'react'
import type { QaAskResp } from '../../../types'
import MarkdownView from '../../../components/MarkdownView'
import { useSnackbar } from '../../../hooks/useSnackbar'
import { buildAiCardCopyText } from '../../../services/qa'
import { copyToClipboard } from '../../../services/clipboard'
import AiSteps from './AiSteps'
import AiDataTable from './AiDataTable'
import AiStatsGrid from './AiStatsGrid'
import AiCardFooter from './AiCardFooter'
import AiFollowUps from './AiFollowUps'
import AiFeedbackModal from './AiFeedbackModal'
import { Module, BlkPending, BlkEmpty } from './qaBlocks'

// ECharts 按需分包：仅当回复含图表时才加载图表 chunk
const ChartView = lazy(() => import('../charts'))

interface Props {
  resp: Partial<QaAskResp>
  question: string
  streaming?: boolean
  /** 消息落库时间，透传至页脚展示（避免重渲染时显示时间漂移） */
  createdAt?: string
}

export default function AiCard({ resp, question, streaming, createdAt }: Props) {
  const [openSteps, setOpenSteps] = useState(!!streaming)
  const [copied, setCopied] = useState(false)
  const [fbOpen, setFbOpen] = useState(false)
  const { showSnackbar } = useSnackbar()

  const toggleSteps = useCallback(() => setOpenSteps((v) => !v), [])

  const handleCopy = useCallback(() => {
    copyToClipboard(buildAiCardCopyText(resp as QaAskResp))
      .then(() => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
      })
      .catch(() => showSnackbar('复制失败，请稍后重试', 'error'))
  }, [resp, showSnackbar])

  const openFeedback = useCallback(() => setFbOpen(true), [])
  const closeFeedback = useCallback(() => setFbOpen(false), [])

  // 流式中按「块是否已到达」渲染：到达→内容，未到达→占位
  const hasFindings = !streaming || 'findings' in resp
  const hasTable = !streaming || 'columns' in resp
  const hasStats = !streaming || 'stats' in resp
  const hasChart = !streaming || 'chart' in resp
  const hasText = !streaming || 'text' in resp

  // 条件不足澄清卡：不渲染完整报告块
  if (resp.clarify) {
    return (
      <div className="qa-ai-msg">
        <div className="qa-ai-card">
          <div className="qa-ai-avatar" style={{ marginBottom: 12 }}><i className="fas fa-robot" /></div>
          <div className="mod-body">
            <div className="dot-li">{resp.clarify}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="qa-ai-msg">
      <div className="qa-ai-card">
        <div className="qa-ai-avatar" style={{ marginBottom: 12 }}><i className="fas fa-robot" /></div>

        {/* ① 分析过程（流式时默认展开，逐步点亮） */}
        <AiSteps open={openSteps} onToggle={toggleSteps} steps={resp.steps ?? []} />

        {/* ② 数据发现 */}
        <Module num={1} title="数据发现">
          {hasFindings ? (
            <div className="mod-body">
              {(resp.findings ?? []).map((f, i) => <div key={i} className="dot-li">{f}</div>)}
            </div>
          ) : <BlkPending />}
        </Module>

        {/* ③ 数据表格 */}
        <Module num={2} title="数据表格">
          {hasTable ? (
            resp.rows?.length ? (
              <AiDataTable columns={resp.columns ?? []} rows={resp.rows} totalCount={resp.stats?.count ?? 0} />
            ) : <BlkEmpty text="无表格数据" />
          ) : <BlkPending />}
        </Module>

        {/* ④ 数据统计 */}
        <Module num={3} title="数据统计">
          {hasStats ? <AiStatsGrid stat={resp.stats!} /> : <BlkPending />}
        </Module>

        {/* ⑤ 数据可视化 */}
        <Module num={4} title="数据可视化">
          {hasChart ? (
            resp.chart && (
              <div className="qa-ai-chart">
                <div className="chart-desc">{resp.chart.title}{resp.chart.unit ? `（单位：${resp.chart.unit}）` : ''}：</div>
                <Suspense fallback={<div className="text-sm text-slate-400 py-2">图表加载中…</div>}>
                  <ChartView chart={resp.chart} />
                </Suspense>
              </div>
            )
          ) : <BlkPending />}
        </Module>

        {/* 结论 */}
        {hasText ? (
          !!resp.text && <MarkdownView content={resp.text} />
        ) : <BlkPending />}

        {/* 页脚 + 追问 chips：完成后才渲染 */}
        {!streaming && resp.meta && (
          <>
            <AiCardFooter resp={resp as QaAskResp} copied={copied} onCopy={handleCopy} onFeedback={openFeedback} createdAt={createdAt} />
            <AiFollowUps followUps={resp.follow_ups ?? []} />
            <AiFeedbackModal open={fbOpen} sessionId={resp.session_id ?? ''} question={question} answer={resp.text ?? ''}
              onClose={closeFeedback} />
          </>
        )}
      </div>
    </div>
  )
}
