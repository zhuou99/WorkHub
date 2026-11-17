import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    // 把 /api 与 /health 代理到后端：前后端同源，登录 Cookie 不再有跨 host 丢失问题。
    // 不管用 localhost 还是 127.0.0.1 打开页面都能正常登录。
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5277',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:5277',
        changeOrigin: true,
      },
    },
  },
})
