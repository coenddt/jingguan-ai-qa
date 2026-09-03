import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import { useConfigStore } from '../../store/useConfigStore'
import { useSnackbar } from '../../hooks/useSnackbar'
import type { AppConfig as AppConfigData } from '../../types'

const CARDS: { key: keyof AppConfigData; title: string; desc: string }[] = [
  { key: 'suggestions', title: '下一步问题建议', desc: 'AI 回复卡片底部展示追问建议' },
  { key: 'tts', title: '文字转语音', desc: '开启后回复页脚可用语音播报' },
  { key: 'stt', title: '语音转文字', desc: '开启后输入栏麦克风可用' },
  { key: 'modelConfig', title: '模型配置', desc: '点击进入模型配置页' },
  { key: 'hotRecommend', title: '常问设置', desc: '同一问题出现次数达到阈值即视为常问' },
]

export default function AppConfig() {
  const { config, fetchMethod, saveMethod } = useConfigStore()
  const [greetingText, setGreetingText] = useState('')
  const [questions, setQuestions] = useState<string[]>([])
  const [newQ, setNewQ] = useState('')
  const [threshold, setThreshold] = useState(3)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('配置加载失败', 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setGreetingText(config.greeting.text)
    setQuestions(config.greeting.questions)
    setThreshold(config.hotRecommend.threshold)
  }, [config])

  const save = async (patch: Partial<AppConfigData>, okMsg = '配置已保存，即时生效') => {
    try {
      await saveMethod(patch)
      showSnackbar(okMsg, 'success')
    } catch {
      showSnackbar('保存失败，请重试', 'error')
    }
  }

  const saveGreeting = () => save({ greeting: { text: greetingText, questions: questions.slice(0, 10) } })

  const addQuestion = () => {
    const q = newQ.trim()
    if (!q || questions.length >= 10) return
    setQuestions([...questions, q])
    setNewQ('')
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader title="应用配置" subtitle="配置全局生效、即时生效（切回即用新值）" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* 对话开场白 */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover">
          <h3 className="font-black text-gray-700 mb-1">对话开场白</h3>
          <p className="text-xs text-gray-400 mb-3">新会话欢迎页展示的开场白与推荐问题（上限 10 条）</p>
          <textarea className="textarea textarea-bordered w-full h-20 text-sm" value={greetingText}
            onChange={(e) => setGreetingText(e.target.value)} placeholder="开场白文案" />
          <div className="mt-3 space-y-2">
            {questions.map((q, i) => (
              <div key={`${q}-${i}`} className="flex items-center gap-2">
                <input className="input input-bordered input-sm flex-1" value={q} readOnly />
                <button className="btn btn-ghost btn-xs btn-square text-error whitespace-nowrap"
                  onClick={() => setQuestions(questions.filter((_, j) => j !== i))}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <input className="input input-bordered input-sm flex-1" placeholder="新增推荐问题"
                value={newQ} onChange={(e) => setNewQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addQuestion()} />
              <button className="btn btn-outline btn-sm whitespace-nowrap gap-1" onClick={addQuestion} disabled={questions.length >= 10}>
                <Plus size={14} /> 添加
              </button>
            </div>
          </div>
          <button className="btn btn-primary btn-sm whitespace-nowrap mt-4" onClick={saveGreeting}>保存开场白</button>
        </div>

        {/* 常问设置 */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover">
          <h3 className="font-black text-gray-700 mb-1">常问设置</h3>
          <p className="text-xs text-gray-400 mb-3">问题频次阈值（次），达到阈值视为常问</p>
          <div className="flex items-center gap-3">
            <input type="number" min={1} className="input input-bordered w-28" value={threshold}
              onChange={(e) => setThreshold(Math.max(1, Number(e.target.value) || 1))} />
            <span className="text-sm text-gray-500">次</span>
            <button className="btn btn-primary btn-sm whitespace-nowrap ml-auto"
              onClick={() => save({ hotRecommend: { ...config.hotRecommend, threshold } })}>保存</button>
          </div>
        </div>

        {/* 开关类卡片 */}
        {CARDS.map((c) => (
          <div key={c.key} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover flex items-center justify-between gap-4">
            <div>
              <h3 className="font-black text-gray-700">{c.title}</h3>
              <p className="text-xs text-gray-400 mt-0.5">{c.desc}</p>
            </div>
            {c.key === 'modelConfig' ? (
              <a href="/config/model" className="btn btn-outline btn-sm whitespace-nowrap">前往配置</a>
            ) : (
              <input type="checkbox" className="toggle toggle-primary"
                checked={config[c.key] as boolean}
                onChange={(e) => save({ [c.key]: e.target.checked } as Partial<AppConfigData>)} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
