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
//
// '/' must stay LAST. Its snapshot overwrites dist/index.html, and the preview
// server answers every other route with dist/index.html — so a route captured
// after it boots on top of the landing page's baked <head>. Production's
// /dosha-test shipped that way: two <title>s and two canonicals, one pointing
// at the home page. assertSingleHead below fails the build if it happens again.
const ROUTES = [
  { path: '/dosha-test', selector: '.dt-hero-title',  out: 'dist/dosha-test.html' },
  { path: '/',           selector: '.lnd-hero-title', out: 'dist/index.html' },
]

// A snapshot with two of any of these tells a crawler two different things
// about the page. Throwing here lands in the catch below, which skips the
// prerender rather than shipping it.
function assertSingleHead(html, path) {
  const head = html.slice(0, html.indexOf('</head>'))
  for (const [name, re] of [
    ['<title>', /<title>/g],
    ['canonical', /<link rel="canonical"/g],
    ['og:url', /property="og:url"/g],
    ['description', /<meta name="description"/g],
  ]) {
    const n = (head.match(re) || []).length
    if (n > 1) throw new Error(`${path}: ${n} ${name} tags in the captured <head>`)
  }
}

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

// NOTE: the SPA fallback document (dist/app.html — the pristine shell that
// every NON-prerendered route is served) is emitted during the build by the
// `emitAppShell` plugin in vite.config.js, deliberately not here: it has to
// exist before vite-plugin-pwa builds its precache manifest, and postbuild
// runs long after that. See that plugin for why the fallback can't be
// index.html.

