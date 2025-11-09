import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // Allow network access
    port: 5155,
    proxy: {
      '/api': {
        target: 'http://localhost:8182',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8182',
        ws: true
      }
    }
  }
})

