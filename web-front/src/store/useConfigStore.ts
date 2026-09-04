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
  loading: boolean
  fetchMethod: () => Promise<void>
  saveMethod: (patch: Partial<AppConfig>) => Promise<void>
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: DEFAULT_CONFIG,
  loaded: false,
  loading: false,
  fetchMethod: async () => {
    if (get().loading || get().loaded) return
    set({ loading: true })
    try {
      const { data } = await configApi.get()
      set({ config: { ...DEFAULT_CONFIG, ...data }, loaded: true })
    } finally {
      set({ loading: false })
    }
  },
  saveMethod: async (patch) => {
    const { data } = await configApi.put(patch)
    set({ config: { ...DEFAULT_CONFIG, ...data }, loaded: true })
  },
}))
