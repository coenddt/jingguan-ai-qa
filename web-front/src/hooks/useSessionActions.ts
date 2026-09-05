/** 会话操作流：置顶/重命名/删除（SessionList 使用；悬停菜单开合状态由 SessionList 自持） */

import { useCallback, useState } from 'react'
import type { SessionItem } from '../types'
import { qaApi } from '../api/modules/qa'
import { useSessionStore } from '../store/useSessionStore'
import { useSnackbar } from './useSnackbar'

export function useSessionActions(activeId: string | null, onActiveDeleted?: (id: string) => void) {
  const [renameFor, setRenameFor] = useState<SessionItem | null>(null)
  const [renameText, setRenameText] = useState('')
  const [delFor, setDelFor] = useState<SessionItem | null>(null)
  const [delLoading, setDelLoading] = useState(false)
  const fetchSessions = useSessionStore((s) => s.fetchMethod)
  const { showSnackbar } = useSnackbar()

  const togglePin = useCallback(async (s: SessionItem) => {
    try {
      await qaApi.patchSession(s.id, { pinned: !s.pinned })
      await fetchSessions()
    } catch {
      showSnackbar('置顶操作失败，请重试', 'error')
    }
  }, [fetchSessions, showSnackbar])

  const openRename = useCallback((s: SessionItem) => {
    setRenameFor(s)
    setRenameText(s.title)
  }, [])
  const closeRename = useCallback(() => setRenameFor(null), [])
  const changeRenameText = useCallback((v: string) => setRenameText(v), [])

  const submitRename = useCallback(async () => {
    if (!renameFor || !renameText.trim()) return
    try {
      await qaApi.patchSession(renameFor.id, { title: renameText.trim() })
      setRenameFor(null)
      await fetchSessions()
    } catch {
      showSnackbar('重命名失败，请重试', 'error')
    }
  }, [renameFor, renameText, fetchSessions, showSnackbar])

  const openDelete = useCallback((s: SessionItem) => setDelFor(s), [])
  const closeDelete = useCallback(() => setDelFor(null), [])

  const submitDelete = useCallback(async () => {
    if (!delFor) return
    setDelLoading(true)
    try {
      await qaApi.deleteSession(delFor.id)
      showSnackbar('会话已删除', 'success')
      setDelFor(null)
      await fetchSessions()
      if (activeId === delFor.id) onActiveDeleted?.(delFor.id)
    } catch {
      showSnackbar('删除失败，请重试', 'error')
    } finally {
      setDelLoading(false)
    }
  }, [delFor, activeId, fetchSessions, showSnackbar, onActiveDeleted])

  return {
    renameFor, openRename, closeRename, renameText, changeRenameText, submitRename,
    delFor, openDelete, closeDelete, delLoading, submitDelete,
    togglePin,
  }
}
