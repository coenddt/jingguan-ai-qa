/**
 * QA 关键路径 E2E：登录 → 进入 /qa → 发送问题 → SSE 流式渲染（步骤/结论/表格/追问）。
 * 全量 route mock /api（不含真实凭据，hermetic、CI 稳定）；SSE 由 /api/qa/ask 返回。
 */
import { test, expect } from '@playwright/test'

/** 构造一段 SSE 帧序列（type: block/done 覆盖结论、表格、追问）。字段形状必须与 QaAskResp 契约一致：
 *  findings 为 string[]、stats 为 QaStats 对象、table 用 columns+rows，done 事件携带完整响应 + meta */
function sseBody(): string {
  const steps = ['意图识别', '选模型', '生成查询', '执行取数', '交付结论'].map((title) => ({ title }))
  const frame = (o: unknown): string => `data: ${JSON.stringify(o)}\n\n`
  const full: Record<string, unknown> = {
    session_id: 's1',
    steps: steps.map((t) => ({ ...t, desc: '完成', done: true })),
    findings: ['A线利润率最高，达15%', 'B线12%，环比略降', 'C线9%，有待提升'],
    columns: ['产品线', '利润率'],
    rows: [['A线', 15], ['B线', 12], ['C线', 9]],
    stats: { count: 3, avg: 12, max: 15, max_of: 'A线', min: 9, min_of: 'C线' },
    chart: null,
    text: '2026年各产品线利润率整体平稳，A线利润率最高。',
    follow_ups: ['B线为什么下降？', 'C线如何提升？'],
    meta: { elapsed_s: 1.2, tokens: 300, model: 'deepseek-chat', modelName: 'deepseek-chat', platform: 'deepseek' },
  }
  let s = ''
  s += frame({ type: 'session', data: { session_id: 's1' } })
  s += frame({ type: 'steps', data: steps })
  for (let i = 0; i < steps.length; i++) s += frame({ type: 'step', index: i, status: 'done', desc: '完成' })
  s += frame({ type: 'block', name: 'findings', data: full.findings })
  s += frame({ type: 'block', name: 'stats', data: full.stats })
  s += frame({ type: 'block', name: 'table', data: { columns: full.columns, rows: full.rows } })
  s += frame({ type: 'block', name: 'text', data: full.text })
  s += frame({ type: 'block', name: 'follow_ups', data: full.follow_ups })
  s += frame({ type: 'done', data: full })
  return s
}

/** 构造一段以 error 事件结尾的 SSE 帧（模拟问数中途失败） */
function sseErrBody(): string {
  const frame = (o: unknown): string => `data: ${JSON.stringify(o)}\n\n`
  return frame({ type: 'session', data: { session_id: 's1' } })
    + frame({ type: 'steps', data: [{ title: '意图识别' }] })
    + frame({ type: 'step', index: 0, status: 'fail', desc: '模型调用失败' })
    + frame({ type: 'error', message: '模型调用失败：请求超时' })
}

/** 登录并进入 /qa，返回输入框定位器 */
async function loginToQa(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.fill('[placeholder="请输入用户名"]', 'admin')
  await page.fill('[placeholder="请输入密码"]', 'admin123')
  await page.click('button.btn-login')
  await page.waitForURL((url) => url.pathname === '/qa')
  const input = page.locator('textarea[placeholder^="请写下您的想法"]')
  await expect(input).toBeVisible({ timeout: 10_000 })
  return input
}

test.describe('QA 关键路径', () => {
  test.beforeEach(async ({ page }) => {
    // 登录态开关：初始未登录，登录接口后置为已登录，供 /auth/check 断言
    let authed = false
    // 兜底：未 mock 到的 /api 一律 404（避免落到静态服务器被当 SPA 回退）
    await page.route('**/api/**', (r) =>
      r.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) }))
    // 具体接口（后注册优先匹配）
    await page.route('**/api/auth/check', (r) =>
      r.fulfill(authed
        ? { status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, user: 'admin' }) }
        : { status: 401, contentType: 'application/json', body: JSON.stringify({ detail: '未登录' }) }))
    await page.route('**/api/auth/login', (r) => {
      authed = true
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, user: 'admin' }) })
    })
    await page.route('**/api/auth/logout', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) }))
    // 注：这些 GET 端点返回裸数组/对象（http.get 直接回传响应体，未包 data 字段）
    await page.route('**/api/qa/sessions', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/qa/sources', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify([{ group: '演示数据', items: [{ key: 'demo', name: '示例台账' }] }]) }))
    await page.route('**/api/qa/quick-asks', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ enabled: true, hot: [{ question: '2026年各产品线利润率如何？', hit: 1 }] }) }))
    await page.route('**/api/qa/ask', (r) =>
      r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody() }))
  })

  test('登录 → /qa → 发送问题 → SSE 流式渲染结论 + 表格', async ({ page }) => {
    const input = await loginToQa(page)
    await input.fill('2026年各产品线利润率如何？')
    await page.click('button[aria-label="发送"]')

    // SSE 供证：结论文本渲染
    await expect(page.getByText('2026年各产品线利润率整体平稳')).toBeVisible({ timeout: 20_000 })
    // 表格表头 + 行数据
    await expect(page.getByText('产品线').first()).toBeVisible()
    await expect(page.getByText('C线').first()).toBeVisible()
    // 追问建议
    await expect(page.getByText('B线为什么下降？').first()).toBeVisible()
  })

  test('问数中途失败（SSE error 事件）→ 移除占位卡 + 错误 snackbar', async ({ page }) => {
    // 覆盖 beforeEach 的 ask 路由（后注册优先匹配）为失败流
    await page.route('**/api/qa/ask', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseErrBody() }))
    const input = await loginToQa(page)
    await input.fill('2026年各产品线利润率如何？')
    await page.click('button[aria-label="发送"]')

    // 失败：AI 占位卡被移除、错误以 snackbar 呈现（getApiErrorMsg 只取 axios detail，
    // SSE 流 error 事件 message 走兜底文案），用户消息保留
    await expect(page.getByText('问数请求失败，请稍后重试')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('2026年各产品线利润率如何？').first()).toBeVisible()
    await expect(page.locator('.qa-ai-card')).toHaveCount(0)
  })

  test('纯空白输入 → 发送按钮禁用（不产生请求）', async ({ page }) => {
    const input = await loginToQa(page)
    await input.fill('    ')
    const send = page.locator('button[aria-label="发送"]')
    await expect(send).toBeDisabled()
    // 必填字符后恢复可用
    await input.fill('2026年各产品线利润率如何？')
    await expect(send).toBeEnabled()
  })
})