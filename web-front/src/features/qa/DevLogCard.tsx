/** 开发者日志卡片：完整复现 AI 回答全链路（分析过程/查询调试/数据/图表/结论/追问/原始日志）
 *  仅用于日志详情弹窗，供开发人员排查；历史老数据缺新字段时防御性降级 */

import { lazy, Suspense, useCallback, useState } from 'react'
import type { QaAskResp } from '../../types'
import MarkdownView from '../../components/MarkdownView'
import AiSteps from './AiCard/AiSteps'
import AiDataTable from './AiCard/AiDataTable'
import AiStatsGrid from './AiCard/AiStatsGrid'
import { Module, BlkEmpty } from './AiCard/qaBlocks'
import { copyToClipboard } from '../../services/clipboard'

// ECharts 按需分包：仅当日志含图表才加载图表 chunk，避免其进主包/首屏
const ChartView = lazy(() => import('./charts'))

interface Props {
  /** 消息 aiMeta（历史数据可能缺少新字段，需防御性渲染） */
  resp: Partial<QaAskResp>
}

export default function DevLogCard({ resp }: Props) {
  const [openSteps, setOpenSteps] = useState(true) // 开发者默认展开分析过程
  const [copied, setCopied] = useState(false)
  const meta = resp.meta

  const dump = useCallback((v: unknown) => {
    try {
      return JSON.stringify(v, null, 2)
    } catch {
      return String(v)
    }
  }, [])

  const handleCopyRaw = useCallback(() => {
    copyToClipboard(dump(resp)).then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    }).catch(() => undefined)
  }, [resp, dump])

  const modelLabel = [meta?.model, meta?.modelName, meta?.platform].filter(Boolean).join(' · ') || '-'

  return (
    <div className="qa-ai-card" style={{ padding: '10px 14px', flex: 1, minWidth: 0 }}>
      {/* ⓪ 失败横幅：问数失败时醒目展示错误详情 */}
      {!!resp.error && (
        <div className="dev-error-banner">
          <i className="fas fa-exclamation-triangle" /> 本次问数失败：
          <pre className="dev-error-pre">{resp.error}</pre>
        </div>
      )}

      {/* ① 分析过程（完整 5 步中间产物 + 每步时间戳/耗时） */}
      <AiSteps open={openSteps} onToggle={() => setOpenSteps((v) => !v)} steps={resp.steps ?? []} showTime />

      {/* ② 查询调试（新字段，老数据缺字段时显示 -） */}
      <Module num={1} title="查询调试">
        <div className="dev-meta-grid">
          <span>来源：<b>{resp.query_source === 'exact_cache' ? '精确缓存' : resp.query_source === 'llm' ? 'LLM 生成' : '-'}</b></span>
          <span>重试：<b>{resp.retries ?? 0}</b> 次</span>
          <span>截断：<b>{resp.truncated ? '是' : resp.truncated === undefined ? '-' : '否'}</b></span>
          <span>行数：<b>{resp.row_count ?? resp.rows?.length ?? 0}</b></span>
          <span>耗时：<b>{meta?.elapsed_s ?? '-'}</b> s</span>
          <span>Token：<b>{meta?.tokens ?? '-'}</b></span>
          <span>模型：<b>{modelLabel}</b></span>
        </div>
        {resp.query && (
          <details className="dev-details">
            <summary>查询模板（守卫校验后）</summary>
            <pre className="dev-pre">{dump(resp.query)}</pre>
          </details>
        )}
        <details className="dev-details">
          <summary>LLM 原始产出（verify 前）</summary>
          {resp.query_raw
            ? <pre className="dev-pre">{dump(resp.query_raw)}</pre>
            : <BlkEmpty text={resp.query_source === 'exact_cache' ? '精确缓存命中，未经过 LLM 生成' : '无记录'} />}
        </details>
      </Module>

      {/* ③ 数据发现 */}
      <Module num={2} title="数据发现">
        {!!(resp.findings ?? []).length ? (
          <div className="mod-body">{(resp.findings ?? []).map((f, i) => <div key={i} className="dot-li">{f}</div>)}</div>
        ) : <BlkEmpty text="无数据发现" />}
      </Module>

      {/* ④ 数据表格（总行数取 row_count 更准确） */}
      {(resp.columns?.length || resp.rows?.length) ? (
        <Module num={3} title="数据表格">
          {!!resp.rows?.length ? (
            <>
              <AiDataTable columns={resp.columns ?? []} rows={resp.rows}
                totalCount={resp.row_count ?? resp.stats?.count ?? resp.rows.length} />
              {resp.truncated && <div className="blk-empty" style={{ color: '#D97706' }}>该查询被守卫截断（上限 200 行）</div>}
            </>
          ) : <BlkEmpty text="无表格数据" />}
        </Module>
      ) : null}

      {/* ⑤ 数据统计 */}
      {resp.stats && <Module num={4} title="数据统计"><AiStatsGrid stat={resp.stats} /></Module>}

      {/* ⑥ 数据可视化 */}
      {resp.chart && (
        <Module num={5} title="数据可视化">
          <div className="qa-ai-chart">
            <div className="chart-desc">{resp.chart.title}{resp.chart.unit ? `（单位：${resp.chart.unit}）` : ''}：</div>
            <Suspense fallback={<div className="text-sm text-slate-400 py-2">图表加载中…</div>}>
              <ChartView chart={resp.chart} />
            </Suspense>
          </div>
        </Module>
      )}

      {/* ⑦ 结论 */}
      {!!resp.text && <MarkdownView content={resp.text} />}

      {/* ⑧ 追问建议：仅展示纯文本 chips，不可点击 */}
      {!!resp.follow_ups?.length && (
        <div className="qa-followup">
          {resp.follow_ups.map((f) => <span key={f} className="fu-chip fu-chip-static">{f}</span>)}
        </div>
      )}

      {/* ⑨ 原始日志（完整 aiMeta + 复制） */}
      <details className="dev-details" style={{ marginTop: 12 }}>
        <summary>
          原始日志（完整 aiMeta）
          <button className="dev-copy-btn" onClick={handleCopyRaw}>{copied ? '已复制' : '复制'}</button>
        </summary>
        <pre className="dev-pre">{dump(resp)}</pre>
      </details>
    </div>
  )
}
