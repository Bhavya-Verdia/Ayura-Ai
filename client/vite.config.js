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
      const critical = /(?:manrope-latin-wght-normal|fraunces-latin-opsz-normal).*\.woff2$/
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

// Emit dist/app.html — a byte-copy of the built index.html, kept as the SPA
// fallback document for every route that is NOT pre-rendered.
//
// WHY: scripts/prerender.mjs overwrites dist/index.html with a full snapshot of
// `/` (69 kB of landing-page DOM). That file was also the fallback nginx and the
// service worker served for unmatched paths, so opening /dashboard, /login or
// /settings painted the entire marketing homepage — hero, "Sign In", "Get
// Started" — for ~0.9-1.3s on a throttled phone, then a spinner, then the real
// screen. main.jsx uses `createRoot`, not `hydrateRoot`, so that markup is
// discarded wholesale: on any route but `/` it was never anything but cost.
//
// app.html is 4.6 kB against index.html's 69 kB and carries only the entry
// preloads, not the runtime-injected Landing chunk + Landing.css the snapshot
// had absorbed — so app routes stop fetching landing code altogether.
//
// It must be emitted HERE, in the bundle, rather than in postbuild: the PWA
// plugin builds its precache manifest from the emitted output, and
// `navigateFallback` below can only point at a precached file. Copying the
// index.html asset in generateBundle also means it inherits every
// transformIndexHtml edit (font preloads, PWA register script) for free.
const emitAppShell = () => ({
  name: 'emit-app-shell',
  enforce: 'post',
  generateBundle(_options, bundle) {
    const index = bundle['index.html']
    if (!index || index.type !== 'asset') {
      // Loud rather than silent: without this file every app route silently
      // falls back to the landing snapshot again.
      this.warn('emit-app-shell: index.html asset not found — app.html NOT emitted')
      return
    }
    this.emitFile({ type: 'asset', fileName: 'app.html', source: index.source })
  },
})

// https://vite.dev/config/
export default defineConfig({
  envDir: '..',
  plugins: [
    emitAppShell(),
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
        // Installed-PWA navigations are served from the precache, so this — not
        // just nginx — decides which HTML an app route gets offline or on a warm
        // start. It defaults to 'index.html', i.e. the pre-rendered landing
        // snapshot, which is exactly the wrong-page paint app.html exists to
        // stop (see the emitAppShell plugin above). Keep the two in sync.
        navigateFallback: '/app.html',
        // `/` and `/dosha-test` have their own pre-rendered HTML worth serving
        // from the network; everything else is the SPA and wants the shell.
        navigateFallbackDenylist: [/^\/api\//, /^\/uploads\//],
        // Web push + notification-click handlers live in a separate file so
        // the generated Workbox SW stays plugin-managed. Copied from public/
        // into dist untouched; not precache-manifested, so it must stay
        // stable-named (it is content-versioned only through sw.js updates).
        importScripts: ['push-sw.js'],
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
  // The target list must describe what the app ACTUALLY supports, because
  // lightningcss makes lowering/prefixing decisions from it.
  //
  // It used to claim `iOS >= 14`, which was fiction: the shipped CSS requires
  // `color-mix()` (Safari 16.2 — `--ayura-accent-soft` and the button hovers)
  // and `@property` (Safari 16.4 — the animated gradient angle). On iOS 14/15
  // those declarations are invalid, so the target was promising support the
  // stylesheet could not deliver. 16.4 is the first version where everything
  // load-bearing works.
  //
  // Two features shipped here are NEWER than the floor on purpose, because they
  // degrade to "no optimisation" rather than to a broken layout:
  // `content-visibility` (Safari 18) and `text-wrap` (Safari 17.5).
  // Viewport units (`dvh`/`svh`) are guarded by @supports instead — see
  // "App page roots" in index.css for why a duplicate declaration cannot work.
  //
  // NOTE: raising this floor must NOT lose `-webkit-backdrop-filter`. Safari
  // only dropped the prefix in 18, so at a 16.4 floor lightningcss still emits
  // it — verified in the built CSS. Re-check if the floor ever moves past 18.
  css: {
    lightningcss: {
      // The `>= 16.4` clauses are load-bearing, not decorative: `defaults`
      // alone resolves to iOS 18.5+ (it is "last 2 versions / >0.5%"), and at
      // that floor lightningcss stops emitting -webkit-backdrop-filter. The
      // union pulls 16.4→current back in; the `not` clauses drop what
      // `defaults`' >0.5% bucket would otherwise re-admit below the floor.
      targets: browserslistToTargets(
        browserslist(
          'defaults, ios_saf >= 16.4, safari >= 16.4, not ios_saf < 16.4, not safari < 16.4'
        )
      ),
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
