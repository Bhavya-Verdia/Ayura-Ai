# Ayura AI — Pre-Launch QA Checklist

Status legend: ☐ todo · ✅ verified this session · ⚠️ needs your action / environment

Generated 2026-06-26, revised 2026-08-19. "verified this session" = exercised against a
live local stack (local MongoDB + backend + Playwright). It does **not** mean verified on
production infra.

---

## 1. Infrastructure & config (⚠️ — your environment, not verifiable from code)
- ⚠️ **MongoDB Atlas reachable from prod hosts** — the app fails hard if Mongo is down. Confirm the prod server IPs are in the Atlas **IP allowlist** (the dev sandbox was blocked by this).
- ⚠️ **Redis running** — required for the ARQ worker (reminders + holistic plan jobs) and rate limiting. Without it, reminders never fire and holistic generation falls back to in-process.
- ⚠️ **ARQ worker process running** (`arq worker.WorkerSettings`) — reminders + background plans depend on it. Confirm it's deployed and the cron `dispatch_due_reminders` ticks.
- ⚠️ **ChromaDB** reachable (or embedded path persisted) — RAG enrichment + citations context.
- ⚠️ **LLM keys** (`AZURE_OPENAI_API_KEY` / `GEMINI_API_KEY`) valid in prod — diet, dosha narrative, seasonal, meditation, chat, interaction explanations.
- ✅ **Email service — sending DNS repaired 2026-08-14.** Outbound goes through Resend
  (`smtp.resend.com`) as `noreply@ayuraai.in`, which needs three records. Two were broken:
  the SPF on `send.ayuraai.in` read literally `"v=spf1 include[...]nses.com ~all"` (a
  truncated paste, verified at byte level with `od -c`, not a display artifact), and the
  DKIM at `resend._domainkey` was absent. Both now correct and consistent across five
  resolvers including both authoritative servers: DKIM 218 chars, SPF
  `v=spf1 include:amazonses.com ~all`, MX unchanged.
  - ✅ **Verified end to end 2026-08-14**: register → `Verification email scheduled` →
    `[OK] Email sent … via smtp.resend.com:2465` → link clicked → account verified.
  - ⚠️ **Port 2465, not 465.** The droplet cannot reach 25/465/587 — DigitalOcean blocks
    outbound submission ports, verified from inside the api container. Sending was dead and
    silent because `smtplib` had no timeout: the blocked connect parked the background
    thread rather than raising, so registration logged "scheduled" and then nothing at all.
    There is now a 20s timeout, and `IMPLICIT_TLS_PORTS = {465, 2465}` because choosing the
    TLS mode on `port == 465` alone sends STARTTLS to 2465, which never answers.
    Regression: `tests/test_email_transport.py`.
  - **Resend's "verified" badge is a historical check, not live DNS** — it showed all three
    green while two were broken. Never accept it as evidence; query DNS.
  - **Hostinger's email tooling rewrites mail DNS.** Enabling its DKIM removed Resend's
    record the same day. Re-check both records after any hPanel email change.
  - Hostinger DNS is fronted by Cloudflare anycast (`172.64.x`), so a fresh record appears
    on some edge nodes before others — the same nameserver IP answered MISSING and present
    on consecutive queries for ~7 minutes. Sample repeatedly before concluding anything.
- ⚠️ **DNS is served by Hostinger on a 30-day trial.** `ayuraai.in` resolves via
  `solar/lunar.dns-parking.com`. The droplet is paid for separately, so if the trial lapses
  the server keeps running and the domain simply stops resolving — the site goes dark with
  nothing wrong on the host. Confirm whether the domain *registration* is also on the trial;
  moving DNS to a free permanent provider removes the dependency.
- ⚠️ `APP_ENV=production` set → confirms `validate_production_secrets()` passes (non-default `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_TOKEN`; `COOKIE_SECURE` + `SAMESITE=strict` auto-forced).
- ✅ App boots cleanly with all routes mounted (95 routes; both LLM clients init).
- ✅ DB index creation is migration-safe (partial OAuth-id indexes; drops legacy sparse).

