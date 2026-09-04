/** 分页查询通用契约（usePagedList / services 分页拉取共用） */
export type PageFilters = Record<string, string>

export interface PagedQuery<F extends PageFilters = PageFilters> {
  /** 0 起始页码 */
  page: number
  pageSize: number
  filters: F
}

export interface Step {
  title: string
  desc: string
  done: boolean
}

export interface Chart {
  type: 'bar' | 'bar_h' | 'pie' | 'line'
  title: string
  unit?: string
  series: number[]
  x: string[]
  legend?: string[]
}

export interface QaStats {
  count: number
  avg: number
  max: number
  max_of: string
  min: number
  min_of: string
}

export interface QaAskResp {
  session_id: string
  steps: Step[]
  findings: string[]
  columns: string[]
  rows: (string | number)[][]
  stats: QaStats
  chart: Chart | null
  text: string
  follow_ups: string[]
  meta: { elapsed_s: number; tokens: number }
}

export interface SessionItem {
  id: string
  title: string
  pinned: boolean
  userName: string
  msgCount: number
  updatedAt: string
}

export interface MsgItem {
  id: string
  role: 'user' | 'ai'
  content: string
  aiMeta?: QaAskResp
  createdAt?: string
}

export interface SourceItem {
  key: string
  name: string
  label?: string
  group: string
  selected: boolean
}

export interface DataSourceGroup {
  group: string
  items: SourceItem[]
}

export interface AppConfig {
  greeting: { text: string; questions: string[] }
  suggestions: boolean
  tts: boolean
  stt: boolean
  modelConfig: boolean
  hotRecommend: { enabled: boolean; threshold: number }
}

export interface ModelItem {
  id: string
  name: string
  baseUrl: string
  apiKey: string
  modelName: string
  enabled: boolean
}

export interface FeedbackItem {
  id: string
  question: string
  answer: string
  userName: string
  description: string
  status: string
  remark: string
  createdAt: string
}

export interface ImportLogItem {
  id: string
  type: string
  year: number
  fileName: string
  totalRows: number
  successRows: number
  status: string
  detail: string
  createdAt: string
}
