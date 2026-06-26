# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

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
npm run build
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

`routes/plans._generate_feature_via_engine` is the single entry point both the holistic and per-feature paths use — it runs the engine + enricher and applies pregnancy/safety gating. The per-feature endpoints (`POST /api/plans/{gym,yoga,diet,routine,panchakarma,remedies,medicines}`) return the plan **synchronously**. The holistic `POST /api/plans/generate` is offloaded to an **ARQ background worker** (`server/worker.py`) via Redis and returns a `job_id` to poll at `/api/plans/job/{jobId}`; if Redis/ARQ is unavailable it falls back to running the job in-process via FastAPI `BackgroundTasks`.

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
- `server/core/` — cross-cutting concerns: rate limiting, caching, KB cache, metrics, WebSocket manager, admin token auth
- `server/database/` — Motor (async MongoDB) and ChromaDB clients
- `server/data/` — JSON knowledge base files ingested into ChromaDB

### Production Notes
`config.py` enforces non-default `SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_TOKEN` when `APP_ENV=production`. `COOKIE_SECURE` and `COOKIE_SAMESITE=strict` are auto-forced in production. The `validate_production_secrets()` method is called at startup.
