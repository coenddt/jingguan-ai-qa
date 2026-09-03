import { create } from 'zustand'
import { configApi } from '../api/modules/config'
import type { AppConfig } from '../types'

const DEFAULT_CONFIG: AppConfig = {
  greeting: { text: '', questions: [] },
  suggestions: true,
  tts: false,
  stt: false,
  modelConfig: true,
  hotRecommend: { enabled: true, threshold: 3 },
}

interface ConfigStore {
  config: AppConfig
  loaded: boolean
  fetchMethod: () => Promise<void>
  saveMethod: (patch: Partial<AppConfig>) => Promise<void>
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: DEFAULT_CONFIG,
  loaded: false,
  fetchMethod: async () => {
    if (get().loaded) return
    const { data } = await configApi.get()
    set({ config: { ...DEFAULT_CONFIG, ...data }, loaded: true })
  },
  saveMethod: async (patch) => {
    const { data } = await configApi.put(patch)
    set({ config: { ...DEFAULT_CONFIG, ...data }, loaded: true })
  },
}))
