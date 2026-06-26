# Ayura AI — Pre-Launch QA Checklist

Status legend: ☐ todo · ✅ verified this session · ⚠️ needs your action / environment

Generated 2026-06-26. "verified this session" = exercised against a live local stack
(local MongoDB + backend + Playwright). It does **not** mean verified on production infra.

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
- ☐ Rate limits active on auth + sensitive plan endpoints in prod (needs Redis).
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

## 5. Observability & ops (☐)
- ☐ Sentry DSN set (backend + worker); errors reporting.
- ☐ `/api/health` + `/api/ready` wired to load balancer health checks.
- ☐ Structured logs shipping; metrics endpoint (`/api/health/metrics`, admin-gated) reachable.
- ☐ Backups configured on Atlas.

## 6. Known gaps / not built
- Web-push notifications (in-app + email only — needs VAPID + service worker).
- Onboarding symptom set unified with the engine, but verify plan output reflects it for a real profile.
- Reminder firing is only testable with Redis + ARQ running (couldn't verify in sandbox).

---

### Verified green this session
- Backend: **212 unit/integration tests passing**.
- Frontend: **lint + build clean**, **Playwright E2E 6 passing**.
- Live API walk against a real DB: register → onboard → assess → generate plan → all new endpoints.
