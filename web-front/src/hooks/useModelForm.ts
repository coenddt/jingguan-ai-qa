/** 新增模型表单：字段（含平台）+ 连接测试 + 提交（ModelConfig/AddModelModal 使用） */

import { useCallback, useState } from 'react'
import { LLM_PLATFORMS, modelsApi } from '../api/modules/models'
import { useModelStore } from '../store/useModelStore'
import { useSnackbar } from './useSnackbar'

export function useModelForm() {
  const [platform, setPlatformField] = useState<string>(LLM_PLATFORMS[0].value)
  const [baseUrl, setBaseUrlField] = useState('')
  const [apiKey, setApiKeyField] = useState('')
  const [modelName, setModelNameField] = useState('')
  const [testing, setTesting] = useState(false)
  const [testOk, setTestOk] = useState(false)
  const fetchModels = useModelStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()

  const changePlatform = useCallback((v: string) => {
    setPlatformField(v)
    setBaseUrlField('')
    setTestOk(false)
  }, [])
  const changeBaseUrl = useCallback((v: string) => { setBaseUrlField(v); setTestOk(false) }, [])
  const changeApiKey = useCallback((v: string) => { setApiKeyField(v); setTestOk(false) }, [])
  const changeModelName = useCallback((v: string) => { setModelNameField(v); setTestOk(false) }, [])

  const clearForm = useCallback(() => {
    setPlatformField(LLM_PLATFORMS[0].value)
    setBaseUrlField('')
    setApiKeyField('')
    setModelNameField('')
    setTestOk(false)
  }, [])

  const runTest = useCallback(async () => {
    setTesting(true)
    try {
      const { data } = await modelsApi.test({ platform, baseUrl, apiKey, modelName })
      if (data.ok) {
        setTestOk(true)
        showSnackbar(`连接成功（${data.latency_ms ?? 0}ms），可添加`, 'success')
      } else {
        setTestOk(false)
        showSnackbar(`连接失败：${data.error || '未知错误'}`, 'error')
      }
    } catch {
      showSnackbar('测试请求失败', 'error')
    } finally {
      setTesting(false)
    }
  }, [platform, baseUrl, apiKey, modelName, showSnackbar])

  const submitAdd = useCallback(async () => {
    if (!testOk) return
    try {
      await modelsApi.add({ platform, baseUrl, apiKey, modelName })
      showSnackbar('模型已添加', 'success')
      clearForm()
      await fetchModels()
    } catch {
      showSnackbar('添加失败，请重试', 'error')
    }
  }, [platform, baseUrl, apiKey, modelName, testOk, clearForm, fetchModels, showSnackbar])

  const resetAdd = useCallback(() => clearForm(), [clearForm])

  return {
    platform, baseUrl, apiKey, modelName, testing, testOk,
    canTest: Boolean(apiKey && modelName),  // baseUrl 可留空（用平台预设）
    changePlatform, changeBaseUrl, changeApiKey, changeModelName,
    runTest, submitAdd, resetAdd,
  }
}
