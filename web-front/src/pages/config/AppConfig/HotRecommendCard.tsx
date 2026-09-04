/** 常问设置卡片：问题频次阈值（AppConfig 页使用） */

import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { useConfigStore } from '../../../store/useConfigStore'
import type { SaveConfigFn } from '../../../hooks/useGreetingForm'

export default function HotRecommendCard({ save }: { save: SaveConfigFn }) {
  const hotRecommend = useConfigStore((s) => s.config.hotRecommend)
  const [threshold, setThreshold] = useState(hotRecommend.threshold)

  useEffect(() => {
    setThreshold(hotRecommend.threshold)
  }, [hotRecommend])

  const changeThreshold = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setThreshold(Math.max(1, Number(e.target.value) || 1))
  }, [])

  const saveThreshold = useCallback(() => {
    save({ hotRecommend: { ...hotRecommend, threshold } })
  }, [hotRecommend, threshold, save])

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 card-hover">
      <h3 className="font-black text-gray-700 mb-1">常问设置</h3>
      <p className="text-xs text-gray-400 mb-3">问题频次阈值（次），达到阈值视为常问</p>
      <div className="flex items-center gap-3">
        <input type="number" min={1} className="input input-bordered w-28" value={threshold}
          onChange={changeThreshold} />
        <span className="text-sm text-gray-500">次</span>
        <button className="btn btn-primary btn-sm whitespace-nowrap ml-auto" onClick={saveThreshold}>保存</button>
      </div>
    </div>
  )
}
