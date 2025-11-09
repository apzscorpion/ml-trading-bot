import { defineNuxtConfig } from 'nuxt/config'

export default defineNuxtConfig({
  ssr: true,
  modules: ['@pinia/nuxt'],
  typescript: {
    typeCheck: true,
    strict: true,
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8182/api',
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || 'ws://localhost:8182/ws',
    },
  },
  css: ['~/assets/main.css'],
  app: {
    head: {
      title: 'Realtime Trading Intelligence',
      meta: [
        { name: 'description', content: 'Realtime Indian stock forecasting with regime-aware AI.' },
      ],
    },
  },
})
