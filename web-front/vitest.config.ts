import { defineConfig } from 'vitest/config'

// vitest 配置：jsdom 环境；npm test 为自动化门禁
export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})