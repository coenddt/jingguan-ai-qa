/** 快捷提问面板（原型 qq-panel 1:1，锚定输入栏上方）：常问 / 收藏（发送走 AskContext） */

import { useCallback, useEffect, useState } from 'react'
import { qaApi } from '../../api/modules/qa'
import { useSnackbar } from '../../hooks/useSnackbar'
import { readFavorites, writeFavorites } from '../../services/favorites'
import { useAsk } from './qaContext'

interface Props {
  onClose: () => void
}

type Tab = 'hot' | 'fav'

export default function QuickAsk({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('hot')
  const [hot, setHot] = useState<{ question: string; hit: number }[]>([])
  const [hotEnabled, setHotEnabled] = useState(true)
  const [favs, setFavs] = useState<string[]>([])
  const { showSnackbar } = useSnackbar()
  const ask = useAsk()

  useEffect(() => {
    setTab('hot')
    setFavs(readFavorites())
    qaApi.getQuickAsks()
      .then(({ data }) => {
        setHotEnabled(data.enabled)
        setHot(data.hot)
        if (!data.enabled) setTab('fav')
      })
      .catch(() => showSnackbar('常问数据加载失败', 'error'))
  }, [showSnackbar])

  // 点击面板外部关闭
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement
      if (!t.closest('.qq-panel') && !t.closest('.qq-btn')) onClose()
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [onClose])

  const pick = useCallback((q: string) => {
    ask(q)
    onClose()
  }, [ask, onClose])

  const removeFav = useCallback((q: string) => {
    const next = favs.filter((f) => f !== q)
    writeFavorites(next)
    setFavs(next)
    showSnackbar('已取消收藏', 'success')
  }, [favs, showSnackbar])

  const list = tab === 'hot' ? hot.map((h) => h.question) : favs

  return (
    <div className="qq-panel show">
      <div className="qq-phdr">
        <h4><i className="fas fa-bolt" style={{ color: '#2563EB', marginRight: 4 }} />快捷提问</h4>
        <button className="qq-close" aria-label="关闭快捷提问" onClick={onClose}><i className="fas fa-times" /></button>
      </div>
      <div className="qq-tabs">
        {hotEnabled && (
          <button className={`qq-tab ${tab === 'hot' ? 'active' : ''}`} onClick={() => setTab('hot')}>常问</button>
        )}
        <button className={`qq-tab ${tab === 'fav' ? 'active' : ''}`} onClick={() => setTab('fav')}>收藏</button>
      </div>
      <div className="qq-list">
        {list.length === 0 && (
          <div className="qq-item" style={{ cursor: 'default', color: '#9CA3AF' }}>
            {tab === 'fav' ? '暂无收藏问题，在消息上点 ☆ 收藏' : '暂无常问问题'}
          </div>
        )}
        {list.map((q) => (
          <div key={q} className="qq-item" onClick={() => pick(q)}>
            <span>{q}</span>
            {tab === 'fav' && (
              <button className="qq-unfav" title="取消收藏" aria-label="取消收藏" onClick={(e) => { e.stopPropagation(); removeFav(q) }}>
                <i className="fas fa-times" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
