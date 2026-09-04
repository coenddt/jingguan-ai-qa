/** 收藏问题列表（jg_favorites）单源读写，ChatMessage / QuickAsk 共用 */

import { readJsonLS, writeJsonLS } from './localStorage'

const FAVORITES_KEY = 'jg_favorites'

export function readFavorites(): string[] {
  return readJsonLS<string[]>(FAVORITES_KEY, [])
}

export function writeFavorites(favs: string[]): void {
  writeJsonLS(FAVORITES_KEY, favs)
}
