/** 对话开场白配置卡片（AppConfig 页使用） */

import { Plus, Trash2 } from 'lucide-react'
import { useGreetingForm, type SaveConfigFn } from '../../../hooks/useGreetingForm'

export default function GreetingCard({ save }: { save: SaveConfigFn }) {
  const {
    greetingText, changeGreetingText,
    questions, newQ, changeNewQ, addQuestion, removeQuestion, canAddQuestion, saveGreeting,
  } = useGreetingForm(save)

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover">
      <h3 className="font-black text-gray-700 mb-1">对话开场白</h3>
      <p className="text-xs text-gray-400 mb-3">新会话欢迎页展示的开场白与推荐问题（上限 10 条）</p>
      <textarea className="textarea textarea-bordered w-full h-20 text-sm" value={greetingText}
        onChange={(e) => changeGreetingText(e.target.value)} placeholder="开场白文案" />
      <div className="mt-3 space-y-2">
        {questions.map((q, i) => (
          <div key={`${q}-${i}`} className="flex items-center gap-2">
            <input className="input input-bordered input-sm flex-1" value={q} readOnly />
            <button className="btn btn-ghost btn-xs btn-square text-error whitespace-nowrap"
              onClick={() => removeQuestion(i)}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <input className="input input-bordered input-sm flex-1" placeholder="新增推荐问题"
            value={newQ} onChange={(e) => changeNewQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addQuestion()} />
          <button className="btn btn-outline btn-sm whitespace-nowrap gap-1" onClick={addQuestion} disabled={!canAddQuestion}>
            <Plus size={14} /> 添加
          </button>
        </div>
      </div>
      <button className="btn btn-primary btn-sm whitespace-nowrap mt-4" onClick={saveGreeting}>保存开场白</button>
    </div>
  )
}
