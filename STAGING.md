# Ayura AI — Staging Environment

A full-parity stack (frontend + API + ARQ worker + MongoDB + Redis + ChromaDB) in one
command. Use it to tick off the ⚠️ infra items in `LAUNCH_CHECKLIST.md` — especially the
ones that can't be verified without real infra (reminders firing, background plan jobs,
rate limiting, RAG/citations).

## Prerequisites
- Docker + Docker Compose v2 (`docker compose version`). On macOS: Docker Desktop.
- At least one LLM key (Gemini is enough).

## 1. Configure
```bash
cp .env.staging.example .env.staging
# generate the three secrets:
for k in SECRET_KEY JWT_SECRET_KEY ADMIN_TOKEN; do echo "$k=$(openssl rand -hex 32)"; done
# paste those into .env.staging, then add your GEMINI_API_KEY (and SMTP if testing email)
```
`.env.staging` is git-ignored — never commit it.

## 2. Bring it up
```bash
docker compose -f docker-compose.staging.yml up -d --build
docker compose -f docker-compose.staging.yml ps          # all healthy?
docker compose -f docker-compose.staging.yml logs -f api  # watch startup
```
- App: **http://localhost:8080**
- API: **http://localhost:8000** (`/api/health`, `/api/ready`, `/docs`)
- The `vector-seed` container seeds ChromaDB once and exits (check its logs to confirm).

## 3. Smoke test (no data needed)
```bash
curl -s localhost:8000/api/health   # {"mongodb":"connected","chromadb":"connected",...}
curl -s localhost:8000/api/ready    # {"ready":true,...}
```

## 4. Work the checklist in the browser (http://localhost:8080)
- Register 2–3 email accounts (confirms the multi-signup fix).
- Onboard → Dosha quiz → generate each plan (set preferences when prompted) → confirm the
  "Classical basis" footer + agni/ama/ojas show.
- **Reminders that actually fire** (only testable here, with the worker running):
  set a reminder for 1–2 minutes ahead in your timezone, then watch:
  ```bash
  docker compose -f docker-compose.staging.yml logs -f worker
  ```
  A notification should be created at the scheduled minute (check the Notifications page).
- Interaction checker, community comments/report, adverse-reaction → timeline, Vaidya PDF export.

## 5. Useful ops
```bash
# Re-seed Chroma
docker compose -f docker-compose.staging.yml run --rm vector-seed
# Inspect Mongo
docker compose -f docker-compose.staging.yml exec mongodb mongosh ayura_staging
# Tear down (keep data)
docker compose -f docker-compose.staging.yml down
# Tear down + wipe volumes (fresh DB)
docker compose -f docker-compose.staging.yml down -v
```

## Notes
- `APP_ENV=staging` keeps cookies non-secure so it works over plain HTTP locally. To rehearse
  true production behaviour (secure/strict cookies, secret validation), set `APP_ENV=production`
  in `.env.staging` and serve over HTTPS (e.g. behind a TLS-terminating proxy / tunnel).
- This staging Mongo is a **container** (isolated from your production Atlas). To stage against
  a real Atlas cluster instead, set `MONGO_URL` in `.env.staging` and remove the `mongodb`
  service + its `depends_on`.
- The committed `docker-compose.yml` (prod) does **not** inject secrets/LLM keys and runs in
  `APP_ENV=production`; wire it to a secrets manager / env_file before using it for production.
