import { useEffect, useState } from 'react'
import { Star, X, Zap } from 'lucide-react'
import { qaApi } from '../../api/modules/qa'
import { useSnackbar } from '../../hooks/useSnackbar'
import Modal from '../../components/Modal'
import { readFavorites, writeFavorites } from '../../utils/favorites'

interface Props {
  open: boolean
  onClose: () => void
  onAsk: (q: string) => void
}

export default function QuickAsk({ open, onClose, onAsk }: Props) {
  const [tab, setTab] = useState<'hot' | 'fav'>('hot')
  const [hot, setHot] = useState<{ question: string; hit: number }[]>([])
  const [hotEnabled, setHotEnabled] = useState(true)
  const [favs, setFavs] = useState<string[]>([])
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    if (!open) return
    setFavs(readFavorites())
    qaApi.getQuickAsks()
      .then(({ data }) => {
        setHotEnabled(data.enabled)
        setHot(data.hot)
        if (!data.enabled) setTab('fav')
      })
      .catch(() => showSnackbar('常问数据加载失败', 'error'))
  }, [open, showSnackbar])

  if (!open) return null

  const removeFav = (q: string) => {
    const next = favs.filter((f) => f !== q)
    writeFavorites(next)
    setFavs(next)
  }

  return (
    <Modal open={open} onClose={onClose} boxClassName="max-w-lg" showClose
      title={<h3 className="font-bold text-lg flex items-center gap-1.5"><Zap size={18} className="text-gold-deep" /> 快捷提问</h3>}>
        <div role="tablist" className="tabs tabs-bordered mt-2">
          {hotEnabled && (
            <button role="tab" className={`tab whitespace-nowrap gap-1 ${tab === 'hot' ? 'tab-active' : ''}`}
              onClick={() => setTab('hot')}><Zap size={13} /> 常问</button>
          )}
          <button role="tab" className={`tab whitespace-nowrap gap-1 ${tab === 'fav' ? 'tab-active' : ''}`}
            onClick={() => setTab('fav')}><Star size={13} /> 收藏</button>
        </div>
        <div className="flex flex-wrap gap-2 mt-4 min-h-[80px] content-start">
          {tab === 'hot' && hot.map((h) => (
            <button key={h.question} className="btn btn-outline btn-sm rounded-full whitespace-nowrap text-gray-600"
              onClick={() => { onClose(); onAsk(h.question) }}>
              {h.question}
            </button>
          ))}
          {tab === 'fav' && (favs.length ? favs.map((q) => (
            <div key={q} className="flex items-center bg-gray-50 border border-gray-200 rounded-full pl-1">
              <button className="btn btn-ghost btn-xs rounded-full whitespace-nowrap text-gray-600"
                onClick={() => { onClose(); onAsk(q) }}>{q}</button>
              <button className="btn btn-ghost btn-xs btn-square text-gray-300" onClick={() => removeFav(q)}>
                <X size={12} />
              </button>
            </div>
          )) : <p className="text-sm text-gray-400 py-4">暂无收藏问题，在消息上点 ☆ 收藏</p>)}
        </div>
    </Modal>
  )
}
