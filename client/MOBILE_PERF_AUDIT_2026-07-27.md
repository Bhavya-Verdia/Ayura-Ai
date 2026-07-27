# Mobile Speed / Reliability / Smoothness Pass — 2026-07-27

Goal: make the UI faster, more reliable and smoother **on phones**, without
trading away visual quality. Every change here is either free (removes work the
GPU was doing for no visible benefit) or fixes an outright bug. **No design,
colour, layer or motion was removed** — the mobile visual-parity decision
(phones get the exact desktop look) is intact.

Scope: `client/` only. 26 files changed. Lint clean, production build clean,
initial-path JS unchanged at 197.0 KB gzip (budget 250 KB).

---

## TL;DR

| | |
|---|---|
| Live `filter: blur()` layers removed | **12 → 0** (verified at runtime) |
| `will-change` layer hints removed | **67 → 0** on ParticleField pages (verified at runtime) |
| Real bugs found and fixed | **6** (3 of them user-visible) |
| Dead scroll removed from short in-app pages | 205 → 99 px (`/notifications`) |
| Chat: outer-page scroll eliminated | 1179 → **0 px** (transcript scrolls instead) |
| Route-change latency (perceived) | 0.28 s + 0.28 s → 0.10 s + 0.24 s |

The public/marketing pages were already in good shape — they measured 58–60 fps
scroll under 4× CPU throttling *before* this pass. The problems were
concentrated in the **authenticated app shell**, the **Chat** screen, and the
**onboarding** flow.

---

## Method

- Production build (`npm run build` → `vite preview`), not dev.
- Emulated Pixel 5 (393 px, touch, DPR 2.75) via Playwright, **4× CPU
  throttling** to stand in for a mid-range phone.
- Measured per route: document overflow, horizontal overflow, scripted-scroll
  frame rate, long tasks, and a full computed-style sweep counting
  `will-change` / running animations / `filter: blur` / `backdrop-filter`.
- Baseline captured by stashing the changes and rebuilding, so before/after
  numbers come from two real builds of the same tree.

**Honest limits of the measurement.** Two things below could not be measured in
headless emulation and are marked accordingly:

1. Headless browsers have **no collapsing URL bar**, so `100vh`, `100dvh` and
   `innerHeight` all resolve to the same number. The viewport-unit fixes are
   correct per spec and visible in the built CSS, but their benefit only
   materialises on a real device. **Verify on a phone.**
   (Playwright's WebKit is also not iOS Safari — same engine family, different
   compositor, no real touch input or GPU.)
2. ~~The app shell is auth-gated and no backend was running~~ — **closed.** The
   12 auth-gated routes were subsequently walked on both engines with the API
   mocked at the network layer (`ctx.route('**/api/**')`), so no backend and no
   database were involved and **production Atlas was never touched**. This
   renders the real React app, real CSS and the real MainLayout shell, which is
   exactly what this pass changed. It is what surfaced bug #5.
   Result: **24/24 route-loads render, 0 app errors, 0 horizontal overflow,
   `overscroll-behavior: contain` confirmed applied on every one.**
   Still unmocked: the chat WebSocket, so live streaming (the memoised
   `ChatMessage` and the instant-scroll behaviour) is verified by construction,
   not observed.

   Harness note: `serviceWorkers: 'block'` is required. Without it the PWA
   service worker takes over after the first navigation and WebKit bypasses
   Playwright's route interception, which silently served the login page instead
   of the route under test. The resulting "SW registration error" in the logs is
   caused by that blocking, not by the app.

Everything else in this report is a measured before/after.

---

## P0 — Real bugs

### 1. The Chat scroll-to-bottom button had no CSS at all

`.chat-scroll-fab` is rendered as a direct child of `.chat-canvas`, which is
`display: flex; flex-direction: column`. It had **zero style rules anywhere in
the codebase** — no `position`, so it was not an overlay: it laid out as a
normal flex item wedged between the transcript and the composer.

