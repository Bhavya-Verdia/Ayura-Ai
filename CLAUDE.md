# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Deployment
Production deploys run in **GitHub Actions on push to `main`** (`.github/workflows/deploy.yml`),
gated on CI. There is nothing to run locally.

```bash
gh run watch                                    # follow the deploy
gh run list --workflow="Ayura AI Deploy" -L 5   # recent deploys
gh workflow run "Ayura AI Deploy"               # deploy without a push
```

`./deploy.sh` is break-glass only and refuses to run without `--break-glass`. Do not use it
because it is faster: a local deploy and a push-triggered one both run `docker compose rm -fs`
then `up -d` on the same droplet, and the collision has taken production down — Docker renames
the loser's container, the next run hits "container name is already in use", and the site can
be left with nothing running. **Never accept a deploy script's own success line as evidence**;
verify by image timestamp and by fetching the served asset.

### Infrastructure
```bash
docker-compose up -d          # Start MongoDB, Redis, ChromaDB
```

### Backend
```bash
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000   # Dev server
arq worker.WorkerSettings                          # Background job worker (separate terminal)
python scripts/build_vectors.py                    # Seed ChromaDB knowledge base
```

### Frontend
```bash
cd client
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # Vite build; postbuild runs scripts/prerender.mjs (multi-route SEO) + check-bundle-size.mjs
npm run lint
npm run test:e2e  # Playwright E2E tests
npm run test:e2e:ui
```

### Backend Tests
```bash
cd server
pytest                            # All tests
pytest tests/test_auth.py         # Single test file
pytest tests/test_auth.py::test_register_user  # Single test
```

## Environment Variables

Copy `.env.example` to `.env` at the repo root. Settings are loaded by `server/config.py` (pydantic-settings), which reads both `server/.env` and the root `.env`.

Key variables:
- `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` — primary LLM (GPT-4o)
- `GEMINI_API_KEY` — fallback LLM (Gemini 2.0 Flash); app runs without Azure if only this is set
- `MONGO_URL` — full MongoDB URI, or set `MONGO_HOST`/`MONGO_PORT`/`MONGO_DB` individually
- `REDIS_URL` — required for ARQ background worker; rate limiting degrades gracefully without it
- `CHROMA_HOST` / `CHROMA_PORT` — if set, uses remote ChromaDB HTTP client; otherwise embedded PersistentClient at `server/data/chromadb/`
- `JWT_SECRET_KEY`, `SECRET_KEY` — must be changed from defaults in production
- `VITE_API_URL` — frontend API base; defaults to `/api` (proxied by Vite dev server to port 8000)

## Architecture

### Request Flow
The Vite dev server proxies `/api` and `/uploads` to `http://127.0.0.1:8000`. In production, nginx (see `client/nginx.conf`) handles this. All routes are mounted at `/api/<resource>` in `server/main.py`.

### Authentication
JWT tokens are stored exclusively in **HTTP-only cookies** (`ayura_access`, `ayura_refresh`) — never localStorage. The frontend axios client in `client/src/api/client.js` sends `withCredentials: true` and auto-refreshes on 401 via `/api/auth/refresh`. Google and GitHub OAuth are supported alongside email/password.

### AI Plan Generation Pipeline (engine-backed + LLM enrichment)
Each feature is produced by a **deterministic, KB-grounded engine**, then optionally enriched with LLM-generated narrative. There is no free-text LLM agent that authors plans (an earlier 4-agent LangGraph pipeline was removed because it ignored the KB and could hallucinate formulations/asanas).

1. **Tier 1 — Core rule engines** (`server/engine/`): BMI, calorie, dosha analysis, seasonal adjustments, condition filtering.
2. **Tier 2 — Per-feature engines** (`server/services/`): `gym_plan_engine`, `yoga_plan_engine`, `diet_plan_engine`, `panchakarma_engine`, `routine_engine`, `remedy_engine` (medicines + home remedies). Each builds a structured plan from the bundled JSON knowledge bases. Diet is **LLM-primary** (`diet_llm_generator`) with the rule engine as a fallback.
3. **Tier 3 — LLM enrichers** (`server/services/*_enricher.py`): add narrative/coaching on top of the deterministic plan via the shared `llm_client`. RAG (`server/ai/rag_pipeline.py`) provides ChromaDB semantic context.

#### Gym library: authored, not imported
`data/knowledge_base/gym_exercises.json` is **generated** by
`scripts/build_gym_library.py` from the curated spec in `scripts/gym_library/`
(173 movements). Never hand-edit the JSON — `--check` and a test enforce that it
matches the spec. `scripts/seed_gym_exercises.py` is a retired stub that refuses
to run: it re-derived `category`, `level` and `mechanic` from substring matches
on exercise names, and 23% of its rows contradicted their own upstream source.

The library states what the engine used to infer from names — `role`, `mechanic`,
`family`, `load_class`, `impact`, `skill_floor`, `movement_pattern`, `bucket`,
`rep_style`, `canonical`, `coaching_cue`. `role` is the important one: only
`main`/`accessory` may fill a working slot, which is what stops a stretch being
prescribed as a set of eight. Upstream (`data/sources/free_exercise_db.json`) is
a **muscle-list source only**. All instruction prose is authored in
`scripts/gym_library/prose.py`: 89 of the 120 entries that reused upstream text
carried a defect, including a dumbbell exercise whose steps told you to pick up a
barbell and two that instructed holding your breath under load. Contraindications,
pregnancy and dosha are authored per movement in `scripts/gym_library/clinical.py`,
each with a stated mechanism — they differ from the old derived rules on 89 of 173.

