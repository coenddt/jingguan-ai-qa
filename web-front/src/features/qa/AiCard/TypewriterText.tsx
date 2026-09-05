/** 结论逐字打字机：requestAnimationFrame 恒定速率匀速推进（与网络/LLM 到达速度无关，保证平稳），
 *  markdown 源串截断交 MarkdownView 重渲染，放完即完整内容 */

import { useEffect, useState } from 'react'
import MarkdownView from '../../../components/MarkdownView'

export default function TypewriterText({ content }: { content: string }) {
  const [n, setN] = useState(0)
  const finished = n >= content.length

  useEffect(() => {
    if (!content) return
    // 无障碍：用户偏好减弱动画时直接展示完整内容，不做逐字打字
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches) {
      setN(content.length)
      return
    }
    let n = 0
    let acc = 0
    let raf = 0
    // 总时长自适应：短文本快、长文本慢，整体限制在 0.7s~3.5s，速率恒定
    const total = Math.min(3500, Math.max(700, content.length * 24))
    let last = performance.now()
    const tick = (now: number) => {
      acc += (content.length / total) * (now - last)
      last = now
      if (acc >= 1) {
        const step = Math.floor(acc)
        acc -= step
        n = Math.min(content.length, n + step)
        setN(n)
      }
      if (n < content.length) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [content])

  return (
    <div className={`tw-wrap ${finished ? 'tw-done' : ''}`}>
      <MarkdownView content={content.slice(0, n)} />
    </div>
  )
}
