# Launch-Readiness Frontend Audit — 2026-07-27

Full UI/UX audit of the web app ahead of startup launch: every route, both themes,
desktop + mobile, all 7 plan views, against a **live local stack** (real backend,
real generated plans) on the **production build** (`vite preview`, not dev).

**Verdict: strong, with 2 launch-blocking bugs.** The app is measurably solid —
zero JS errors, zero failed requests, zero horizontal overflow anywhere, and every
plan view renders its designed UI in both themes. But **Community is unusable in
light mode** and the **Remedies page is permanently empty**. Both are pre-existing
(neither is from the 2026-07-26 ambient-background commit).

> ## ✅ ALL ITEMS BELOW ARE FIXED (2026-07-27)
> Every P0, P1 and P2 item in this report has been resolved and re-verified.
> See **[Resolution](#resolution--all-items-fixed)** at the end for the measured
> before/after and the full file list.

---

## Method

| | |
|---|---|
| Build | production (`npm run build` → `vite preview`), not dev — no HMR artefacts |
| Backend | live local API, isolated mongo on :27099 (prod Atlas untouched) |
| Data | onboarded user + **all 7 plans generated** + community posts + a second un-onboarded user for `/onboarding` |
| Coverage | 20 routes × 2 themes × 2 viewports = **80 page-loads**, + 12 logged-out auth loads, + 14 plan-view loads |
| Viewports | desktop 1440×900, mobile 390×844 @2× (`isMobile`, `hasTouch`) |
| Checks | page errors, console errors, failed requests, horizontal overflow, tap-target size, missing alt, empty-render, WCAG contrast (computed), plus **human review of every screenshot** |

> **Method note:** the first mobile pass was invalid — viewport `width`/`height` were
> passed as top-level Playwright context options instead of nested under `viewport`,
> so it silently ran at the default 1280×720. It was corrected and re-run; all mobile
> numbers below come from a real 390 px viewport.

---

## What is clean (verified, not assumed)

- **0 JavaScript errors** and **0 console errors** across all 92 page-loads.
- **0 failed network requests.**
- **0 horizontal overflow** on any route, at 390 px or 1440 px. (This is usually the
  single biggest mobile defect class — it is genuinely absent.)
- **All 7 plan views** (routine, diet, yoga, gym, panchakarma, remedies, medicines)
  render their dedicated designed UI in both themes — no raw-JSON fallback, no
  overflow, no errors. Rich and readable; this is the strongest part of the product.
- **Dark mode: no contrast failures found.**
- **All images have `alt`.**
- Auth + onboarding render correctly logged-out in all four theme/viewport combos.
- Ambient background gating verified: present on desktop, **0 sprites at 390 px**.
- Empty/loading states are considered and on-brand throughout.

---

## P0 — Launch blocking

### 1. Community is unreadable in light mode

Post body text is **1.31:1** against the card. WCAG AA requires 4.5:1. Every post in
the feed is effectively invisible. The composer prompt is **1.27:1**.

Root cause: hardcoded dark-theme greys with no `[data-theme='light']` override.

| File:line | Selector | Colour | Contrast (light) |
|---|---|---|---|
| `pages/Community.css:99` | `.comm-post-content` | `#d4d4d8` | **1.31** ← post body |
| `pages/Community.css:55` | `.comm-create-prompt` | `#e4e4e7` | **1.27** |
| `pages/Community.css:34` | `.comm-subtitle` | `#a1a1aa` | 2.56 |
| `pages/Community.css:38` | `.comm-count-label` | `#a1a1aa` | 2.56 |
| `pages/Community.css:64` | `.comm-tip-pill` | `#a1a1aa` | 2.56 |
| `pages/Community.css:111` | post action buttons | `#a1a1aa` | 2.56 |

**Fix:** replace all six literals with the existing theme tokens — `var(--ayura-ink)`
for body/prompt, `var(--ayura-muted)` for secondary. Those tokens are already
theme-aware, so this is a token swap, not new CSS.

**Why every prior pass missed it:** the feed was empty in earlier audits, so the post
text never rendered; and the automated contrast probe skips elements sitting on a
gradient (it cannot resolve the effective background). Caught only by seeding real
posts and looking.

### 2. Remedies page is permanently empty

`/remedies` shows "No home remedies generated yet" even with a remedies plan
generated and present in history. Two independent faults, both must be fixed:

1. **Frontend** — `pages/Remedies.jsx:344` reads `res.data?.plan_data`, but
   `GET /api/plans/latest` returns the `PlanResponse` **directly**; there is no
   `plan_data` key. `data` is therefore always `{}` and the page can never render
   content from this endpoint, regardless of backend state.
2. **Data shape** — even once (1) is fixed, `/plans/latest` returns
   `home_remedies: null` and `medicines: null` for a per-feature plan. The remedies
   plan stores its content under `symptoms_addressed[]`, where each entry carries a
   `remedy` object. The page expects flat `home_remedies` / `medicines` arrays from
   the *holistic* plan shape.

**Fix:** read `res.data` directly, then map `symptoms_addressed[]` → the card list
(each entry already has `symptom_display`, `severity`, `remedy`,
`requires_practitioner`, `drug_interaction_warning`). Since the product's primary
flow is the **per-feature** endpoints, that shape is the one to support.

This is a whole navigation item that is dead for every user on the per-feature flow.

---

## P1 — Fix before launch

### 3. Remaining hardcoded dark-theme greys

`components/PlanViewer.css` lines **4070, 4125, 4170, 4991** use `#94a3b8`
(≈3.0:1 on the light surface — below the 4.5 AA threshold for body text). Same
token-swap fix. Lower severity than Community: these are secondary notes, not body
copy.

### 4. Light-mode selected chips fail AA

Black text on the deep-green fill: **3.48:1** (needs 4.5).

- `pages/HealthTimeline.css:133` — `.ht-filter-pill.active`
- `pages/Settings.css:162` and `pages/Onboarding.css:150` — `.onb-chip.selected`

Background is `#237045`. **Fix:** white text in light mode — the same override
pattern already applied to `.btn-primary`, `.lnd-cta-main`, `.chat-bubble.user`,
and `.chat-send-btn`. White on `#237045` clears AA comfortably.

### 5. Mobile hamburger is a 30×30 tap target

`pages/Dashboard.css:102` — `.dash-hamburger` has `padding: 4px`, giving a 30×30 hit
area. This is the **primary navigation control on every authed mobile page**. Apple
recommends 44×44 pt, Google 48×48 dp.

**Fix:** `padding: 11px` (→ 44×44) or `min-width/min-height: 44px`. Purely additive;
the icon does not move.

---

## P2 — Polish

### 6. Small tap targets failing WCAG 2.2 SC 2.5.8 (24×24)

Landing and `/dosha-test` footer links render **18–22 px tall** with a **15 px**
minimum gap — so they fail the spacing exception too (I measured it rather than
assuming). Also `/forgot-password` "Sign in →" (18 px), `/remedies` "Back to
dashboard" (19 px), `/terms` + `/privacy` "Back to Home" (24 px).

**Fix:** `padding: 6px 0` on footer link lists and the inline back-links.

### 7. CheckIn selects are 31 px tall on mobile

`Duration` and `Trend` selects. Under the 44 px comfort standard (above the WCAG
minimum). Bump to `min-height: 44px` at ≤900 px.

### 8. Ambient glyphs read stronger in light mode

On `/login`, `/register`, `/onboarding` the drifting Om/padmasana are noticeably more
assertive on the cream background than on dark. Not a defect — a taste call. If they
feel busy, drop `--peak` opacity ~20% under `[data-theme='light']`.

---

## Recommended order

1. **Community token swap** (6 lines) — restores a whole feature in light mode.
2. **Remedies data path** — restores a whole page.
3. Chip contrast + hamburger size — small, mechanical, real usability wins.
4. PlanViewer greys, tap-target padding, CheckIn selects.
5. Ambient light-mode opacity — optional.

Items 1, 3, 4 are token/padding changes with effectively no regression risk. Item 2
needs a data-shape mapping and should get a manual re-test with a generated
remedies plan.

---

## Still not covered

- **Real-device testing.** Everything here is headless Chromium. No real iOS, Android,
  or Safari/Firefox pass. Safari is the notable gap — it is the only engine where the
  `dvh`/`env(safe-area-inset-*)` handling is truly exercised.
- **The GPU-compositing flicker check**, which by prior investigation cannot be
  captured by screen recording *or* headless — it only ever reproduced on real
  hardware. Outstanding on the ambient background shipped 2026-07-26.
- **Keyboard-only and screen-reader navigation** were not exercised (focus ring and
  skip-link exist; actual tab-order was not walked).
- Load/perf was not re-measured this pass (last measured mobile Lighthouse ≈83).

---

# Resolution — all items fixed

Applied and re-verified against the running production build on 2026-07-27.
Verification is measured, not assumed: the contrast and route sweeps were re-run
end-to-end after the changes.

## Measured before → after

| Item | Before | After |
|---|---|---|
| Community post body (light) | **1.31:1** | **14.78:1** |
| Community composer prompt (light) | **1.27:1** | **14.78:1** |
| Community subtitle / time / tip pill | 2.56:1 | **5.52:1** |
| Timeline active filter pill | 3.48:1 | **6.04:1** |
| Settings / Onboarding selected chip | 3.48:1 | **6.04:1** |
| Remedies filter chip | 3.48:1 | **6.04:1** |
| Remedies page content | 0 cards (permanently empty) | **2 remedies + 7 medicines** |
| Mobile hamburger | 30×30 | **44×44** |
| CheckIn selects (mobile) | 31 px | **44 px** |
| Landing / DoshaTest footer links | 18–22 px | **29–30 px** |
| Nav "Dashboard" link | 21 px | **24 px** |
| "Sign in →" / "Back to dashboard" | 18 / 19 px | **24 / 44 px** |
| Community post actions | 15×19, 35×18 | **≥32×32** |

**App-wide contrast: 0 AA failures in either theme** (was 2 distinct, plus the
Community and Remedies failures that were hidden behind empty states).

**Route sweep: 74/80 page-loads fully clean**, up from 42/80. The 6 remaining
flags are all targets between 24 px and 32 px — they pass WCAG 2.2 SC 2.5.8
(24×24); the probe simply warns below 32 px.

Unchanged and still green: 0 JS errors, 0 console errors, 0 failed requests,
0 horizontal overflow, 10/10 e2e, bundle 196.7 KB (budget 250).

## Files changed

| File | Change |
|---|---|
| `pages/Community.css` | 7 hardcoded zinc greys → theme tokens; post-action tap targets ≥32 px |
| `pages/Remedies.jsx` | rewrote the data layer (history instead of `/plans/latest`) + adapters for both engine shapes |
| `pages/Remedies.css` | light override for `.rem-filter-chip.active`; back-link 44 px |
| `components/PlanViewer.css` | light-only overrides for 4 slate note/badge rules |
| `pages/HealthTimeline.css` | light override for `.ht-filter-pill.active` |
| `pages/Settings.css`, `pages/Onboarding.css` | light override for `.onb-chip.selected` |
| `pages/Dashboard.css` | hamburger → 44×44 via padding (icon does not move) |
| `components/VikritiCheckIn.css` | selects 44 px at ≤900 px only |
| `pages/Landing.css`, `pages/DoshaTest.css`, `pages/Legal.css`, `pages/Auth.css` | link tap targets |
| `components/AmbientMeditation.css` | `--peak-mult` damping for light theme |

## Implementation notes worth keeping

- **PlanViewer greys were fixed light-only.** The dark values are deliberately
  untouched — that file's cool tones are intentional data-viz encodings, and a
  previous pass caused a regression by grep-remapping them. Only
  `[data-theme='light']` overrides were added.
- **Remedies now reads `/plans/history`, not `/plans/latest`.** `/plans/latest`
  returns just the single newest plan, so even with the `plan_data` bug fixed, a
  user whose newest plan was (say) gym would still have seen an empty page. The
  page now picks the newest plan *of each relevant type*, and keeps the holistic
  flat-array shape as a fallback.
- **Ingredient objects are flattened to strings in the adapter.** The chips render
  `{ing}` directly, so passing the engine's `{item, amount, preparation}` object
  through would have crashed React with "Objects are not valid as a React child".
- **Ambient light-mode damping uses `--peak-mult`, not `--peak`.** `--peak` is set
  per-sprite as an inline style and inline always beats a stylesheet rule; the
  multiplier is inherited from the container instead.
- **Two bugs were only reachable after other fixes landed** — the Remedies filter
  chip and the Community post actions do not exist in the DOM while those surfaces
  render empty. Worth re-running the sweep after any fix that makes a dead surface
  live.

## Still not covered (unchanged)

Real iOS/Android/Safari hardware, the GPU-compositing flicker check, keyboard and
screen-reader tab-order, and a fresh Lighthouse run.
