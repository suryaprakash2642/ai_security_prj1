import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/api/l1': { target: 'http://localhost:8001', rewrite: path => path.replace(/^\/api\/l1/, ''), changeOrigin: true },
      '/api/l3': { target: 'http://localhost:8300', rewrite: path => path.replace(/^\/api\/l3/, ''), changeOrigin: true },
      '/api/l5': { target: 'http://localhost:8500', rewrite: path => path.replace(/^\/api\/l5/, ''), changeOrigin: true },
      '/api/l6': { target: 'http://localhost:8600', rewrite: path => path.replace(/^\/api\/l6/, ''), changeOrigin: true },
      '/api/l7': { target: 'http://localhost:8700', rewrite: path => path.replace(/^\/api\/l7/, ''), changeOrigin: true },
      '/api/l8': { target: 'http://localhost:8800', rewrite: path => path.replace(/^\/api\/l8/, ''), changeOrigin: true },
    },
  },
})
