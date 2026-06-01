import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use /sap-cpi-assistant/ base for GitHub Pages production build,
// but / for local development so http://localhost:5173 works directly.
const isProd = process.env.NODE_ENV === 'production'

export default defineConfig({
  base: isProd ? '/sap-cpi-assistant/' : '/',
  plugins: [react()],
  server: {
    port: 5173,
    host: true,           // listen on 0.0.0.0 so network devices can reach it too
    open: false,          // we open the browser from start.bat
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
