import { modelsApi } from '../api/modules/models'
import type { ModelItem } from '../types'
import { createListStore } from './createListStore'

export const useModelStore = createListStore<ModelItem>(async () => {
  const { data } = await modelsApi.list()
  return data
})