## 2. Security & privacy (health/PII data) (☐)
- ☐ Confirm JWT in HTTP-only cookies only (no localStorage); refresh flow works on 401.
- ☐ Admin endpoints require `X-Admin-Token` (✅ confirmed in code: HMAC compare).
- ☐ GDPR: `/privacy/export` and `/privacy/account` (delete) work end-to-end; deletion cascades (timeline, plans, reminders, comments).
- ✅ Rate limits active on auth + sensitive plan endpoints in prod (needs Redis).
- ✅ **Rate-limit bypass fixed (2026-08-11).** nginx appended to the caller's
  `X-Forwarded-For` while the app read the *leftmost* entry, so rotating one header
  gave a fresh bucket per request — verified live against ayuraai.in (30 rotating
  requests, zero 429s). nginx now overwrites with `$remote_addr`; the app reads from
  the right (`TRUSTED_PROXY_HOPS`). Regression test: `test_abuse_limits.py`.
  **Re-verified on production after the rebuild**: 30 rotating-header requests now
  trip at 20 (20× 200 → 10× 429), and a 3-entry fake chain is still bucketed to the
  real peer. Note the nginx half needs an image **rebuild**, not a restart.
- ✅ Per-account login lockout added (was: IP rate limit only, which a distributed
  attacker sidesteps). `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`.
- ✅ Per-user daily LLM quotas added (`DAILY_PLAN_QUOTA` / `DAILY_CHAT_QUOTA`) —
  there was previously **no ceiling on billed LLM spend** for an authenticated
  account. Covers plan routes, holistic (billed ×6), meditation, interaction-check,
  and both chat paths incl. the WebSocket, which bypasses the HTTP middleware.
- ☐ Avatar upload: magic-byte validation + size cap (✅ in code).
- ☐ Penetration sanity: prompt-injection sanitization on chat/quiz inputs (✅ helpers exist).

## 3. Per-feature manual QA (run each in a browser against staging)
Auth & onboarding
- ✅ Multiple email/password signups succeed (was a launch-blocker — fixed).
- ☐ Google + GitHub OAuth round-trip.
- ✅ Email verification gate — an unverified account is refused at login (`POST /api/auth/login
  403`, observed), and the emailed link verifies the account. Whole flow exercised against
  production 2026-08-14 with a throwaway plus-address, which was then deleted through the
  same cascade `routes/privacy.py` uses.
- ✅ Onboarding free-text conditions normalize to canonical vocab (verified: "high blood pressure"→hypertension).

Assessment & plans
- ✅ Dosha assessment full pipeline (Prakriti/Vikriti/Agni/Ama/Ojas/Manasa) returns + persists; `agni_type` now exposed via API (was dropped — fixed).
- ☐ Clarify follow-up flow triggers on low-confidence/contradiction (fixed wiring — verify in UI).
- ☐ Generate each plan (gym/yoga/diet/routine/panchakarma/remedies/medicines) after setting preferences; confirm content + "Classical basis" footer renders.
- ☐ Holistic `/plans/generate` job polling (needs worker/Redis).
- ☐ **Yoga end-to-end on production** (shipped 2026-08-13, `031cfaa`): guided practice
  player runs a full session, bilateral poses announce both sides, week feedback generates
  week 2 with an explained adjustment, completion writes a timeline event. Covered by
  Playwright against stubbed routes; **not yet walked against prod**.
- ☐ **Gym end-to-end on production** (shipped 2026-08-18, `e6f1b4f`): set training style,
  days/week, equipment, muscle focus and a disliked movement in Preferences, then generate —
  confirm the split honours the requested days, the session opens with a canonical main lift
  at a plausible load, mobility work is not prescribed as a lift, the dislike is respected,
  and the four-week progression narrative matches the four weeks shown. Covered by the
  backend suite and the 4,950-plan sweep; **not yet walked against prod in a browser**.

Supporting features
- ✅ Timeline endpoint returns events (was missing entirely — built).
- ✅ Dashboard streak card reflects real progress logs (was stuck at 0 — fixed).
- ✅ Reminders create with browser timezone; ⚠️ confirm one actually **fires** at local time (needs worker running — only testable with Redis + ARQ).
- ✅ Notifications mark-read + delete + clear-all.
- ✅ Community post / comment / like / report (auto-hide at 3 flags).
- ✅ Interaction checker (metformin × fenugreek → warnings).
- ✅ Adverse-reaction report → timeline event; severe → re-assessment flag.
- ✅ Ritucharya seasonal card.
- ✅ Vaidya-handoff PDF includes clinical profile (2.7KB→9.2KB once assessed).

