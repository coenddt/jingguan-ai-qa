import { create } from 'zustand'
import { modelsApi } from '../api/modules/models'
import type { ModelItem } from '../types'

interface ModelStore {
  models: ModelItem[]
  loaded: boolean
  loading: boolean
  fetchMethod: () => Promise<void>
}

export const useModelStore = create<ModelStore>((set, get) => ({
  models: [],
  loaded: false,
  loading: false,
  fetchMethod: async () => {
    if (get().loading) return
    set({ loading: true })
    try {
      const { data } = await modelsApi.list()
      set({ models: data, loaded: true })
    } finally {
      set({ loading: false })
    }
  },
}))
