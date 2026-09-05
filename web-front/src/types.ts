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
  /** 流式加载态：true=该步执行中 */
  running?: boolean
  /** 步完成/失败时间戳（unix 毫秒，日志详情排查用） */
  ts?: number
  /** 自上一步以来的耗时（毫秒，日志详情排查用） */
  elapsed?: number
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

export interface QaAskMeta {
  elapsed_s: number
  tokens: number
  /** AiModel.name（展示名），日志详情排查用 */
  model?: string
  /** AiModel.modelName（API 模型标识） */
  modelName?: string
  /** AiModel.platform（deepseek / volcengine 等） */
  platform?: string
}

/** 守卫校验后的完整查询模板（日志详情排查用） */
export interface QaQueryTemplate {
  model: string
  mode: 'query' | 'aggregate'
  condition: Record<string, unknown>
  fields: string[]
  sort?: Record<string, number>
  limit: number
  groupBy?: string[]
  measures?: { op: string; field: string }[]
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
  /** 完整校验后查询模板（新字段，历史数据缺失） */
  query?: QaQueryTemplate
  /** LLM 原始产出（verify 前，含重试最终版）；精确缓存命中为 null */
  query_raw?: Record<string, unknown> | null
  /** 查询来源：精确缓存命中 | LLM 生成 */
  query_source?: 'exact_cache' | 'llm'
  /** LLM 重试轮数 */
  retries?: number
  /** 是否被守卫截断（超 MAX_LIMIT=200） */
  truncated?: boolean
  /** 实际执行返回行数 */
  row_count?: number
  /** 问数失败时的错误详情（含步骤/耗时），成功时无此字段 */
  error?: string
  /** 条件不足澄清：string=纯文本（老会话/软门回退）；ClarifyForm=结构化澄清表单 */
  clarify?: string | ClarifyForm
  meta: QaAskMeta
}

/** 澄清表单字段：key 为查询条件 topic 键，type 决定控件形态 */
export interface ClarifyField {
  key: string
  label: string
  type: 'radio' | 'checkbox' | 'select' | 'input'
  required?: boolean
  options?: string[]
  placeholder?: string
}

/** 条件不足澄清表单：用户补全参数后由前端拼成完整问题重问 */
export interface ClarifyForm {
  text: string
  question: string
  fields: ClarifyField[]
}

export interface SessionItem {
  id: string
  title: string
  pinned: boolean
  userName: string
  msgCount: number
  userFeedback: string
  adminFeedback: string
  updatedAt: string
  createdAt: string
}

export interface MsgItem {
  id: string
  role: 'user' | 'ai'
  content: string
  /** 流式过程中为 Partial（逐块填充），done 事件后为完整 QaAskResp */
  aiMeta?: Partial<QaAskResp>
  /** 流式加载中（true 时卡片按块占位渲染） */
  streaming?: boolean
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
  greeting: { enabled: boolean; text: string; questions: string[] }
  suggestions: boolean
  tts: boolean
  stt: boolean
  modelConfig: boolean
  hotRecommend: { enabled: boolean; threshold: number }
}

export interface ModelItem {
  id: string
  name: string
  platform: string
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