Effect on a phone: scrolling up in a conversation made an unstyled default
browser button appear in the message flow and **shrink the transcript**, then
disappear when you scrolled back down. `.chat-copy-btn` was unstyled too — a
grey default button under every AI reply.

**Fix:** proper styles for both, plus the action chips (which were inline
styles). `.chat-scroll-fab` is now `position: absolute` as intended, 44 × 44 on
mobile.
`src/pages/Chat.css`, `src/pages/Chat.jsx`

### 2. Streaming a chat reply re-parsed the markdown of every message

Every WebSocket chunk called `setMessages` with a new array. The message list
was rendered inline, so **each chunk re-ran the full remark/micromark markdown
pipeline over the entire conversation** — cost proportional to history length,
many times per second, on the weakest device.

**Fix:** extracted `ChatMessage` as a `React.memo` component keyed on the
message object. Only the last message's identity changes per chunk, so the work
is now confined to the one bubble being written. `copyMessage` is `useCallback`'d
so the memo isn't defeated by a fresh function each render.
`src/pages/Chat.jsx`

### 3. Auto-scroll restarted a smooth-scroll animation on every chunk

`scrollIntoView({ behavior: 'smooth' })` ran per chunk. A smooth scroll that is
re-triggered several times a second never settles — it reads as the transcript
vibrating, and it fights the user's own scrolling.

It was also the wrong element: `scrollIntoView` walks up and scrolls **every**
ancestor scroller, including the app shell's, so it could yank the whole page.

**Fix:** scroll `historyRef` directly (contained to the transcript), instantly
while `isLoading`, smooth once the reply completes.
`src/pages/Chat.jsx`

### 4. Mobile drawer breakpoint was off by one pixel

CSS used `@media (max-width: 900px)` (inclusive); JS used `innerWidth < 900`
(exclusive). At exactly 900 px the CSS applied the mobile drawer + tab-bar rules
while JS still rendered the desktop sidebar.

**Fix:** the JS test is now the same media query the CSS uses.
`src/layouts/MainLayout.jsx`

---

### 5. Chat had no inner scrolling at all — the composer scrolled off-screen

Found only after finally rendering the auth-gated routes (see *Verification*
below). `.chat-page-root` sets `height: 100%`, but a percentage height resolves
only if **every** ancestor has a definite one — and `#main-content`,
PageWrapper's in-shell wrapper, sets no height. So it silently computed to
`auto`.

Consequence: the chat panel grew with the transcript instead of fitting the
screen. Measured `.chat-history`: `scrollHeight === clientHeight === 1881px` —
i.e. the transcript's `flex: 1; overflow-y: auto` never had a box to scroll
inside. The whole page scrolled in the app shell instead, so on a long
conversation **the composer was pushed off the bottom of the screen** and you
had to scroll down to type. The scroll-to-bottom FAB never appeared either,
because the element it watches was never scrollable.

**Fix:** `#main-content:has(> .chat-page-root) { height: 100%; }` — scoped with
`:has()` so only the chat route's wrapper is constrained and every other
in-shell page still grows naturally.

Measured after: `.chat-history` clientHeight 1881 → **417px** (now genuinely
scrollable), outer shell scroll on `/chat` **1139px → 0px** on both engines,
scroll FAB present at 44×44 `position: absolute`.

While there: the mobile header was eating ~45% of a 662px screen. Trimming the
oversized title/icon and dropping the first-run subtitle took the visible
transcript from 370px to **417px**.

### 6. The browserslist target promised support the CSS could not deliver

`vite.config.js` declared `iOS >= 14, Safari >= 14`. That was fiction. The
shipped CSS requires `color-mix()` (Safari **16.2** — `--ayura-accent-soft`,
button hovers) and `@property` (Safari **16.4** — the animated gradient angle).
On iOS 14/15 those declarations are simply invalid.

