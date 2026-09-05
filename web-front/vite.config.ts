import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    preview: {
      // vite preview 生产预览：同样把 /api 转发到后端，保持端口直连即可访问完整功能
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      // 经实测 manualChunks 拆分会导致 React 运行时 useState undefined 崩溃（分包边界问题），
      // 为保稳定性回退整体分包；真实性能收益已由路由级 React.lazy + ECharts 懒加载承担。
    },
  }
})
