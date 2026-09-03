---
name: "build-timestamp-directory"
description: "Configures Vite build to output to a timestamp-based directory (dist/YYYYMMDDHHmmss/{projectName}/), keeping only the latest 10 builds and automatically removing the oldest ones."
---

# Build Timestamp Directory

## 核心概念

Vite 构建输出到 `dist/YYYYMMDDHHmmss/{projectName}/`，保留最近 10 次构建，超出自动清理。仅影响 `vite build`，不影响 `vite dev`。

## 步骤 1：添加插件到 `vite.config.ts`

```js
// vite.config.ts
import { defineConfig } from 'vite'

function timestampOutDir(projectName) {
  return {
    name: 'timestamp-outdir',
    config(config, { command }) {
      if (command === 'build') {
        const d = new Date()
        const p = (n) => String(n).padStart(2, '0')
        const ts = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
        config.build = config.build || {}
        config.build.outDir = `dist/${ts}/${projectName}`
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), timestampOutDir('{项目名}')], // 替换为实际项目名
})
```

**注意**：Vite 插件 `config` hook 中不能安全执行 `fs` 操作，清理逻辑分离到步骤 2。

## 步骤 2：创建 `cleanup.mjs`

```js
// cleanup.mjs
import fs from 'fs'
import path from 'path'
import { spawnSync } from 'child_process'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.resolve(__dirname, 'dist')
const MAX_BACKUPS = 10

function removeDir(dirPath) {
  try {
    fs.rmSync(dirPath, { recursive: true, force: true })
    if (!fs.existsSync(dirPath)) return true
  } catch {
  }
  // Windows 回退：fs.rmSync 被文件系统锁阻塞时用 PowerShell
  spawnSync('powershell', [
    '-NoProfile', '-Command',
    `Remove-Item -Path "${dirPath}" -Recurse -Force`,
  ], { encoding: 'utf-8', timeout: 10000 })
  return !fs.existsSync(dirPath)
}

if (!fs.existsSync(distDir)) process.exit(0)

const dirs = fs.readdirSync(distDir, { withFileTypes: true })
  .filter(d => d.isDirectory() && /^\d{14}$/.test(d.name))
  .map(d => d.name)
  .sort()

if (dirs.length > MAX_BACKUPS) {
  const toRemove = dirs.slice(0, dirs.length - MAX_BACKUPS)
  console.log(`[cleanup] Removing ${toRemove.length} old build dirs: ${toRemove.join(', ')}`)
  for (const dir of toRemove) removeDir(path.join(distDir, dir))
}

const remaining = fs.readdirSync(distDir, { withFileTypes: true })
  .filter(d => d.isDirectory() && /^\d{14}$/.test(d.name)).length
console.log(`[cleanup] ${remaining} build dirs retained`)
```

## 步骤 3：更新 `package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build && node cleanup.mjs",
    "preview": "vite preview"
  }
}
```

删除 `prebuild` 脚本（保留历史构建，不清 `dist`）。

## 输出结构

```
dist/
├── {YYYYMMDDHHmmss}/
│   └── {项目名}/
│       ├── index.html
│       ├── assets/
│       │   ├── index-xxx.js
│       │   └── ...
│       └── ...
├── {older_timestamp}/
│   └── {项目名}/
└── ...
```

最多保留 10 个时间戳目录。超出的旧目录在下一次构建后自动删除。

## 验证清单

- [ ] `dist/` 包含时间戳子目录
- [ ] 项目名子目录存在，内有 `index.html` 和 `assets/`
- [ ] 构建 11+ 次后只保留最近 10 个
- [ ] 构建输出显示 `[cleanup]` 日志

## 禁止事项

❌ 禁止在插件内直接操作 `fs`（被 Vite 沙盒静默拦截）  
❌ 禁止用 `prebuild` 清 `dist`（破坏历史保留）  
❌ 禁止修改 `vite dev` 的输出路径  

## 注意事项

1. **零外部依赖**：`cleanup.mjs` 仅用 `fs`、`path`、`child_process` 内置模块
2. **Windows 兼容**：`fs.rmSync` 被文件系统锁阻塞时自动回退 PowerShell `Remove-Item`
3. **保留数量可调**：修改 `MAX_BACKUPS` 变量即可调整保留上限
4. **回滚友好**：历史构建保留在 `dist/` 下，改 Web 服务器指向即可回滚
5. **仅构建时生效**：`config` hook 的 `command === 'build'` 判断确保开发服务器不受影响
