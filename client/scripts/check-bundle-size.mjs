// Bundle budget gate — fails the build if the JavaScript on the critical
// first-load path grows past budget, so a stray import can't silently regress
// startup performance. Runs in postbuild (after prerender) and in CI.
//
// "Initial path" = every script the browser fetches before first render:
// the entry <script type="module"> plus all <link rel="modulepreload"> chunks
// in dist/index.html. Lazy route/vendor chunks (PlanViewer, markdown…) are
// intentionally NOT counted — growing those is fine.
import { readFileSync, statSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../dist')

// ~210 KB gzip today (React 19 + router + framer-motion + query + app core).
// Headroom for organic growth, but a whole new heavyweight dependency on the
// critical path will trip it — which is the point.
const BUDGET_GZIP_BYTES = 250 * 1024

const html = readFileSync(resolve(DIST, 'index.html'), 'utf8')
const files = new Set()
for (const m of html.matchAll(/<script[^>]+src="\/?([^"]+\.js)"/g)) files.add(m[1])
for (const m of html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="\/?([^"]+\.js)"/g)) files.add(m[1])

if (files.size === 0) {
  console.error('check-bundle-size: no script tags found in dist/index.html — did the build change shape?')
  process.exit(1)
}

let total = 0
const rows = []
for (const f of files) {
  const path = resolve(DIST, f)
  try {
    statSync(path)
  } catch {
    continue // external/absent (e.g. registerSW inline) — skip
  }
  const gz = gzipSync(readFileSync(path)).length
  total += gz
  rows.push([f, gz])
}

rows.sort((a, b) => b[1] - a[1])
const kb = (n) => `${(n / 1024).toFixed(1)} KB`
for (const [f, gz] of rows) console.log(`  ${kb(gz).padStart(9)}  ${f}`)
console.log(`  ${'─'.repeat(30)}\n  ${kb(total).padStart(9)}  initial-path JS (gzip)  [budget ${kb(BUDGET_GZIP_BYTES)}]`)

if (total > BUDGET_GZIP_BYTES) {
  console.error(`\n✖ Initial JS ${kb(total)} exceeds the ${kb(BUDGET_GZIP_BYTES)} budget.`)
  console.error('  Either move the new code off the critical path (lazy import / manualChunks)')
  console.error('  or consciously raise BUDGET_GZIP_BYTES in scripts/check-bundle-size.mjs.')
  process.exit(1)
}
console.log('✓ within budget')
