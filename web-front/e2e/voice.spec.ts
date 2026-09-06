/**
 * 语音输入 E2E（hermetic）：登录 → /qa → 点语音按钮 → 建 WS(/api/asr/ws) → 发 start →
 * 后端流式下行 transcript → 输入框实时回填识别文本 → done 收尾。
 *
 * WebSocket 用页面内注入的 FakeWebSocket 接管（本环境 routeWebSocket 对 ws:// 握手无效），
 * 测试从外部驱动 _emit 推送 transcript，端到端校验真实前端录音链路（getUserMedia→AudioContext→
 * PCM 上行→ onmessage 回填）。无需真实麦克风：Chromium 假音频 + 注入合成静音轨自动授权。
 */
import { test, expect } from '@playwright/test'

/** /api/config 返回的 AppConfig（stt=true 放开语音按钮；其余取默认） */
const appConfig = {
  greeting: { enabled: true, text: '', questions: [] },
  suggestions: true,
  tts: false,
  stt: true,
  modelConfig: true,
  hotRecommend: { enabled: true, threshold: 3 },
}

/** 注入 FakeWebSocket + 合成麦克风：录音链路完全在浏览器内闭环，测试可驱动下行消息 */
const injectVoiceMocks = (page: import('@playwright/test').Page) =>
  page.addInitScript(() => {
    // 1) 合成静音音频轨：确保 getUserMedia 同步 resolve，进入真实 AudioContext 链路
    const md = navigator.mediaDevices
    if (md) {
      md.getUserMedia = async () => {
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
        const ctx = new AC()
        return ctx.createMediaStreamDestination().stream
      }
    }
    // 2) FakeWebSocket：接管 new WebSocket，记录上行，暴露 _emit 供测试下行
    ;(window as unknown as { __wsOut: unknown[] }).__wsOut = []
    ;(window as unknown as { __wsSockets: unknown[] }).__wsSockets = []
    class FakeWebSocket {
      static CONNECTING = 0
      static OPEN = 1
      static CLOSING = 2
      static CLOSED = 3
      binaryType: string
      onopen: (() => void) | null = null
      onmessage: ((e: { data: unknown }) => void) | null = null
      onerror: (() => void) | null = null
      onclose: ((e: { code: number }) => void) | null = null
      readyState: number
      url: string
      constructor(url: string) {
        this.url = url
        // 同步置 OPEN：真实场景 WS 在录音就绪前已握手完成（start 需在 OPEN 下发送）
        this.readyState = FakeWebSocket.OPEN
        this.binaryType = 'blob'
        ;(window as unknown as { __wsSockets: FakeWebSocket[] }).__wsSockets.push(this)
        const sock = this
        setTimeout(() => { sock.onopen?.() }, 0)
      }
      send(data: unknown) { (window as unknown as { __wsOut: { data: unknown }[] }).__wsOut.push({ data }) }
      close() { this.readyState = FakeWebSocket.CLOSED }
      _emit(payload: { type: string; text?: string; final?: boolean; detail?: string }) {
        if (this.readyState === FakeWebSocket.OPEN) this.onmessage?.({ data: JSON.stringify(payload, null, 0) })
      }
    }
    ;(window as unknown as { WebSocket: typeof FakeWebSocket }).WebSocket = FakeWebSocket
  })

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

test.describe('语音输入（hermetic FakeWebSocket）', () => {
  test.beforeEach(async ({ page }) => {
    await injectVoiceMocks(page)
    let authed = false
    await page.route('**/api/auth/check', (r) =>
      r.fulfill(authed
        ? { status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, user: 'admin' }) }
        : { status: 401, contentType: 'application/json', body: JSON.stringify({ detail: '未登录' }) }))
    await page.route('**/api/auth/login', (r) => {
      authed = true
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, user: 'admin' }) })
    })
    await page.route('**/api/config', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(appConfig) }))
    await page.route('**/api/qa/sessions', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/qa/sources', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  })

  test('点语音按钮 → 发 start → 流式 transcript 实时回填输入框 → done 收尾', async ({ page }) => {
    const input = await loginToQa(page)

    // 语音按钮在 stt=true 下可用
    const mic = page.locator('button[aria-label="语音输入"]')
    await expect(mic).toBeEnabled()

    await mic.click()

// 前端已创建 WS 并发出 {action:'start'}（FakeWebSocket 记录上行）
    await expect.poll(async () => {
      const out = await page.evaluate(() => (window as unknown as { __wsOut: { data: unknown }[] }).__wsOut)
      return out.some((o) => typeof o.data === 'string' && String(o.data).includes('"start"'))
    }).toBe(true)

    // 模拟后端流式识别：partial → final → done
    await page.evaluate(() => {
      const w = window as unknown as { __wsSockets: { _emit(p: { type: string; text?: string; final?: boolean }): void }[] }
      const sock = w.__wsSockets[w.__wsSockets.length - 1]
      sock._emit({ type: 'transcript', text: '你好', final: false })
      sock._emit({ type: 'transcript', text: '你好，这是测试语音', final: true })
      sock._emit({ type: 'done' })
    })

    // 足够时间让 flushFinal 落盘固化结果
    await page.waitForTimeout(400)
    // 实时回填最终文本
    await expect(input).toHaveValue('你好，这是测试语音', { timeout: 5_000 })
    // done 后结束聆听（语音态关闭）
    await expect(mic).toBeEnabled()
  })
})