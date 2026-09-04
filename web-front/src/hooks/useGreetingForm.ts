/** 开场白表单：文案 + 推荐问题列表编辑（AppConfig/GreetingCard 使用） */

import { useCallback, useEffect, useState } from 'react'
import { useConfigStore } from '../store/useConfigStore'
import type { AppConfig } from '../types'

export type SaveConfigFn = (patch: Partial<AppConfig>, okMsg?: string) => void

const MAX_QUESTIONS = 10

export function useGreetingForm(save: SaveConfigFn) {
  const greeting = useConfigStore((s) => s.config.greeting)
  const [greetingText, setGreetingText] = useState('')
  const [questions, setQuestions] = useState<string[]>([])
  const [newQ, setNewQ] = useState('')

  // 配置加载后回填表单
  useEffect(() => {
    setGreetingText(greeting.text)
    setQuestions(greeting.questions)
  }, [greeting])

  const changeGreetingText = useCallback((v: string) => setGreetingText(v), [])
  const changeNewQ = useCallback((v: string) => setNewQ(v), [])

  const addQuestion = useCallback(() => {
    const q = newQ.trim()
    if (!q || questions.length >= MAX_QUESTIONS) return
    setQuestions((prev) => [...prev, q])
    setNewQ('')
  }, [newQ, questions.length])

  const removeQuestion = useCallback((index: number) => {
    setQuestions((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const saveGreeting = useCallback(() => {
    save({ greeting: { text: greetingText, questions: questions.slice(0, MAX_QUESTIONS) } })
  }, [greetingText, questions, save])

  return {
    greetingText, changeGreetingText,
    questions, newQ, changeNewQ, addQuestion, removeQuestion,
    canAddQuestion: questions.length < MAX_QUESTIONS,
    saveGreeting,
  }
}
