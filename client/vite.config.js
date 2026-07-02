import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  envDir: '..',
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'pwa-512x512-maskable.png', 'og-image.png'],
      manifest: {
        name: 'Ayura AI — Adaptive Ayurvedic Wellness',
        short_name: 'Ayura AI',
        description: 'AI-Powered Holistic Wellness Platform',
        theme_color: '#100D09',
        background_color: '#100D09',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      }
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('framer-motion'))                return 'vendor-motion'
          if (id.includes('@tanstack/react-query'))         return 'vendor-query'
          // Markdown parser (react-markdown + its micromark/mdast/unified/hast
          // tree) is only used by Chat + plan views — keep it OUT of the initial
          // path (Landing/Dashboard) so first-load JS stays lean.
          if (id.includes('react-markdown') || id.includes('remark') ||
              id.includes('micromark') || id.includes('mdast') ||
              id.includes('/unist') || id.includes('unified') ||
              id.includes('/hast') || id.includes('/vfile') ||
              id.includes('/decode-named-character-reference') ||
              id.includes('/property-information') ||
              id.includes('/space-separated-tokens') ||
              id.includes('/comma-separated-tokens'))       return 'vendor-markdown'
          if (id.includes('lucide-react'))                 return 'vendor-ui'
          if (id.includes('react-dom') ||
              id.includes('react-router') ||
              id.includes('/react/'))                      return 'vendor-react'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
