/** 开关/入口类配置卡片组（AppConfig 页使用） */

import { useCallback, type ChangeEvent } from 'react'
import { useConfigStore } from '../../../store/useConfigStore'
import type { AppConfig } from '../../../types'
import type { SaveConfigFn } from '../../../hooks/useGreetingForm'

type ToggleKey = 'suggestions' | 'tts' | 'stt' | 'modelConfig'

const CARDS: { key: ToggleKey; title: string; desc: string }[] = [
  { key: 'suggestions', title: '下一步问题建议', desc: 'AI 回复卡片底部展示追问建议' },
  { key: 'tts', title: '文字转语音', desc: '开启后回复页脚可用语音播报' },
  { key: 'stt', title: '语音转文字', desc: '开启后输入栏麦克风可用' },
  { key: 'modelConfig', title: '模型配置', desc: '点击进入模型配置页' },
]

/** 单张配置卡片：开关项或入口链接项 */
function FeatureCard({ card, checked, onChange }: {
  card: { key: ToggleKey; title: string; desc: string }
  checked: boolean
  onChange: (key: ToggleKey, checked: boolean) => void
}) {
  const handleToggle = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    onChange(card.key, e.target.checked)
  }, [card.key, onChange])

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover flex items-center justify-between gap-4">
      <div>
        <h3 className="font-black text-gray-700">{card.title}</h3>
        <p className="text-xs text-gray-400 mt-0.5">{card.desc}</p>
      </div>
      {card.key === 'modelConfig' ? (
        <a href="/config/model" className="btn btn-outline btn-sm whitespace-nowrap">前往配置</a>
      ) : (
        <input type="checkbox" className="toggle toggle-primary" checked={checked} onChange={handleToggle} />
      )}
    </div>
  )
}

export default function FeatureCards({ save }: { save: SaveConfigFn }) {
  const suggestions = useConfigStore((s) => s.config.suggestions)
  const tts = useConfigStore((s) => s.config.tts)
  const stt = useConfigStore((s) => s.config.stt)

  const changeCard = useCallback((key: ToggleKey, checked: boolean) => {
    save({ [key]: checked } as Partial<AppConfig>)
  }, [save])

  const checkedMap: Record<ToggleKey, boolean> = { suggestions, tts, stt, modelConfig: true }

  return (
    <>
      {CARDS.map((c) => (
        <FeatureCard key={c.key} card={c} checked={checkedMap[c.key]} onChange={changeCard} />
      ))}
    </>
  )
}