This mattered more after the viewport-unit work, because `dvh` (Safari 15.4)
became load-bearing: `.dash-root` / `.dash-main-container` use it for **height**,
and a dropped height doesn't degrade — the shell's flex column collapses and the
app-shell layout goes with it.

**Two fixes, both needed:**

**(a) `@supports`, not duplicate declarations.** The obvious fallback —
`min-height: 100vh; min-height: 100dvh;` — was tried first and **does not
survive this build**: lightningcss collapses the pair to the last declaration,
the same behaviour `vite.config.js` already documents for `backdrop-filter`, and
it does so even with iOS 14 explicitly in the target list. A separate rule block
survives:

```css
.dash-root { height: 100vh; }
@supports (height: 100dvh) { .dash-root { height: 100dvh; } }
```

Applied to all 9 viewport-unit rules. Inline `style={{ minHeight: '100dvh' }}`
cannot express this at all (a JS object has one key per property), so the four
inline cases — including MainLayout's load-bearing shell height — moved to two
new utility classes, `.fill-viewport` and `.fill-viewport-h`.

**(b) An honest target: `>= 16.4`.** The first version where everything
load-bearing works. Two features ship newer than the floor on purpose, because
they degrade to "no optimisation" rather than a broken layout:
`content-visibility` (Safari 18) and `text-wrap` (Safari 17.5).

One trap worth recording: `defaults` **alone** resolves to iOS 18.5+, and at that
floor lightningcss stops emitting `-webkit-backdrop-filter` — silently undoing
the Chrome/Safari glass fix this config exists to protect. The query needs
explicit `>= 16.4` union clauses to pull 16.4→current back in.

**Verified in the built CSS:** all 9 `@supports` blocks survive minification,
both the `100vh` base and the `dvh` upgrade are present, and
`-webkit-backdrop-filter` is still emitted for all 38 `backdrop-filter`
declarations. Re-checked on WebKit and Chromium: no errors, no overflow,
`.fill-viewport-h` resolves to exactly the viewport height on both.

`vite.config.js`, `index.css`, `App.jsx`, `MainLayout.jsx`,
`GoogleCallback.jsx`, `GithubCallback.jsx`, + 6 page stylesheets

---

## P1 — GPU cost removed, zero visual change

### 7. Twelve full-screen `filter: blur()` layers → soft gradients

Almost every app page painted decorative "orbs": `position: fixed`,
`50vw`-scale, with `filter: blur(80–120px)` on top. A blurred fixed element is a
viewport-sized GPU texture that re-rasterizes whenever the layer is invalidated
— including on every URL-bar move during scroll. This is the same cost pattern
that `VitalBackground` was rebuilt to eliminate in the 2026-07 flicker fix; the
per-page orbs were simply never included in that pass.

Several were pure waste: `.da-orb`, `.notfound-orb-*` and `.onb-orb-*` **already
painted a radial gradient** and then blurred it — re-blurring an image that was
already soft, at full texture cost.

The worst was `.onb-orb-a/b`: `filter: blur(100px)` on an element with a running
20 s `transform` animation — a filtered ~600 px texture re-rasterized every
frame, forever, on the onboarding screen every new mobile user sees first.

**Fix:** the blur is expressed as gradient falloff instead (the technique
already documented in `index.css`: *the blur of a soft gradient IS a bigger soft
gradient*). Element sizes grew ~25 % to reproduce the blur's spread. The
onboarding drift animation is kept — without the filter it is now a pure
compositor transform.

Measured: `filter: blur` elements **12 → 0**. Verified visually on mobile
screenshots — the glows still read as soft light, no hard-edged discs.

`Progress.css`, `Remedies.css`, `Reminders.css`, `Notifications.css`,
`CheckIn.css`, `Settings.css`, `Community.css`, `InteractionChecker.css`,
`DoshaQuiz.css`, `NotFound.css`, `Onboarding.css`

### 8. `will-change` on up to 167 elements at once

