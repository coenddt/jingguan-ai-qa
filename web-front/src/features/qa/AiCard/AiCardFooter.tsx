/** 卡片页脚（原型 qa-ai-footer）：复制/反馈/语音播放 图标按钮 + 耗时元信息 */

import { useConfigStore } from '../../../store/useConfigStore'
import type { QaAskResp } from '../../../types'
import TtsButton from '../TtsButton'

interface Props {
  resp: QaAskResp
  copied: boolean
  onCopy: () => void
  onFeedback: () => void
}

export default function AiCardFooter({ resp, copied, onCopy, onFeedback }: Props) {
  const ttsEnabled = useConfigStore((s) => s.config.tts)
  const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  return (
    <div className="qa-ai-footer">
      <div className="qa-ai-actions">
        <button data-title="复制" className={copied ? 'saved' : ''} onClick={onCopy}>
          <i className={copied ? 'fas fa-check' : 'fas fa-copy'} />
        </button>
        <button data-title="反馈" onClick={onFeedback}>
          <i className="fas fa-frown" />
        </button>
        {ttsEnabled && <TtsButton text={resp.text} />}
      </div>
      <div className="qa-ai-stats">耗时{resp.meta.elapsed_s}s&nbsp;&nbsp;Token:{resp.meta.tokens}&nbsp;&nbsp;{ts}</div>
    </div>
  )
}
