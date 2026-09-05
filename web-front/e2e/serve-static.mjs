// 极简静态服务器：托管 dist 产物 + SPA fallback（供 Playwright webServer 使用，无第三方依赖）
import http from 'node:http'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { join, extname, normalize } from 'node:path'

const ROOT = normalize(join(process.cwd(), 'dist'))
const PORT = Number(process.env.PORT || 4173)

const MIME = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.map': 'application/json',
}

http
  .createServer((req, res) => {
    let pathname = '/'
    try {
      pathname = decodeURIComponent(new URL(req.url || '/', 'http://x').pathname)
    } catch {
      pathname = '/'
    }
    const file = normalize(join(ROOT, pathname === '/' ? 'index.html' : pathname))
    if (!file.startsWith(ROOT)) {
      res.statusCode = 403
      res.end()
      return
    }
    if (existsSync(file) && statSync(file).isFile()) {
      res.setHeader('content-type', MIME[extname(file).toLowerCase()] || 'application/octet-stream')
      createReadStream(file).pipe(res)
      return
    }
    // SPA fallback：非静态资源一律回退到 index.html（由前端路由接管）
    res.setHeader('content-type', 'text/html; charset=utf-8')
    createReadStream(join(ROOT, 'index.html')).pipe(res)
  })
  .listen(PORT, () => console.log(`[e2e-static] serving ${ROOT} on :${PORT}`))