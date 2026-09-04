/** 问数域纯业务函数（AiCard / useQaChat 共用） */

import type { QaAskResp } from '../types'

const QA_ASK_EVENT = 'qa:ask'

/** 通过全局事件触发一次问数（AiCard 追问 chips 等深层组件免 props 透传） */
export function dispatchQaAsk(question: string): void {
  window.dispatchEvent(new CustomEvent<string>(QA_ASK_EVENT, { detail: question }))
}

/** 订阅全局问数事件，返回取消订阅函数 */
export function onQaAsk(handler: (question: string) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<string>).detail)
  window.addEventListener(QA_ASK_EVENT, listener)
  return () => window.removeEventListener(QA_ASK_EVENT, listener)
}

/** 拼接 AI 卡片复制文本：结论 + 逐列数据 */
export function buildAiCardCopyText(resp: QaAskResp): string {
  const lines = [resp.text, ...resp.columns.map((c, i) => `${c}: ${resp.rows.map((r) => r[i]).join('、')}`)]
  return lines.join('\n')
}
