/** ⑦ 追问建议 chips（点击经全局事件触发问数） */

import { dispatchQaAsk } from '../../../services/qa'

export default function AiFollowUps({ followUps }: { followUps: string[] }) {
  if (!followUps.length) return null
  return (
    <div className="flex flex-wrap gap-2">
      {followUps.map((f) => (
        <button key={f} className="btn btn-outline btn-xs rounded-full whitespace-nowrap text-gray-600"
          onClick={() => dispatchQaAsk(f)}>
          {f}
        </button>
      ))}
    </div>
  )
}
