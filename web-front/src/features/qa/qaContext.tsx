/** 问数发送统一入口（React Context）：替代原 window 事件总线，
 *  props 深层透传深（Welcome/ChatMessage/AiCard→AiFollowUps），改用单层 Provider 下发，组件内 useAsk 读取 */
/* eslint-disable react-refresh/only-export-components */ // context 模块常 paired Provider+hook，禁用复用性 fast-refresh 报错

import { createContext, useContext } from 'react'

const AskContext = createContext<((q: string) => void) | null>(null)

export const AskProvider = AskContext.Provider

/** 读取问数发送回调；Provider 外使用属编程错误，直接抛错暴露（禁止静默失守） */
export function useAsk() {
  const ask = useContext(AskContext)
  if (!ask) throw new Error('useAsk 必须在 <AskProvider> 内使用')
  return ask
}