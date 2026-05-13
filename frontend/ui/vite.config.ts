import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/mgmt': {
        target: 'http://localhost:9800',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/mgmt/, '/api/v1'),
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, '..', 'packages', 'web', 'dist'),
    emptyOutDir: true,
  },
})
