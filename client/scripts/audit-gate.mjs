#!/usr/bin/env node
// CI security gate — fails the build on high+ severity CVEs in PRODUCTION
// dependencies only (the code that actually ships to users' browsers).
//
// Dev / build-tool CVEs (postcss, js-yaml, fast-uri, brace-expansion, workbox…)
// are intentionally out of scope: they run at build time on our own trusted
// source/config and never reach the shipped bundle. We scope with --omit=dev
// so the gate tracks real user-facing risk instead of build-tree noise.
//
// ALLOWLIST — advisories reviewed and judged non-exploitable for THIS app.
// Each entry needs a justification and a re-audit trigger:
//
//   GHSA-qwww-vcr4-c8h2  react-router "RSC Mode CSRF Bypass". We ship a client
//     SPA (react-router-dom <Routes>, no React Server Components / server
//     actions), so the RSC attack surface does not exist here. The advisory
//     range (7.12.0–8.2.0) currently has NO forward fix — npm's only remedy is a
//     backward, breaking downgrade to 7.11.0. Remove this entry and upgrade once
//     react-router publishes a patched release above 8.2.0.
import { execSync } from 'node:child_process'

const ALLOW = new Set(['GHSA-qwww-vcr4-c8h2'])

let report
try {
  const out = execSync('npm audit --audit-level=high --omit=dev --json', { encoding: 'utf8' })
  report = JSON.parse(out)
} catch (e) {
  // npm audit exits non-zero when it finds vulnerabilities; the JSON payload is
  // still written to stdout, so parse that rather than treating it as an error.
  report = JSON.parse(e.stdout || '{}')
}

const V = report.vulnerabilities || {}

// Collect every GHSA id behind a package, following npm's `via` chain (a `via`
// entry is either an advisory object with a url, or a string naming another
// vulnerable package that this one depends on).
const ghsasOf = (name, seen = new Set()) => {
  if (seen.has(name)) return []
  seen.add(name)
  const info = V[name]
  if (!info) return []
  const ids = []
  for (const v of info.via || []) {
    if (typeof v === 'string') ids.push(...ghsasOf(v, seen))
    else if (v.url) ids.push(v.url.split('/').pop())
  }
  return ids
}

const blocking = []
for (const [name, info] of Object.entries(V)) {
  if (!['high', 'critical'].includes(info.severity)) continue
  const ids = [...new Set(ghsasOf(name))]
  // Skip only when EVERY advisory behind this package is allowlisted. An unknown
  // advisory (no ids resolved) always blocks.
  if (ids.length && ids.every((id) => ALLOW.has(id))) continue
  blocking.push(`${name} (${info.severity}): ${ids.join(', ') || 'unknown advisory'}`)
}

if (blocking.length) {
  console.error('✖ Blocking high+ severity vulnerabilities in production deps:')
  for (const b of blocking) console.error('  - ' + b)
  console.error('\nFix forward (npm i <pkg>@latest). If reviewed and non-exploitable, add the')
  console.error('GHSA id to ALLOW in client/scripts/audit-gate.mjs with a justification comment.')
  process.exit(1)
}

console.log('✔ npm audit gate: no blocking high+ vulnerabilities in production dependencies.')
if (ALLOW.size) console.log('  (allowlisted after review: ' + [...ALLOW].join(', ') + ')')