`.particle-dot, .particle-orb { will-change: transform, opacity }`.
`ParticleField` mounts up to 167 of these (160 dots + 7 orbs) on Onboarding,
Settings, Dosha Quiz, Admin and Verify-Email. `will-change` is an instruction to
allocate a compositor layer **up front and hold it for the page's lifetime** —
167 of them, on the device with the least GPU memory.

It also bought nothing: every one of those elements has a running `transform`
animation, which the browser composites on its own regardless. The hint only
mattered in the window before the animation started.

Measured on `/verify-email`: elements with `will-change` **67 → 0**.
`src/index.css`

---

## P2 — Scroll correctness and perceived latency

### 9. Short in-app pages had dead scroll under them

**Correction to an earlier draft of this report,** which claimed ~200–300 px on
*every* screen. Measuring the real routes showed that is too broad: the fix only
bites where the page root's `min-height` is the binding constraint, i.e. on
short pages. On tall ones (Settings, Dashboard) content already exceeds the
viewport and the change is a no-op. Measured, Chromium/Pixel 5:

| Route | Before | After |
|---|---|---|
| `/notifications` | 205 px | **99 px** |
| `/community` | 205 px | **136 px** |
| `/chat` | 1179 px | **0 px** (via the fix above) |
| `/settings`, `/dashboard`, `/progress`, … | unchanged | unchanged |

Add the URL-bar delta on real hardware — headless resolves `100vh` and `100dvh`
identically, so the emulator only shows the padding component of the bug.

`100vh` is the **large** viewport — the height the page would have with the
mobile URL bar hidden. Nine app pages set `min-height: 100vh` on their root
while sitting **inside** MainLayout's scroller, which is `100dvh` minus the
56 px mobile top bar, with 140 px of bottom padding clearing the tab bar and FAB.

So every screen was guaranteed roughly `(100vh − 100dvh) + 56 + 140` px taller
than its own scroller. Short pages — an empty Notifications list, Check-In —
scrolled for no reason, and every page rubber-banded into dead space.

**Fix, by position in the tree:**

| Where | Was | Now | Why |
|---|---|---|---|
| Inside the app shell (9 page roots) | `100vh` | `min-height: 100%` | resolves against the scroller, not the viewport |
| Standalone (auth, onboarding, 404, callbacks, error boundary, loading overlay, `body`/`#root`) | `100vh` | `100dvh` | tracks the URL bar |
| Landing hero | `100vh` | `100svh` | always fully visible **and** never reflows mid-scroll (`dvh` would re-lay-out the hero every time the bar animates) |
| `.dash-root` | `100vh` / `100vw` | `100dvh` / `100%` | `100vw` also causes desktop scrollbar-gutter overflow |
| `.pref-modal-overlay` | `100vw`/`100vh` | `inset: 0` | the modal ran taller than the screen, its centred card partly under the URL bar |

The convention is now written down under **"App page roots"** in `index.css` so
it doesn't drift back.

### 10. Scroll chaining / accidental pull-to-refresh

Only `body` had `overscroll-behavior`. The three inner scrollers didn't, so a
flick past the end of any of them chained into the document — on Android that is
what fires pull-to-refresh mid-scroll; on iOS it is the whole-page rubber-band
under the fixed tab bar.

**Fix:** `overscroll-behavior: contain` on the app-shell scroller, the chat
transcript, and the mobile drawer.

### 11. The mobile drawer couldn't scroll

`.dash-sidebar.mobile` lists 12 nav items plus a profile card and sign-out, with
no scroller of its own — on a small phone (and any phone in landscape) the
bottom items were simply unreachable. Added `overflow-y: auto`.

### 12. `resize` listener ran on every scroll frame on Android

MainLayout tracked the breakpoint with a `resize` listener. Android fires
`resize` on **every URL-bar show/hide**, i.e. continuously while scrolling — so
the handler did a layout read (`innerWidth`) and a `setState` on the whole shell
mid-scroll. Replaced with a `matchMedia` change listener, which fires only when
the breakpoint is actually crossed.

