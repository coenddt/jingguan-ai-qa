import { useState } from 'react'
import { Check, ChevronDown, Copy, ThumbsDown } from 'lucide-react'
import type { QaAskResp } from '../../types'
import MarkdownView from '../../components/MarkdownView'
import ChartView from './charts'
import TtsButton from './TtsButton'
import { feedbackApi } from '../../api/modules/feedback'
import { useSnackbar } from '../../hooks/useSnackbar'
import { formatDateTime } from '../../utils/date'

export default function AiCard({ resp, question }: { resp: QaAskResp; question: string }) {
  const [openSteps, setOpenSteps] = useState(false)
  const [copied, setCopied] = useState(false)
  const [fbOpen, setFbOpen] = useState(false)
  const [fbText, setFbText] = useState('')
  const { showSnackbar } = useSnackbar()

  const copyAll = async () => {
    const lines = [
      resp.text,
      ...resp.columns.map((c, i) => `${c}: ${resp.rows.map((r) => r[i]).join('、')}`),
    ]
    await navigator.clipboard.writeText(lines.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const submitFeedback = async () => {
    await feedbackApi.create({ sessionId: resp.session_id, question, answer: resp.text, description: fbText })
    setFbOpen(false)
    setFbText('')
    showSnackbar('反馈已提交，感谢校对', 'success')
  }

  const stat = resp.stats
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4 max-w-[860px]">
      {/* ① 分析过程 */}
      <div className="collapse collapse-arrow bg-base-100 border border-gray-200 rounded-xl">
        <input type="checkbox" checked={openSteps} onChange={(e) => setOpenSteps(e.target.checked)} />
        <div className="collapse-title text-sm font-bold text-gray-600 pr-2">分析过程</div>
        <div className="collapse-content">
          <ul className="space-y-2">
            {resp.steps.map((s, i) => (
              <li key={i} className="flex gap-2 text-sm">
                {s.done && <Check size={16} className="text-success shrink-0 mt-0.5" />}
                <div>
                  <span className="font-bold text-gray-700">{s.title}</span>
                  {s.desc && <div className="text-gray-500 break-all">{s.desc}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ② 数据发现 */}
      {!!resp.findings.length && (
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          {resp.findings.map((f, i) => <li key={i}>{f}</li>)}
        </ul>
      )}

      {/* ③ 数据表格 */}
      {!!resp.rows.length && (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="table table-sm">
            <thead>
              <tr>{resp.columns.map((c) => <th key={c} className="whitespace-nowrap">{c}</th>)}</tr>
            </thead>
            <tbody>
              {resp.rows.map((row, i) => (
                <tr key={i}>{row.map((cell, j) => <td key={j} className="whitespace-nowrap">{String(cell)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {resp.rows.length >= 200 && (
        <div className="text-xs text-warning">共 {stat.count} 条已截断（上限 200 条）</div>
      )}

      {/* ④ 数据统计 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-50 rounded-xl p-3">
          <div className="text-xs text-gray-400">记录数</div>
          <div className="text-lg font-extrabold text-primary">{stat.count}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-3">
          <div className="text-xs text-gray-400">均值</div>
          <div className="text-lg font-extrabold text-primary">{stat.avg}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-3">
          <div className="text-xs text-gray-400">最大值</div>
          <div className="text-lg font-extrabold text-gold-deep">{stat.max}<span className="text-xs font-medium text-gray-400 ml-1">{stat.max_of}</span></div>
        </div>
        <div className="bg-gray-50 rounded-xl p-3">
          <div className="text-xs text-gray-400">最小值</div>
          <div className="text-lg font-extrabold text-primary">{stat.min}<span className="text-xs font-medium text-gray-400 ml-1">{stat.min_of}</span></div>
        </div>
      </div>

      {/* ⑤ 数据可视化 */}
      {resp.chart && <ChartView chart={resp.chart} />}

      {/* ⑥ 结论 */}
      <MarkdownView content={resp.text} />

      {/* 页脚 */}
      <div className="flex items-center gap-1 pt-1 border-t border-gray-100 text-gray-500">
        <button className="btn btn-ghost btn-xs gap-1 whitespace-nowrap" onClick={copyAll}>
          {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />} 复制
        </button>
        <button className="btn btn-ghost btn-xs gap-1 whitespace-nowrap" onClick={() => setFbOpen(true)}>
          <ThumbsDown size={13} /> 反馈
        </button>
        <TtsButton text={resp.text} />
        <span className="ml-auto text-[11px] text-gray-400">
          耗时 {resp.meta.elapsed_s}s · Tokens {resp.meta.tokens} · {formatDateTime(Date.now())}
        </span>
      </div>

      {/* ⑦ 追问 chips */}
      {!!resp.follow_ups.length && (
        <div className="flex flex-wrap gap-2">
          {resp.follow_ups.map((f) => (
            <button key={f} className="btn btn-outline btn-xs rounded-full whitespace-nowrap text-gray-600"
              onClick={() => window.dispatchEvent(new CustomEvent('qa:ask', { detail: f }))}>
              {f}
            </button>
          ))}
        </div>
      )}

      {/* 反馈弹窗 */}
      {fbOpen && (
        <dialog className="modal modal-open" onClick={() => setFbOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-bold text-lg mb-3">回复校对</h3>
            <textarea className="textarea textarea-bordered w-full h-24" placeholder="描述问题（如数据不符/图表有误）"
              value={fbText} onChange={(e) => setFbText(e.target.value)} />
            <div className="modal-action">
              <button className="btn btn-ghost whitespace-nowrap" onClick={() => setFbOpen(false)}>取消</button>
              <button className="btn btn-primary whitespace-nowrap" disabled={!fbText.trim()} onClick={submitFeedback}>提交</button>
            </div>
          </div>
        </dialog>
      )}
    </div>
  )
}
