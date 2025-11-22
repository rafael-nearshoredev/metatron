import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      // Proxy API requests to the backend server
      '/api': {
        target: process.env.VITE_APPLICATION_SERVER_URL || 'http://localhost:5885',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api/, ''),
        configure: (proxy, options) => {
          proxy.on('error', (err: Error, req: any, res: any) => {
            console.log('Proxy error:', err)
          })
          proxy.on('proxyReq', (proxyReq: any, req: any, res: any) => {
            console.log('Proxying request:', req.method, req.url, '→', options.target + proxyReq.path)
          })
        }
      }
    }
  }
})