// Set by the hydration check below. Everything else here is non-fatal by
// design; that check fails CI because its failure is otherwise invisible.
let exitCode = 0

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

  // Tell the app it is being snapshotted, BEFORE any of its script runs.
  // Third-party SDKs (Sentry, PostHog) are dynamically imported when a key is
  // configured, and that has two consequences during a capture, both bad:
  //
  //   1. The browser injects a <link rel="modulepreload"> for the SDK chunk into
  //      the live DOM, and page.content() bakes it into the snapshot as though it
  //      were a static dependency of `/`. Sentry alone is 84 kB gzip, which both
  //      blew the initial-JS budget and — the real damage — would have made every
  //      landing visitor eagerly preload the SDK that main.jsx deliberately
  //      loads lazily.
  //   2. The build machine would report a live pageview and open a Sentry
  //      session on every build, i.e. CI noise inside production analytics.
  //
  // Route-blocking the chunks instead would mean matching hashed filenames; a
  // flag read at init is stable. Route chunks (Landing, useTranslation) are NOT
  // suppressed — preloading those is exactly what the snapshot is for.
  await page.addInitScript(() => { window.__PRERENDER__ = true })

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
    //
    // Only the toast list goes. The <section> around it is rendered by
    // <Toaster> whether or not a toast is showing, and main.jsx hydrates this
    // snapshot, so removing it would make the snapshot disagree with React.
    await page.evaluate(() => {
      document.querySelectorAll('ol[data-sonner-toaster]').forEach((el) => el.remove())
    })

    // main.jsx hydrates this snapshot (hydrateRoot) instead of redrawing it.
    // Hydration expects each <Suspense> boundary's HTML to sit between
    // <!--$--> and <!--/$-->, which a server render writes and a browser DOM
    // never contains, so without them React gives up at the first boundary
    // and redraws the whole page. These routes render exactly two, both
    // around #main-content (App.jsx): App's around <Routes>, whose content is
    // the <main> itself, and PageWrapper's inside it. A third boundary on
    // these routes would need its markers added here.
    //
    // The same goes for adjacent text nodes: `{a}{b}` is two text nodes in the
    // DOM and one in serialized HTML, so hydration finds one where it expects
    // two. A server render separates them with <!-- -->, which hydration skips.
    const marked = await page.evaluate(() => {
      const main = document.getElementById('main-content')
      if (!main) return false
      const walker = document.createTreeWalker(document.getElementById('root'), NodeFilter.SHOW_TEXT)
      const texts = []
      for (let n = walker.nextNode(); n; n = walker.nextNode()) texts.push(n)
      texts.forEach((t) => {
        if (t.nextSibling && t.nextSibling.nodeType === Node.TEXT_NODE) t.after(document.createComment(' '))
      })
      main.before(document.createComment('$'))
      main.after(document.createComment('/$'))
      main.prepend(document.createComment('$'))
      main.append(document.createComment('/$'))
      return true
    })
    if (!marked) throw new Error(`${path}: no #main-content to mark for hydration`)

    // React.lazy chunks trigger runtime-injected <link rel="modulepreload"> whose
    // href resolves to the preview server's absolute origin. Rewrite that origin to
    // root-relative so the saved HTML doesn't ship dead http://localhost:4174/…
    // preloads to production.
    let html = (await page.content()).split(PREVIEW_ORIGIN).join('')

    // Inline the stylesheets. Each was a render-blocking request after the
    // HTML, so on a phone the snapshot sat fully downloaded and unpainted for
    // one more round trip (Lighthouse: ~450 ms). Together they are ~17 kB gzip.
    //
    // Loading the route's chunk still makes Vite add a <link> for the route's
    // own stylesheet (~6 kB gzip), after first paint and without blocking it.
    // Leaving a disabled <link> to satisfy Vite's check does not help: Chrome
    // downloads disabled stylesheets too, so it fetched index.css as well.
    html = html.replace(
      /<link rel="stylesheet"(?: crossorigin="")? href="(\/assets\/[^"]+\.css)">/g,
      (tag, href) => {
        const css = readFileSync(resolve(root, 'dist' + href), 'utf8')
        return `<style data-href="${href}">${css.replace(/<\/style/gi, '<\\/style')}</style>`
      },
    )
    assertSingleHead(html, path)
    const outPath = resolve(root, out)
    mkdirSync(dirname(outPath), { recursive: true })
    writeFileSync(outPath, html, 'utf8')

    const kB = (html.length / 1024).toFixed(1)
    console.log(`✅  ${out} updated (${kB} kB) — ${path} pre-rendered`)
  }
  console.log('    Crawlers now receive full HTML. React hydrates on top.')

  // main.jsx hydrates these snapshots. If the first client render stops
  // matching one, React draws that page again over it, which costs the LCP the
  // snapshot exists for and logs nothing a visitor would report. So load each
  // written file the way a first-time visitor does and check that the title
  // on screen afterwards is the very node the HTML delivered.
  const failures = []
  for (const { path, selector } of ROUTES) {
    const check = await browser.newPage()
    await check.route('**/api/**', (route) => route.abort())
    const errors = []
    check.on('console', (m) => { if (m.type() === 'error' && m.text().includes('[hydrate]')) errors.push(m.text().slice(0, 200)) })
    await check.addInitScript((sel) => {
      document.addEventListener('readystatechange', () => {
        if (document.readyState === 'interactive') window.__snapshotNode = document.querySelector(sel)
      })
    }, selector)
    await check.goto(`${PREVIEW_ORIGIN}${path}`, { waitUntil: 'networkidle', timeout: 25000 })
    await check.waitForTimeout(1000)
    const kept = await check.evaluate((sel) => !!window.__snapshotNode && window.__snapshotNode === document.querySelector(sel), selector)
    if (!kept || errors.length) failures.push(`${path}: snapshot ${kept ? 'kept' : 'redrawn'}${errors.length ? `, ${errors[0]}` : ''}`)
    await check.close()
  }
  if (failures.length) {
    console.error('❌  Hydration check failed — React redraws these pages instead of adopting the snapshot:')
    failures.forEach((f) => console.error('   ', f))
    if (process.env.CI) exitCode = 1
  } else {
    console.log('✅  Hydration check: React adopts every snapshot without redrawing it')
  }
} catch (err) {
  console.warn('⚠  Prerender skipped (non-fatal):', err.message)
  console.warn('   Build is still valid — the SPA serves index.html and React renders normally.')
} finally {
  if (browser) await browser.close().catch(() => {})
  server.httpServer.close()
  process.exit(exitCode)
}
