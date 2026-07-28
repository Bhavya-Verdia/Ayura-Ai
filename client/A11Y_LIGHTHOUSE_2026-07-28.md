# Keyboard / Landmark / Lighthouse Pass — 2026-07-28

Closes two of the four items the 2026-07-27 launch audit listed as **"Still not
covered"**: keyboard tab-order, and a fresh Lighthouse run. The other two —
real iOS/Android hardware and the GPU-compositing flicker check — remain open
and **cannot** be closed from this machine.

## Method

- Production build (`npm run build`), served by `vite preview` on :4173. Not the
  dev server — the audit targets the minified CSS and the prerendered HTML.
- Lighthouse 13.4.1 CLI, default **mobile** preset (412x823, 4x CPU throttle,
  simulated slow 4G), headless Chrome for Testing on a clean profile.
- Keyboard: scripted Tab walk (`kbd-audit.mjs`), 390x844, **both Chromium and
  WebKit**, `serviceWorkers: 'block'` — without that the PWA service worker
  serves stale assets and the run silently audits the previous build.
- Routes: the 7 public ones. The 12 auth-gated routes were **not** re-walked
  here; see "Not covered" below.

## Scores (mobile preset)

| route | perf | a11y before → after | best-practices | seo |
|---|---|---|---|---|
| `/` | 83 | 100 → 100 | 96 | 100 |
| `/dosha-test` | 90 | 98 → **100** | 96 | 100 |
| `/login` | 82 | 93 → **100** | 96 | 100 |
| `/register` | 82 | — → **100** | 96 | 100 |

Perf is unchanged by this pass (nothing here touches the loading path) and
matches the ~83 recorded previously. FCP ~2.5–3.1 s, LCP ~3.1–3.9 s,
**TBT 0 ms, CLS 0** on every route — the layout and main-thread numbers are
already clean; the score is held down by network-simulated paint timings.

## Fixed

### 1. No `<main>` landmark on any route except Landing
`PageWrapper` renders the element the skip link jumps to (`#main-content`), and
it was a `<div>`. So "Skip to content" moved focus into a generic container with
no landmark, and screen-reader users had no main region to jump to. Landing
passed only because it happened to have its own inner `<main>`.

Both `PageWrapper` branches now render `<main>`. Landing's and Admin's inner
`<main>` were demoted to `<div>` — otherwise the fix would have produced *nested*
main landmarks, which is its own violation. Verified: exactly 1 `<main>` on `/`,
`/register`, `/admin`, `/login`, `/dosha-test`, `/terms`.

No CSS targets a bare `main` selector, and `.dash-main` has no rule at all
(Admin styles it inline), so the tag swap is visually inert.

### 2. The password-reveal button was three defects in one control
`.auth-pw-eye` on both `/login` and `/register`:
- **No accessible name** — Lighthouse `button-name` failure; screen readers
  announced a bare "button". Now `aria-label` that tracks state
  ("Show password" / "Hide password") plus `aria-pressed`.
- **`tabIndex={-1}`** — keyboard users could *never* toggle password visibility.
  Removed. It picks up the global `:focus-visible` teal ring automatically.
- **23x23 px**, failing SC 2.5.8. Now 32x32 via `min-width/height`; `right` was
  pulled 11px → 7px so the wider box leaves the icon optically where it was, and
  the input's 40px right padding still clears it.

### 3. `.auth-forgot` was a 104x19 target
`inline-flex` + `min-height: 24px` — passes SC 2.5.8 with the text unmoved.

### 4. Consent checkbox 13x13 → 18x18
SC 2.5.8 already passed here (the wrapping `<label>` gives it a 315x43
activation area) — 13px was simply an uncomfortable phone tap.

### 5. `getByLabel(/Password/i)` in `auth.spec.js` became ambiguous
Naming the reveal button correctly made the loose regex match two elements
(strict-mode violation). The **test** was narrowed to `{ exact: true }` rather
than compromising the accessible name.

## Investigated and NOT bugs

- **`.scroll-to-top` flagged as a focus stop on a hidden element.** False
  positive in the audit script: it caught the button mid-entrance while
  `AnimatePresence` was still at `opacity: 0`. Measured after settling —
  `opacity: 1`, `visibility: visible`, 44x44. No change made.
- **WebKit skips every link in the tab ring** (13 stops on `/` vs Chromium's 29;
  the skip link is not reachable at all). This is Safari's default — links are
  not tabbable unless "Full Keyboard Access" is on. Platform behaviour, not an
  app defect. Worth knowing when hand-testing on a Mac or iPhone: **the skip
  link will look broken in Safari until that setting is enabled.**
- **`errors-in-console` fails on every route** — a single 502 on
  `/api/profile/me`, because `vite preview` proxies `/api` to :8000 and no
  backend was running. Harness artifact.

## Known, not fixed

**Public legal pages fire `/api/profile/me` and surface a "Server error. Please
try again." toast when it fails.** On `/terms` and `/privacy` — logged-out,
purely static pages — a backend hiccup pops an error toast at a visitor who
never asked for anything. Under the test harness this is the 502 above, so the
*trigger* is an artifact, but the behaviour is real: the axios interceptor
toasts a 5xx on a session probe the page does not need. Left alone because the
fix belongs in the interceptor's error policy and deserves its own change.

## Still not covered

- **Real iOS/Android hardware.** Unchanged. WebKit here is Playwright's engine
  on macOS, not Safari on a phone.
- **The GPU-compositing flicker check.** Unchanged — reproduces only on real
  hardware.
- **The 12 auth-gated routes' tab order.** This pass walked public routes only.
  The 2026-07-27 mobile pass showed these can be reached with the API mocked at
  the network layer (`serviceWorkers: 'block'` required); doing the same for a
  keyboard walk is the obvious next step.
- **A real screen reader.** Landmarks and accessible names are now correct by
  audit, but nothing was listened to with VoiceOver or NVDA.
