/** 新会话欢迎页（原型 qa-welcome 1:1）：你好 / 我是经管之星·AI问数助手 / 开场白 / 你可以这么问我 */

import { useConfigStore } from '../../store/useConfigStore'

export default function Welcome({ onAsk }: { onAsk: (q: string) => void }) {
  const greeting = useConfigStore((s) => s.config.greeting)

  // 原型 qa-quick-row：每行最多两个按钮
  const rows: string[][] = []
  greeting.questions.forEach((q, i) => {
    if (i % 2 === 0) rows.push([q])
    else rows[rows.length - 1].push(q)
  })

  return (
    <div className="qa-welcome">
      <div className="qa-welcome-inner">
        <h1>你好</h1>
        <h2>我是经管之星·AI问数助手</h2>
        {/* 原型 renderGreeting：关闭开场白时隐藏引导语与快捷提问区 */}
        {greeting.enabled !== false && (
          <>
            <p className="qa-desc">{greeting.text || '欢迎使用智能AI问数，您可以向我咨询经营数据、报表分析相关问题。'}</p>
            {!!greeting.questions.length && (
              <div className="qa-quick-section">
                <div className="qa-quick-title">你可以这么问我</div>
                <div className="qa-quick-grid">
                  {rows.map((row, i) => (
                    <div key={i} className="qa-quick-row">
                      {row.map((q) => (
                        <div key={q} className="qa-quick-btn" onClick={() => onAsk(q)}>{q}</div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
