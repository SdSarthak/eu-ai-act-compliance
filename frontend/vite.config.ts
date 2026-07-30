import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Inside Docker the API lives on another host, so the dev proxy target is
// configurable: API_PROXY_TARGET=http://backend:8000
const apiTarget = process.env.API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 5173,
  },
})