#### Diet library: authored, not derived
`data/knowledge_base/diet_foods.json` is **generated** by
`scripts/build_diet_library.py` from the curated spec in `scripts/diet_library/`
(150 foods). Never hand-edit the JSON — `--check` and a test enforce that it
matches the spec. `scripts/seed_diet_foods.py` is a retired stub that refuses to
run: it produced the entire Ayurvedic layer from a ten-row table of category
defaults plus substring matches on the food's id, and its values differ from the
authored ones on 83 of 150 rows for rasa, 46 for vipaka, 42 for virya, 134 for
dosha effect, 128 for nutrition and all 150 for ritu.

What the generator could not express is why the spec exists: it emitted six rasa
combinations for 150 foods, `season_suitable: ["all"]` on every row (so the
Ritucharya scoring in `diet_plan_engine` had nothing to score against), no `guna`
axis at all — while `diet_llm_generator`'s prompt requires every meal to cite it,
so the model invented it — and **no sour vipaka at all**, which is unreachable in
its category table and wrong for every sour food. `prep_state` is part of a food's
identity, not a note: Ardraka and Shunthi are `ginger_fresh` and `ginger_dry`,
two rows with opposite virya, not one `ginger`. A row that departs from the rasa
rule must state a `prabhava` giving the reason, or `schema.validate` refuses it.

Rows are `reviewed: false` — authored, **not clinically reviewed**. They belong in
the Vaidya packet alongside the gym and Panchakarma flags.

`routes/plans._generate_feature_via_engine` is the single entry point both the holistic and per-feature paths use — it runs the engine + enricher and applies pregnancy/safety gating. The per-feature endpoints (`POST /api/plans/{gym,yoga,diet,routine,panchakarma,remedies,medicines}`) return the plan **synchronously**. The holistic `POST /api/plans/generate` is offloaded to an **ARQ background worker** (`server/worker.py`) via Redis and returns a `job_id` to poll at `/api/plans/job/{jobId}`; if Redis/ARQ is unavailable it falls back to running the job in-process via FastAPI `BackgroundTasks`.

### Chat Agent (`server/ai/agents/health_agent.py`)
The conversational chatbot (`POST /api/chat`, mounted in `main.py`) **is** a LangGraph ReAct agent (`create_react_agent`) with a small tool set (`get_plan_detail`, `set_reminder`, `check_my_medicine_interactions`, `adapt_plan`, `get_health_trend`). This is the *only* place LangGraph is used — the removed 4-agent pipeline noted above was for **plan authoring**, which is now purely engine-backed. Chat may read/adapt plans and trigger side effects but never authors them from free text. LangSmith tracing is enabled when a key is configured.

### LLM Client (`server/ai/llm_client.py`)
Singleton `llm_client` wraps Azure OpenAI (primary) and Google Gemini (fallback) with automatic failover and tenacity retry. Both `generate()` (batch) and `generate_stream()` (SSE) are supported. Metrics are recorded via `core/metrics.py`.

### Frontend State
- **Auth state**: `client/src/providers/AuthContext` — wraps the app, exposes `user` and `loading`
- **Server state**: TanStack Query (React Query v5) with IDB-backed persistence
- **Routing**: React Router v7, lazy-loaded pages, route guards (`PrivateRoute`, `AdminRoute`, `OnboardingRoute`, `PublicRoute`) in `client/src/App.jsx`
- **i18n**: `i18next` + `react-i18next`, config in `client/src/i18n.js`
- **PWA**: `vite-plugin-pwa` with `registerType: 'prompt'`

### Backend Structure
- `server/routes/` — FastAPI routers, one file per domain
- `server/schemas/` — Pydantic v2 request/response models
- `server/services/` — business logic called by routes
- `server/core/` — cross-cutting concerns: rate limiting, daily usage quotas, caching, KB cache, metrics, WebSocket manager, admin token auth

### Abuse & Cost Controls
Two independent layers, because they stop different things:
- **Per-minute rate limiting** (`core/rate_limit.py`, middleware) caps burst. Authenticated requests key on **user id** (decoded from the access cookie); auth routes and anonymous requests key on **IP**. The client IP is read from the *right* of `X-Forwarded-For`, `TRUSTED_PROXY_HOPS` entries in — reading from the left let callers spoof a fresh bucket per request. `client/nginx.conf` must therefore **overwrite** `X-Forwarded-For` with `$remote_addr`, not append to it.
- **Per-user daily quotas** (`core/quota.py`) cap sustained spend, since every plan generation and chat turn is a billed LLM call. Counted in `usage_quota` (MongoDB, TTL-reaped) so they hold across processes. Charged on cache *misses* only, after any non-LLM short-circuit; holistic generation bills `HOLISTIC_QUOTA_COST`. Admins are exempt, and the check fails open if Mongo is unreachable.
- Login has a **per-account lockout** (`LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`) — IP limits alone don't bound a distributed guessing attack on one password.
- `server/database/` — Motor (async MongoDB) and ChromaDB clients
- `server/data/` — JSON knowledge base files ingested into ChromaDB

### Production Notes
`config.py` enforces non-default `SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_TOKEN` when `APP_ENV=production`. `COOKIE_SECURE` and `COOKIE_SAMESITE=strict` are auto-forced in production. The `validate_production_secrets()` method is called at startup.
