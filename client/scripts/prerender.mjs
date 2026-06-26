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
import { writeFileSync, existsSync } from 'fs'
import { resolve } from 'path'
import { fileURLToPath } from 'url'

const root = resolve(fileURLToPath(new URL('.', import.meta.url)), '..')

if (!existsSync(resolve(root, 'dist'))) {
  console.error('❌  dist/ not found — run npm run build first')
  process.exit(1)
}

console.log('🔧  Starting Vite preview server…')
const server = await preview({
  root,
  preview: { port: 4174, host: false, open: false },
})

console.log('🌐  Launching Chromium…')
let browser
try {
  // Browser launch is inside the try so a missing/broken Chromium (e.g. in a
  // Docker build image without Playwright browsers) degrades gracefully instead
  // of failing the whole `npm run build`.
  browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] })
  const page = await browser.newPage()

  // Abort API calls → auth check throws immediately → user = null → landing renders
  await page.route('**/api/**', route => route.abort())
  // Also abort CDN requests that might slow networkidle
  await page.route('https://fonts.googleapis.com/**', route => route.continue())

  await page.goto('http://localhost:4174/', {
    waitUntil: 'networkidle',
    timeout: 25000,
  })

  // Wait for the hero title to confirm landing rendered
  await page.waitForSelector('.lnd-hero-title', { timeout: 10000 }).catch(() => {
    console.warn('⚠  Hero title not found — prerendering whatever rendered')
  })

  // Brief pause for any remaining paint
  await page.waitForTimeout(800)

  const html = await page.content()
  writeFileSync(resolve(root, 'dist/index.html'), html, 'utf8')

  const kB = (html.length / 1024).toFixed(1)
  console.log(`✅  dist/index.html updated (${kB} kB) — landing page pre-rendered`)
  console.log('    Crawlers now receive full HTML. React hydrates on top.')
} catch (err) {
  console.warn('⚠  Prerender skipped (non-fatal):', err.message)
  console.warn('   Build is still valid — the SPA serves index.html and React renders normally.')
} finally {
  if (browser) await browser.close().catch(() => {})
  server.httpServer.close()
  process.exit(0)
}
