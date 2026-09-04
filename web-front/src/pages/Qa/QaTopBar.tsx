/** 问数主区顶栏（原型 qa-right-hdr）：侧栏开关 + 会话标题 + 数据源指示 + 日志入口 */

interface Props {
  title: string
  listOpen: boolean
  onOpenList: () => void
  sourceLabel: string
  onOpenSources: () => void
  onSwitchView: (v: 'chat' | 'log') => void
}

export default function QaTopBar({ title, listOpen, onOpenList, sourceLabel, onOpenSources, onSwitchView }: Props) {
  return (
    <div className="qa-right-hdr">
      <div className="qa-rh-left">
        {!listOpen && (
          <button className="qa-rh-btn" title="侧边栏" onClick={onOpenList}>
            <i className="fas fa-outdent" />
          </button>
        )}
      </div>
      <div className="qa-rh-center">{title}</div>
      <div className="qa-rh-right">
        <button className="rh-btn" title="选择问数数据源" onClick={onOpenSources}>
          <i className="fas fa-paperclip" /> <span>{sourceLabel}</span>
        </button>
        <button className="rh-btn" title="查看问数日志" onClick={() => onSwitchView('log')}>
          <i className="fas fa-clock" /> 日志
        </button>
      </div>
    </div>
  )
}
