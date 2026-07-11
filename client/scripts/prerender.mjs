/**
 * prerender.mjs
 *
 * Snapshots the landing page at build time using Playwright (already installed
 * as a dev dep for E2E tests). Runs automatically via the "postbuild" npm hook.
 *
 * What it does:
 *   1. Starts `vite preview` to serve the just-built dist/
 *   2. Opens a real Chromium browser, aborts API calls so auth resolves instantly
 *   3. Waits for the landing page hero to render
 *   4. Saves the full HTML over dist/index.html
 *
 * Result: crawlers and first-time visitors get real HTML instead of
 * <div id="root"></div>. React still hydrates normally on top of it.
 */

import { chromium } from '@playwright/test'
import { preview } from 'vite'
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const root = resolve(fileURLToPath(new URL('.', import.meta.url)), '..')

if (!existsSync(resolve(root, 'dist'))) {
  console.error('❌  dist/ not found — run npm run build first')
  process.exit(1)
}

// Public, content-rich routes worth snapshotting to static HTML. Each gets its
// OWN file so crawlers (and no-JS clients) receive route-correct <head> tags —
// critically a single self-referencing canonical. nginx `try_files $uri/`
// serves dist/<route>/index.html directly for these paths.
const ROUTES = [
  { path: '/',           selector: '.lnd-hero-title', out: 'dist/index.html' },
  { path: '/dosha-test', selector: '.dt-hero-title',  out: 'dist/dosha-test.html' },
]

const PORT = 4174
const PREVIEW_ORIGIN = `http://localhost:${PORT}`

// The shell's static fallback tags, read BEFORE the loop overwrites
// dist/index.html — used to strip the shell duplicates that react-helmet-async
// leaves behind when it adds its per-page <title>/<meta name="description">.
const shell = readFileSync(resolve(root, 'dist/index.html'), 'utf8')
const shellFallbacks = {
  shellTitle: (shell.match(/<title>([^<]*)<\/title>/) || [])[1] ?? null,
  shellDesc: (shell.match(/<meta name="description" content="([^"]*)"/) || [])[1] ?? null,
}

console.log('🔧  Starting Vite preview server…')
const server = await preview({
  root,
  preview: { port: PORT, host: false, open: false },
})

console.log('🌐  Launching Chromium…')
let browser
try {
  // Browser launch is inside the try so a missing/broken Chromium (e.g. in a
  // Docker build image without Playwright browsers) degrades gracefully instead
  // of failing the whole `npm run build`.
  browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] })
  const page = await browser.newPage()

  // Abort API calls → auth check throws immediately → user = null → public page renders
  await page.route('**/api/**', route => route.abort())
  // Also abort CDN requests that might slow networkidle
  await page.route('https://fonts.googleapis.com/**', route => route.continue())

  for (const { path, selector, out } of ROUTES) {
    await page.goto(`${PREVIEW_ORIGIN}${path}`, {
      waitUntil: 'networkidle',
      timeout: 25000,
    })

    // Wait for a route-specific element to confirm the page rendered
    await page.waitForSelector(selector, { timeout: 10000 }).catch(() => {
      console.warn(`⚠  ${selector} not found for ${path} — prerendering whatever rendered`)
    })

    // Brief pause for any remaining paint
    await page.waitForTimeout(800)

    // The shell (index.html) carries static fallback <title>/<meta> tags, and
    // react-helmet-async ADDS its per-page versions without removing (or
    // marking) the originals — so the captured head ships two different
    // <title>s and descriptions, and Google picks one unpredictably. Helmet's
    // insertion position varies by tag type, so the only deterministic rule is
    // content: drop the tag whose content exactly matches the shell's static
    // fallback whenever a differing duplicate of the same tag exists.
    await page.evaluate(({ shellTitle, shellDesc }) => {
      const titles = [...document.head.querySelectorAll('title')]
      if (titles.length > 1) {
        titles.filter((t) => t.textContent === shellTitle).forEach((t) => t.remove())
      }
      const descs = [...document.head.querySelectorAll('meta[name="description"]')]
      if (descs.length > 1) {
        descs.filter((d) => d.getAttribute('content') === shellDesc).forEach((d) => d.remove())
      }
    }, shellFallbacks)

    // Transient runtime UI must not be baked into the static snapshot: the
    // service worker registers during the capture and sonner shows its
    // "App is ready to work offline" toast, which would greet every first-time
    // visitor (and crawler) as frozen HTML until React hydrates and wipes it.
    await page.evaluate(() => {
      document.querySelectorAll('[data-sonner-toaster]').forEach((el) => {
        const section = el.closest('section')
        ;(section || el).remove()
      })
    })

    // React.lazy chunks trigger runtime-injected <link rel="modulepreload"> whose
    // href resolves to the preview server's absolute origin. Rewrite that origin to
    // root-relative so the saved HTML doesn't ship dead http://localhost:4174/…
    // preloads to production.
    const html = (await page.content()).split(PREVIEW_ORIGIN).join('')
    const outPath = resolve(root, out)
    mkdirSync(dirname(outPath), { recursive: true })
    writeFileSync(outPath, html, 'utf8')

    const kB = (html.length / 1024).toFixed(1)
    console.log(`✅  ${out} updated (${kB} kB) — ${path} pre-rendered`)
  }
  console.log('    Crawlers now receive full HTML. React hydrates on top.')
} catch (err) {
  console.warn('⚠  Prerender skipped (non-fatal):', err.message)
  console.warn('   Build is still valid — the SPA serves index.html and React renders normally.')
} finally {
  if (browser) await browser.close().catch(() => {})
  server.httpServer.close()
  process.exit(0)
}
