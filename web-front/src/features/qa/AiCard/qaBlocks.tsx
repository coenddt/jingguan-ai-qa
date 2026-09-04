/** AI 卡片通用块级组件（AiCard 与 DevLogCard 共用） */

/** 原型 qa-ai-module：编号圆点标题 + 内容 */
export function Module({ num, title, children }: { num: number; title: string; children: React.ReactNode }) {
  return (
    <div className="qa-ai-module">
      <div className="mod-title"><span className="mod-num">{num}</span>{title}</div>
      {children}
    </div>
  )
}

/** 流式中未到达块的占位 */
export function BlkPending() {
  return (
    <div className="blk-pending">
      <i className="fas fa-circle-notch fa-spin" /> 正在生成…
    </div>
  )
}

/** 空态占位 */
export function BlkEmpty({ text = '无数据' }: { text?: string }) {
  return <div className="blk-empty">{text}</div>
}
