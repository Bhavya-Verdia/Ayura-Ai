import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import browserslist from 'browserslist'
import { browserslistToTargets } from 'lightningcss'

// Preload the two fonts that gate the first meaningful paint (body Manrope 400
// = hero subtitle/LCP element, display Fraunces = hero title). Without this
// they're only discovered after the CSS parses; preloading fetches them in
// parallel with the JS. Hashed filenames are only known at bundle time, hence
// a plugin instead of hand-written <link> tags.
const preloadCriticalFonts = () => ({
  name: 'preload-critical-fonts',
  transformIndexHtml: {
    order: 'post',
    handler(html, ctx) {
      if (!ctx.bundle) return
      const critical = /(?:manrope-latin-400-normal|fraunces-latin-opsz-normal).*\.woff2$/
      return Object.keys(ctx.bundle)
        .filter((f) => critical.test(f))
        .map((f) => ({
          tag: 'link',
          attrs: { rel: 'preload', as: 'font', type: 'font/woff2', href: `/${f}`, crossorigin: '' },
          injectTo: 'head',
        }))
    },
  },
})

// https://vite.dev/config/
export default defineConfig({
  envDir: '..',
  plugins: [
    // React Compiler auto-memoizes components/hooks at build time — the
    // equivalent of hand-written React.memo/useMemo/useCallback everywhere,
    // which cuts re-render work (the main source of interaction jank on
    // mid-range phones). Components that break the Rules of React are
    // skipped, not miscompiled.
    react({ babel: { plugins: ['babel-plugin-react-compiler'] } }),
    preloadCriticalFonts(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'pwa-512x512-maskable.png', 'og-image.png'],
      workbox: {
        // Fonts gate first paint, so precache them alongside js/css/html —
        // repeat visits (and offline) render text with zero network. Latin
        // subsets only: unicode-range means the browser never requests the
        // cyrillic/greek/vietnamese files, so precaching them would burn
        // ~160KB of mobile data for nothing. Images are left to nginx's
        // immutable HTTP cache.
        globPatterns: ['**/*.{js,css,html}', '**/*latin*.woff2'],
      },
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
  // Without explicit targets the lightningcss minifier collapses a
  // `backdrop-filter` + `-webkit-backdrop-filter` pair down to whichever comes
  // last (the -webkit- one, which Chromium does NOT support) — shipping glass
  // surfaces with no blur on Chrome/Android. Real targets make it emit the
  // standard property and keep/add the -webkit- prefix only for Safari.
  css: {
    lightningcss: {
      targets: browserslistToTargets(browserslist('defaults, iOS >= 14, Safari >= 14')),
    },
  },
  build: {
    cssMinify: 'lightningcss',
    rollupOptions: {
      output: {
        // Vite 8 bundles with rolldown, whose native chunking API is
        // advancedChunks (groups matched in order, first match wins). The old
        // function-form manualChunks was NOT honored reliably here: rolldown
        // placed React core itself inside vendor-markdown, which made every
        // chunk (and the entry) statically depend on the 46KB-gzip markdown
        // parser — defeating the whole split. Verified fixed via
        // scripts/check-bundle-size.mjs (initial path dropped ~46KB gzip).
        advancedChunks: {
          groups: [
            // React runtime — every page needs it; claim it FIRST so no other
            // group (markdown reaches React via hast-util-to-jsx-runtime) can
            // capture it.
            { name: 'vendor-react', test: /node_modules\/(?:react|react-dom|react-is|scheduler|react-router|react-router-dom)\// },
            { name: 'vendor-motion', test: /node_modules\/framer-motion\// },
            { name: 'vendor-query', test: /node_modules\/@tanstack\// },
            // Markdown parser (react-markdown + its micromark/mdast/unified/
            // hast tree) is only used by Chat + plan views — keep it OUT of
            // the initial path (Landing/Dashboard) so first-load JS stays lean.
            { name: 'vendor-markdown', test: /node_modules\/(?:react-markdown|remark-|micromark|mdast-|unist-|unified|hast-|vfile|devlop|bail|trough|ccount|markdown-table|longest-streak|escape-string-regexp|is-plain-obj|trim-lines|extend|html-url-attributes|inline-style-parser|style-to-(?:js|object)|estree-util-is-identifier-name|@ungap\/structured-clone|decode-named-character-reference|character-entities|property-information|space-separated-tokens|comma-separated-tokens)/ },
            { name: 'vendor-ui', test: /node_modules\/lucide-react\// },
          ],
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
  },
  // Same proxy for `vite preview` so the production build can be exercised
  // against a local backend (perf measurement, pre-deploy smoke tests).
  preview: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    }
  }
})
