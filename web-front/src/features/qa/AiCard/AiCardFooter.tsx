/** 卡片页脚：复制/反馈/语音播报/耗时元信息 */

import { Check, Copy, ThumbsDown } from 'lucide-react'
import type { QaAskResp } from '../../../types'
import TtsButton from '../TtsButton'
import { formatDateTime } from '../../../utils/date'

interface Props {
  resp: QaAskResp
  copied: boolean
  onCopy: () => void
  onFeedback: () => void
}

export default function AiCardFooter({ resp, copied, onCopy, onFeedback }: Props) {
  return (
    <div className="flex items-center gap-1 pt-1 border-t border-gray-100 text-gray-500">
      <button className="btn btn-ghost btn-xs gap-1 whitespace-nowrap" onClick={onCopy}>
        {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />} 复制
      </button>
      <button className="btn btn-ghost btn-xs gap-1 whitespace-nowrap" onClick={onFeedback}>
        <ThumbsDown size={13} /> 反馈
      </button>
      <TtsButton text={resp.text} />
      <span className="ml-auto text-[11px] text-gray-400">
        耗时 {resp.meta.elapsed_s}s · Tokens {resp.meta.tokens} · {formatDateTime(Date.now())}
      </span>
    </div>
  )
}
