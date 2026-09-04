/** 消息编辑态气泡（ChatMessage 编辑模式渲染） */

import { useCallback, useState, type ChangeEvent } from 'react'
import { X } from 'lucide-react'

interface Props {
  content: string
  onCancel: () => void
  onSend: (draft: string) => void
}

export default function ChatEditBox({ content, onCancel, onSend }: Props) {
  const [draft, setDraft] = useState(content)

  const changeDraft = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value), [])

  const send = useCallback(() => {
    if (draft.trim()) onSend(draft.trim())
  }, [draft, onSend])

  return (
    <div className="flex justify-end">
      <div className="bg-white border border-gray-200 rounded-2xl p-3 max-w-[70%] space-y-2">
        <textarea className="textarea textarea-bordered w-full h-24 text-sm" value={draft}
          onChange={changeDraft} autoFocus />
        <div className="flex gap-2 justify-end">
          <button className="btn btn-ghost btn-xs whitespace-nowrap" onClick={onCancel}>
            <X size={13} /> 取消
          </button>
          <button className="btn btn-primary btn-xs whitespace-nowrap" disabled={!draft.trim()} onClick={send}>
            重新发送
          </button>
        </div>
      </div>
    </div>
  )
}
