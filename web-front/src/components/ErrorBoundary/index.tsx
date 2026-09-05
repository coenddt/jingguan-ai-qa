/** 全局错误边界：子树渲染异常时兜底，避免整页白屏；记录错误以便排查 */
import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** 兜底文案（默认通用提示） */
  fallbackText?: string
  /** 该值变化时重置错误态（如路由切换），避免用户被"困"在错误页 */
  resetKey?: unknown
}

interface State {
  hasError: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    // 渲染异常触发：置为失败态，走兜底 UI
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    // 上报/记录，供排查
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  componentDidUpdate(prevProps: Props) {
    // resetKey 变化（如跳转别的页面）自动复位，正常渲染
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false })
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-[#f8fafc]">
          <div className="text-center">
            <p className="text-lg font-semibold text-slate-700">页面出错了</p>
            <p className="mt-1 text-sm text-slate-500">
              {this.props.fallbackText ?? '请刷新页面重试，若问题持续请联系管理员'}
            </p>
            <button
              type="button"
              className="btn btn-primary mt-4"
              onClick={() => window.location.reload()}
            >
              刷新页面
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}