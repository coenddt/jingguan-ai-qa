/** 消息编辑态（原型 qa-edit-bar）：取消 / 重新发送 */

import { useCallback, useState, type ChangeEvent } from 'react'

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
    <div className="qa-user-msg">
      <div className="qa-user-bubble" style={{ padding: 0 }}>
        <textarea autoFocus value={draft} onChange={changeDraft}
          style={{
            width: '100%', border: 'none', background: 'transparent', resize: 'none', outline: 'none',
            fontSize: 16, color: '#1E1B4B', lineHeight: 1.5, fontFamily: 'inherit',
            minHeight: 40, display: 'block', padding: '12px 16px', boxSizing: 'border-box',
          }} />
      </div>
      <div className="qa-edit-bar">
        <button className="btn btn-light btn-sm whitespace-nowrap" onClick={onCancel}>
          <i className="fas fa-times" /> 取消
        </button>
        <button className="btn btn-primary btn-sm whitespace-nowrap" disabled={!draft.trim()} onClick={send}>
          <i className="fas fa-paper-plane" /> 重新发送
        </button>
      </div>
    </div>
  )
}
