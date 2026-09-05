/** 卡片页脚（原型 qa-ai-footer）：复制/反馈/语音播放 图标按钮 + 耗时元信息 */

import { useState } from 'react'
import { useConfigStore } from '../../../store/useConfigStore'
import type { QaAskResp } from '../../../types'
import TtsButton from '../TtsButton'

interface Props {
  resp: QaAskResp
  copied: boolean
  onCopy: () => void
  onFeedback: () => void
  /** 消息落库时间（历史消息恢复时有值）；流式消息缺省时以页脚挂载（即回答完成）时刻锁定 */
  createdAt?: string
}

const fmtTime = (t: string) => new Date(t).toLocaleTimeString('zh-CN', { hour12: false })

export default function AiCardFooter({ resp, copied, onCopy, onFeedback, createdAt }: Props) {
  const ttsEnabled = useConfigStore((s) => s.config.tts)
  const [doneTs] = useState(() => new Date().toLocaleTimeString('zh-CN', { hour12: false }))
  const ts = createdAt ? fmtTime(createdAt) : doneTs
  return (
    <div className="qa-ai-footer">
      <div className="qa-ai-actions">
        <button data-title="复制" aria-label="复制答案" className={copied ? 'saved' : ''} onClick={onCopy}>
          <i className={copied ? 'fas fa-check' : 'fas fa-copy'} />
        </button>
        <button data-title="反馈" aria-label="反馈答案" onClick={onFeedback}>
          <i className="fas fa-frown" />
        </button>
        {ttsEnabled && <TtsButton text={resp.text} />}
      </div>
      <div className="qa-ai-stats">耗时{resp.meta.elapsed_s}s&nbsp;&nbsp;Token:{resp.meta.tokens}&nbsp;&nbsp;{ts}</div>
    </div>
  )
}
