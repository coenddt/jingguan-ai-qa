/** 问数域纯业务函数（AiCard 使用） */

import type { QaAskResp } from '../types'

/** 拼接 AI 卡片复制文本：结论 + 逐列数据 */
export function buildAiCardCopyText(resp: QaAskResp): string {
  const lines = [resp.text, ...resp.columns.map((c, i) => `${c}: ${resp.rows.map((r) => r[i]).join('、')}`)]
  return lines.join('\n')
}