### 13. Route changes felt slow

`AnimatePresence mode="wait"` holds the incoming route until the outgoing one
finishes exiting, so a tab tap cost 0.28 s exit **plus** 0.28 s enter. On a phone
the tap is the only feedback you get, so total latency matters more than the
outgoing flourish. The exit is now a 0.10 s fade with no y-drift; the entrance is
0.24 s.

### 14. Chat wasted ~76 px of a phone screen

The shell reserves 140 px at the end of the scroller for the tab bar **and** the
floating feedback FAB. But `FeedbackWidget.css` already hides that FAB on Chat —
and Chat isn't a scrolling document, it's a fixed-height panel with its own inner
scroller. The reservation only shrank the message area and floated the composer
above the tab bar. Chat now reserves the tab bar's own height and nothing more.
Chat's mobile padding was also tightened and the empty-state suggestion grid
dropped to one column (two 0.8 rem cards side by side wrapped to 3–4 lines each).

---

## Measured before / after

Emulated Pixel 5, 4× CPU throttle, production build:

| Route | Scroll FPS | `filter: blur` | `will-change` | h-overflow |
|---|---|---|---|---|
| `/` | 58 → 58 | 0 → 0 | 1 → 1 | 0 → 0 |
| `/verify-email` | 60 → 60 | 0 → 0 | **67 → 0** | 0 → 0 |
| `/dosha-test` | 60 → 60 | 0 → 0 | 0 → 0 | 0 → 0 |
| `/login` | 60 → 60 | 0 → 0 | 1 → 1 | 0 → 0 |
| `/404` | 60 → 60 | **2 → 0** | 0 → 0 | 0 → 0 |

Cross-engine check (WebKit/iPhone 13 vs Chromium/Pixel 5, 6 public routes):
**0 page errors and 0 horizontal overflow on both engines**, before and after.
The only divergence is `/login` scrolling 19 px on WebKit vs 0 on Chromium.

Public pages were already smooth, and this pass did not make them measurably
smoother — that is the honest result. Their value here is as a regression check:
nothing got worse, no new errors, no horizontal overflow. The changes that
matter are on the routes this harness cannot reach.

Bundle: initial-path JS unchanged at **197.0 KB gzip**. No new dependencies.

---

## Deliberately NOT changed

- **The grain overlay** (`NoiseOverlay`, `position: fixed; inset: 0; z-index: 9999`)
  is a full-screen composited layer over everything, at 2.4 % opacity. Dropping
  it on mobile would remove one screen-sized layer from every frame — but it is
  a visual-parity decision, not a bug, and parity was your explicit call. Flagging
  it as an available lever, not taking it.
- **`content-visibility: auto` on in-app lists** (notifications, reminders,
  community). It helps with hundreds of items; these lists are tens, and a wrong
  `contain-intrinsic-size` causes scroll-anchoring jitter. Not worth the risk at
  current list sizes.
- **Rewriting `ParticleField` onto a canvas.** 167 animated DOM nodes is a lot,
  but they are tiny; with `will-change` gone the remaining cost is likely
  acceptable. This is the next lever if onboarding still feels heavy on a real
  device — it would be a like-for-like visual port, not a reduction.
- **Lenis** is already correctly disabled on touch devices.
- **The 16 px input floor** (iOS focus-zoom) is already in place.
- **`backdrop-filter`** is already tiered down on mobile, keeping true blur only
  where sharp content actually scrolls behind glass.

---

## Verify on a real phone

The four items below are the ones the emulator cannot confirm:

1. Open Check-In or an empty Notifications list — it should **not** scroll at all.
2. Scroll to the bottom of any app page and keep flicking — no pull-to-refresh,
   no whole-page bounce.
3. Open the nav drawer in landscape — Settings and Sign out should be reachable.
4. Send a chat message and watch it stream — the transcript should track the
   text steadily, with no vibration, and the scroll-to-bottom button should be a
   round floating pill, not a grey inline button.
