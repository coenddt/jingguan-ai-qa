import { Sparkles } from 'lucide-react'
import { useConfigStore } from '../../store/useConfigStore'

export default function Welcome({ onAsk }: { onAsk: (q: string) => void }) {
  const { config } = useConfigStore()
  const greeting = config.greeting
  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      <div className="w-12 h-12 rounded-2xl gold-gradient flex items-center justify-center text-[#0f172a] mb-4">
        <Sparkles size={26} strokeWidth={1.5} />
      </div>
      <h1 className="text-3xl font-black text-gray-800 tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>
        你好<span className="text-gold-deep">，</span>我是经管之星·AI问数助手
      </h1>
      {greeting.text && <p className="text-gray-500 mt-3 text-center max-w-lg">{greeting.text}</p>}
      {!!greeting.questions.length && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 w-full max-w-xl">
          {greeting.questions.slice(0, 10).map((q) => (
            <button key={q}
              className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 text-left text-sm text-gray-600 hover:border-gold hover:shadow-md card-hover whitespace-nowrap"
              onClick={() => onAsk(q)}>
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
