import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_API_PROXY_TARGET: where the Vite dev server forwards /api/* requests.
//   In Docker Compose this must be the service name (http://api:8000) because
//   localhost inside the frontend container resolves to itself, not the API.
//   Locally (outside Docker) it defaults to http://localhost:8000.
// VITE_API_URL: injected into the browser bundle — always a host-visible address.
const proxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
