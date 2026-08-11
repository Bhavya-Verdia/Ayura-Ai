# Ayura AI — Pre-Launch QA Checklist

Status legend: ☐ todo · ✅ verified this session · ⚠️ needs your action / environment

Generated 2026-06-26, revised 2026-08-04. "verified this session" = exercised against a
live local stack (local MongoDB + backend + Playwright). It does **not** mean verified on
production infra.

---

## 1. Infrastructure & config (⚠️ — your environment, not verifiable from code)
- ⚠️ **MongoDB Atlas reachable from prod hosts** — the app fails hard if Mongo is down. Confirm the prod server IPs are in the Atlas **IP allowlist** (the dev sandbox was blocked by this).
- ⚠️ **Redis running** — required for the ARQ worker (reminders + holistic plan jobs) and rate limiting. Without it, reminders never fire and holistic generation falls back to in-process.
- ⚠️ **ARQ worker process running** (`arq worker.WorkerSettings`) — reminders + background plans depend on it. Confirm it's deployed and the cron `dispatch_due_reminders` ticks.
- ⚠️ **ChromaDB** reachable (or embedded path persisted) — RAG enrichment + citations context.
- ⚠️ **LLM keys** (`AZURE_OPENAI_API_KEY` / `GEMINI_API_KEY`) valid in prod — diet, dosha narrative, seasonal, meditation, chat, interaction explanations.
- ⚠️ **Email service** configured — verification emails + reminder/notification email delivery (`email_notifications` pref respected).
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
- ☐ Email verification gate (plan generation blocked until verified).
- ✅ Onboarding free-text conditions normalize to canonical vocab (verified: "high blood pressure"→hypertension).

Assessment & plans
- ✅ Dosha assessment full pipeline (Prakriti/Vikriti/Agni/Ama/Ojas/Manasa) returns + persists; `agni_type` now exposed via API (was dropped — fixed).
- ☐ Clarify follow-up flow triggers on low-confidence/contradiction (fixed wiring — verify in UI).
- ☐ Generate each plan (gym/yoga/diet/routine/panchakarma/remedies/medicines) after setting preferences; confirm content + "Classical basis" footer renders.
- ☐ Holistic `/plans/generate` job polling (needs worker/Redis).

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

## 5. Observability & ops
- ⚠️ **Sentry DSN NOT set** — integration is wired in `client/src/main.jsx`, `server/main.py`
  and `worker.py`, all correctly gated on a DSN, but no `SENTRY_DSN` / `VITE_SENTRY_DSN`
  exists in `.env`. **Production errors are currently reported nowhere.** Add both keys
  (see `.env.example`) and rebuild the web image — VITE_* vars bake at build time.
- ⚠️ **PostHog key NOT set** — analytics wired 2026-08-04 (`client/src/lib/analytics.js`),
  inert until `VITE_POSTHOG_KEY` is set. Confirm the host region matches the project
  (`eu.` vs `us.`) or events are silently dropped. Rebuild the web image after setting.
- ✅ `/api/health` + `/api/ready` live and green on production (mongodb + chromadb connected).
- ☐ Structured logs shipping; metrics endpoint (`/api/health/metrics`, admin-gated) reachable.
- ☐ Backups configured on Atlas.

## 6. Legal & compliance (revised 2026-08-04)
- ✅ Privacy Policy rewritten for the DPDP Act 2023 + IT Rules 2021: grievance officer
  contact, retention periods, cookie/analytics disclosure, breach notification, 18+ age
  gate, nomination right, DPB complaint route.
- ✅ Terms rewritten: no-practitioner-relationship clause, acceptable use, IP, termination,
  indemnity, governing law.
- ✅ Both pages now carry a hand-maintained `LAST_UPDATED` constant. They previously
  rendered `new Date()`, so each claimed same-day revision in perpetuity.
- ⚠️ **`privacy@ayuraai.in` does not exist yet** — both documents publish it as the
  grievance contact. Set up forwarding (Cloudflare Email Routing is free) *before*
  announcing, or grievance mail bounces.
- ⚠️ **Jurisdiction is a placeholder** — `JURISDICTION` in `client/src/pages/Terms.jsx`
  says Bengaluru. Confirm it matches where you actually operate.
- ☐ No legal entity named in either document (not incorporated yet — revisit on registration).

## 7. Known gaps / not built
- No monetisation: zero payment integration anywhere in the codebase.
- Onboarding symptom set unified with the engine, but verify plan output reflects it for a real profile.
- Reminder firing is only testable with Redis + ARQ running (couldn't verify in sandbox).
- Dependency drift: chromadb 0.6.3→1.5.9, bcrypt 4.2→5.0, cryptography 48→50. Not urgent; needs a patch cadence.

---

### Verified green 2026-08-04
- Backend: **260 unit/integration tests passing**.
- Frontend: **lint + build clean**, **Playwright E2E 10 passing**, initial JS 197.6 KB gzip
  against a 250 KB budget.
- Production live and healthy at https://ayuraai.in (`/api/health`, `/api/ready` both green).
- Zero TODO/FIXME markers in application source.

### The one item no amount of testing closes
Section 4 (clinical/BAMS validation) remains entirely unchecked. The app ships dosage,
anupana and contraindication guidance to the public, and no registered practitioner has
reviewed the medicine KB, the disease→dosha mappings, or the pregnancy gating. The medical
disclaimer in the Terms mitigates but does not substitute for that review.
