/** 回复校对域纯业务函数（Feedback 页分页拉取） */

import { feedbackApi } from '../api/modules/feedback'
import type { FeedbackItem, PagedQuery } from '../types'

export async function fetchFeedbackPage({ page, pageSize, filters }: PagedQuery): Promise<{ items: FeedbackItem[]; total: number }> {
  const { data } = await feedbackApi.list({
    page: page + 1, pageSize,
    search: filters.search || undefined,
    userSearch: filters.userSearch || undefined,
    status: filters.status || undefined,
  })
  return data
}
