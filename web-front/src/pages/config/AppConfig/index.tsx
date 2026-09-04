/** 应用配置页：开场白 / 常问设置 / 开关类卡片 */

import { useCallback, useEffect } from 'react'
import PageHeader from '../../../components/PageHeader'
import { useConfigStore } from '../../../store/useConfigStore'
import { useSnackbar } from '../../../hooks/useSnackbar'
import type { AppConfig as AppConfigData } from '../../../types'
import type { SaveConfigFn } from '../../../hooks/useGreetingForm'
import GreetingCard from './GreetingCard'
import HotRecommendCard from './HotRecommendCard'
import FeatureCards from './FeatureCards'

export default function AppConfig() {
  const fetchMethod = useConfigStore((s) => s.fetchMethod)
  const saveMethod = useConfigStore((s) => s.saveMethod)
  const { showSnackbar } = useSnackbar()

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('配置加载失败', 'error'))
  }, [fetchMethod, showSnackbar])

  const save: SaveConfigFn = useCallback((patch, okMsg = '配置已保存，即时生效') => {
    saveMethod(patch)
      .then(() => showSnackbar(okMsg, 'success'))
      .catch(() => showSnackbar('保存失败，请重试', 'error'))
  }, [saveMethod, showSnackbar])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader title="应用配置" subtitle="配置全局生效、即时生效（切回即用新值）" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <GreetingCard save={save} />
        <HotRecommendCard save={save} />
        <FeatureCards save={save} />
      </div>
    </div>
  )
}
