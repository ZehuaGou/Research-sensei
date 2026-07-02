import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const backendTarget = process.env.VITE_BACKEND_PROXY ?? 'http://127.0.0.1:8765'
const wsTarget = backendTarget.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 13000,
    proxy: {
      '/api': backendTarget,
      '/ws': { target: wsTarget, ws: true },
    },
  },
})
