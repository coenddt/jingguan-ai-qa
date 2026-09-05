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
    build: {
      // 大体积第三方库按需拆成独立 chunk，主包只留业务代码，利于缓存与首屏
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes('echarts') || id.includes('zrender')) return 'charts-lazy'
            if (id.includes('react') || id.includes('scheduler') || id.includes('react-dom')) return 'react'
            if (id.includes('react-router')) return 'router'
            if (id.includes('axios')) return 'http'
            if (id.includes('dayjs')) return 'time'
            if (id.includes('zustand')) return 'state'
            if (id.includes('emoji-mart')) return 'emoji'
            return 'vendor'
          },
        },
      },
      // vendor/图表 chunk 体积大属预期，仅对超此阈值告警
      chunkSizeWarningLimit: 700,
    },
  }
})
