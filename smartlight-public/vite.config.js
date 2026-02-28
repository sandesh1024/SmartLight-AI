import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: '0.0.0.0',   // ← allows access from other devices on same WiFi
    proxy: {
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
})