## 4. Clinical / BAMS validation (☐ — requires a licensed practitioner; I cannot certify)
- ☐ A registered BAMS vaidya reviews `server/data/golden/vaidya_reviewer_packet.md` and signs off.
- ☐ Spot-check the 157-entry medicine KB: dosages, anupana, contraindications, AFI references.
- ☐ Validate disease→dosha mappings + sample generated plans for 5–10 representative profiles.
- ☐ Confirm pregnancy/nursing gating excludes contraindicated medicines/poses/therapies.
- ☐ Confirm disclaimers appear on every plan + remedy + the PDF.
- ☐ **New surface as of 2026-08-12, live since 2026-08-13** — the yoga overhaul widened what
  needs review: 113 rewritten pose entries (instructions, benefits, Ayurvedic rationale),
  the `risk_tags` mechanism assignments on 70 of them, the raising of Headstand/Shoulderstand/
  Plow to `advanced`, and the new per-trimester pregnancy pools (T1 44 / T2 38 / T3 22 poses).
  None of it practitioner-reviewed. Unspecified pregnancy status is treated as third
  trimester, which is the safe reading but is itself a clinical judgement.
- ☐ **New surface as of 2026-08-19, live the same day** — the gym overhaul (PRs #12–#34) put
  the exercise library on the same footing as yoga, and it is the larger surface of the two:
  **902 exercises, of which 18 carry `contraindications_reviewed` and 884 do not.** Those 884
  have safety tags generated by rules, and inspecting roughly a dozen of those rules already
  turned up four faults (every barbell marked unsuitable for Pitta; maximal-effort
  conditioning carrying no cardiovascular tag while a dance class did; 13 foam-rolling entries
  filed as strength; two exercises existing twice with contradictory safety data). That hit
  rate is why the tags cannot be assumed sound.
  - The review is packaged as **`server/data/golden/vaidya_gym_packet.md`** — about a day for
    a physiotherapist, sports physician, or BAMS with exercise-prescription training. The
    reviewable unit is the **rule, not the row**: 242 tag rules across 42 mechanism groups, of
    which **116 are applied inconsistently** (a group tagged 3/13 means one of those two
    answers is wrong). They are sorted largest-group-first in `gym_mechanism_review.csv`, so
    stopping early stops on the least consequential ones.
  - ☐ **Four engineering decisions need a clinician to confirm or reverse** (packet, "Four
    decisions needing your confirmation"): the merged `Elliptical Trainer` keeping
    `pregnancy_safe: true`; `hypertension` used as the age proxy for cardiovascular strain at
    60+; impact work withheld at obese BMI, and whether that should extend to `overweight`;
    and **prenatal training declared unsupported** — the plan generates but carries a notice
    to work with a prenatal-qualified instructor.
  - ☐ **Cardiovascular tagging deserves a pass of its own** even if the sampled rules look
    fine: three separate faults have been found in it and it is the mechanism with the worst
    consequences.
  - What engineering *can* certify is the programming, not the tags: a 4,950-plan sweep across
    eleven profile types confirms no exercise carrying a contraindication ever reaches a
    practitioner who declared that condition. That is gating, not clinical correctness.
  - Regenerate the packet after any KB change: `python scripts/build_gym_review_packet.py`
    (guarded by `tests/test_gym_kb_integrity.py`, so it cannot drift from the library).

## 5. Observability & ops
- ✅ **Sentry live (set + deployed + verified 2026-08-11).** `SENTRY_DSN` (Python, shared by
  api + worker) and `VITE_SENTRY_DSN` (a separate React project — Sentry projects are
  per-platform, one DSN each) are in the root `.env`. Org is on the **EU/DE** region
  (`ingest.de.sentry.io`). Confirmed present in the served bundle 2026-08-13.
- ✅ **PostHog live (same date).** `VITE_POSTHOG_KEY` + `VITE_POSTHOG_HOST`, EU region —
  proven rather than assumed by POSTing the key to `{eu,us}.i.posthog.com/decide/?v=3`
  (EU 200, US 401). That probe reads config and writes no event, so it is the safe way to
  settle a region question; a mismatch drops every event **silently**, with nothing logged.
- ⚠️ **Local dev pollutes both projects unless you stop it.** Vite's `envDir` is the repo
  root, so `npm run dev` and every Playwright run load the production keys. A gitignored
  root `.env.local` now blanks `VITE_SENTRY_DSN` and sets the CI stub `VITE_POSTHOG_KEY`
  (blank breaks the funnel specs — they need the SDK switched on). `deploy.sh` excludes it
  from the rsync. **If you clone fresh, recreate it before running the app locally.**
- ✅ `/api/health` + `/api/ready` live and green on production (mongodb + chromadb connected).
- ☐ Structured logs shipping; metrics endpoint (`/api/health/metrics`, admin-gated) reachable.
- ☐ Backups configured on Atlas.
- ✅ **RAG corpus rebuilt on production 2026-08-13.** `build_vectors.py` now reads the real
  113-pose `yoga_poses.json` (was: the 10-entry legacy `yoga_plans.json`, so the yoga
  enricher's semantic context described poses the engine no longer served — and every one
  of those ten embedded as `"Yoga pose: None."`, because the legacy file keys the name as
  `name_english`, not `name`). `ayurveda_knowledge` 146 → 474 chunks, 338 of them named
  poses. Regression: `tests/test_vector_docs.py`. **Re-run the seeder after any KB edit** —
  nothing detects the drift on its own.
- ⚠️ **The seeder takes RAG down while it runs**, and on a cold container it used to take
  it down *permanently*: it deletes each collection before add() first pulls the ONNX
  model, so a download failure left `ayurveda_knowledge` empty (this happened, and was
  recovered by re-running). It now embeds a probe string before touching anything and
  exits rather than deleting. Still: reseed deliberately, and check counts afterwards.
- ✅ **Embedding model baked into the API image 2026-08-13.** Every fresh container used to
  have all four gunicorn workers download the same 79 MB ONNX archive concurrently and
  unpack over each other — `/api/health` unreachable for ~15s, then `INVALID_PROTOBUF` from
  each worker. It logs as a WARNING and the app stays up, so the symptom is RAG silently
  returning nothing. **After any deploy that rebuilds the api image, check
  `docker compose logs api | grep -i warm-up` is empty.**

## 6. Legal & compliance (revised 2026-08-04)
- ✅ Privacy Policy rewritten for the DPDP Act 2023 + IT Rules 2021: grievance officer
  contact, retention periods, cookie/analytics disclosure, breach notification, 18+ age
  gate, nomination right, DPB complaint route.
- ✅ Terms rewritten: no-practitioner-relationship clause, acceptable use, IP, termination,
  indemnity, governing law.
- ✅ Both pages now carry a hand-maintained `LAST_UPDATED` constant. They previously
  rendered `new Date()`, so each claimed same-day revision in perpetuity.
- ✅ **`privacy@ayuraai.in` is live (2026-08-14)** — the grievance contact published in both
  legal documents now accepts mail. Hostinger Business Email mailbox; apex MX already
  pointed there. Verified by SMTP probe rather than assumption: both `mx1` and
  `mx2.hostinger.com` answer `250` for the address and `550` for a made-up one, so the
  accept is real and not a catch-all. Re-check with an RCPT probe after any MX change.
  ⚠️ **On a 30-day Hostinger trial** — the mailbox *and* DNS for the whole domain go with it
  if the trial lapses. Decide before the date.
- ✅ **Jurisdiction confirmed 2026-08-14** — `JURISDICTION` in `client/src/pages/Terms.jsx`
  is now `Udaipur, Rajasthan`, the operator's actual location, and Terms' `LAST_UPDATED` was
  bumped with it. Privacy was left at its own date, since that document did not change.
  Revisit if the business incorporates with a registered office elsewhere: the clause should
  follow the registered office, not the founder.
- ☐ No legal entity named in either document (not incorporated yet — revisit on registration).

## 7. Known gaps / not built
- ✅ **Third-party pose imagery removed 2026-08-13.** All 64 images traced back to Pocket
  Yoga's artwork — 32 hotlinked from pocketyoga.com, 32 via the third-party `yoga-api`
  Cloudinary account that had copied the same assets — served from a public product with
  commercial intent. Cleared from the KB and from `scripts/generate_new_poses.py`, which
  would otherwise reintroduce them. Guard: `test_no_pose_hotlinks_third_party_imagery`
  asserts provenance, not emptiness, so licensed or self-hosted URLs pass.
- ☐ **Pose imagery is uniformly schematic, and drawn figures are switched OFF.** All 113
  poses render the category diagram in `PoseFigure.jsx`, so 15 backbends share one drawing.
  Plain, but consistent.

  A joint-coordinate figure system was built and shipped for 12 poses on 2026-08-13, then
  rolled back the same day (`USE_DRAWN_FIGURES = false`). Reason: 12 of 113 is ~27% of the
  pose cards in a session — a day's list showed five drawn figures among eleven category
  diagrams, and a partly-illustrated list reads as broken where a uniformly plain one reads
  as a style. **The "~36% of slots" figure used to justify shipping 12 counted repetition**
  (Savasana is in every session), so it flattered the coverage against what a user actually
  scrolls past. Per-card coverage is the number that matters.

  Everything to re-enable is intact and tested — joint data in `yoga_poses.json`, renderer
  in `poseSkeleton.js`, validation in `test_yoga_practice_quality.py`, and the engine still
  sends `figure` with every pose. Turning it on needs ~60-80 poses drawn (87-95% of cards),
  not 12.

  **Recommendation: commission the top 40 poses AFTER clinical sign-off**, as single-colour
  SVG on one viewbox so they inherit the theme tokens. Imagery is polish; section 4 is the
  gate, and a reviewer who reclassifies or drops poses would mean re-briefing.
- Plan content is English-only. The yoga UI chrome and player are translated (68 Hindi
  strings) but pose names, instructions, rationale and all LLM narrative arrive from the
  backend in English regardless of the selected language. Same for the dosha result copy.
- No monetisation: zero payment integration anywhere in the codebase.
- Onboarding symptom set unified with the engine, but verify plan output reflects it for a real profile.
- Reminder firing is only testable with Redis + ARQ running (couldn't verify in sandbox).
- Dependency drift: chromadb 0.6.3→1.5.9, bcrypt 4.2→5.0, cryptography 48→50. Not urgent; needs a patch cadence.

---

### Verified green 2026-08-19
- Backend: **861 unit/integration tests passing**, 0 failures (379 on 2026-08-13, 260 at the
  2026-08-04 audit). The suite now takes 5m31s — the gym profile sweep dominates it.
- Frontend: **lint clean**, build clean, initial-path JS **199.2 KB** gzip against the 250 KB
  budget.
- Production live and healthy at https://ayuraai.in (`/api/health` reports mongo + chromadb
  connected).
- The 28 gym commits are deployed and **verified by served artifact**, not by the deploy
  workflow's own ✅: the locally built `PreferencesModal-lOAbW4pm.js` is hash-identical to the
  chunk production serves, and it contains the `"burpees, deadlift, jump rope"` placeholder
  that only exists after `gym-likes-dislikes`. The *entry* chunk hash differs from a local
  build and that is expected — prod injects `VITE_SENTRY_DSN` / `VITE_POSTHOG_KEY`, so compare
  a chunk with no env-dependent content.

### Verified green 2026-08-13
- Backend: **379 unit/integration tests passing** (260 at the 2026-08-04 audit).
- Frontend: **lint clean**, **Playwright E2E 20 passed / 5 skipped / 0 failed** (the skips
  need a live backend), initial JS **199.4 KB** gzip against a 250 KB budget.
- Production live and healthy at https://ayuraai.in (`/api/health`, `/api/ready` both green).
- The nine yoga commits are deployed and **verified by image timestamps + served artifact**,
  not by `deploy.sh`'s own ✅: served entry hashes match the local build, the prod KB reports
  113 poses / 70 risk-tagged, and `POST /api/practice/session` answers 401 (route exists,
  auth-gated) rather than 404. **Never accept the script's success line as evidence** — it
  has printed it over a deploy that shipped nothing.

### The one item no amount of testing closes
Section 4 (clinical/BAMS validation) remains entirely unchecked, and each feature pass has
widened it rather than narrowed it. The app ships dosage, anupana and contraindication
guidance to the public, and no registered practitioner has reviewed the medicine KB, the
disease→dosha mappings, the pregnancy gating, the 113 rewritten pose entries, or the safety
tags on 884 of the 902 exercises. The medical disclaimer in the Terms mitigates but does not
substitute for that review.

Three packets are ready and waiting on a human: `vaidya_reviewer_packet.md` (medicines),
the yoga surface described above, and `vaidya_gym_packet.md` (~1 day, rule-level). Nothing
further in this repository moves that item.
