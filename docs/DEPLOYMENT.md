# Ayura AI — Production Deployment Guide

## Overview

Ayura AI uses a multi-container Docker Compose setup:

| Service | Image | Role |
|---------|-------|------|
| `api` | `ayura-api` | FastAPI + Uvicorn (Gunicorn workers) |
| `web` | `ayura-web` | React SPA served via Nginx |
| `mongodb` | `mongo:7` | Primary application database |
| `redis` | `redis:7-alpine` | Rate limiting + plan cache |

> [!IMPORTANT]
> The first deployment requires one-time ML model training and ChromaDB vector build steps before AI features are fully populated.

---

## Prerequisites

- Docker Engine 24+ and Docker Compose V2 (`docker compose`, not `docker-compose`)
- Git access to the repository
- A server with at least **4 vCPU / 8 GB RAM** (LangGraph agents run concurrently)
- A `.env` file configured from `.env.example` (see next section)

---

## Step 1 — Configure Environment Variables

```bash
cp .env.example .env
```

Then edit `.env` and fill in every `REPLACE_*` placeholder. Critical values:

| Variable | How to generate |
|----------|----------------|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(64))"` |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(64))"` |
| `ADMIN_TOKEN` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MONGO_PASSWORD` | Choose a strong random password |
| `AZURE_OPENAI_API_KEY` | From Azure Portal > OpenAI resource > Keys and Endpoint |
| `GEMINI_API_KEY` | From https://aistudio.google.com/app/apikey |
| `GOOGLE_CLIENT_ID/SECRET` | From https://console.cloud.google.com |

Also set:
```env
APP_ENV=production
DEBUG=false
FRONTEND_URL=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
```

---

## Step 2 — First-Time Data Setup (One-Time Only)

These steps build the ML models and vector database. **Run them once before or after first deploy, before users start generating plans.**

```bash
# Enter the server container (or run in a local venv)
docker compose run --rm api bash

# Inside the container:
cd /app/scripts

# 1. Generate synthetic training data
python generate_training_data.py

# 2. Train all ML models (saves .pkl files to /app/ml/models/)
python train_models.py

# 3. Build ChromaDB vectors from the knowledge base JSON files
#    (saves vectors to /app/data/chromadb/ which is a persisted volume)
python build_vectors.py

# 4. (Optional) Seed MongoDB with demo/test data
python seed_db.py

exit
```

> [!TIP]
> ML model files are excluded from git (`.gitignore`). They must be trained on first deploy
> and **are persisted inside the Docker volume** — they survive container restarts.
> If you want to pre-build them outside Docker and copy them in, mount the
> `server/ml/models/` directory as a volume.

---

## Step 3 — Start All Services

```bash
# Start all containers in detached mode
docker compose up -d

# Verify all services are healthy
docker compose ps
```

All services should show `healthy` status. If any service is `unhealthy`, check its logs:

```bash
docker compose logs api --tail=100
docker compose logs mongodb --tail=50
```

---

## Step 4 — Health Check Verification

```bash
# Basic health check (should return {"status": "ok"})
curl https://yourdomain.com/api/health

# Admin metrics (requires ADMIN_TOKEN from .env)
curl -H "X-Admin-Token: YOUR_ADMIN_TOKEN" https://yourdomain.com/api/health/metrics
```

Expected health response:
```json
{
  "status": "ok",
  "app": "Ayura AI",
  "environment": "production",
  "services": {
    "mongodb": "connected",
    "chromadb": "connected",
    "ml_models": "loaded"
  }
}
```

---

## Docker Compose Production Startup Sequence

The startup order is guaranteed by `depends_on` + healthchecks:

```
1. mongodb  (healthcheck: mongosh ping)
2. redis    (healthcheck: redis-cli ping)
3. api      (waits for MongoDB and Redis to be healthy, then starts Gunicorn)
4. web      (waits for api to be healthy, then starts Nginx)
```

---

## GitHub Actions Automated Deployment

The `.github/workflows/deploy.yml` workflow automatically:
1. Runs CI (pytest + npm lint + npm build)
2. Builds and pushes Docker images to GitHub Container Registry (GHCR)
3. SSHs into the production server and performs a rolling update
4. Restarts the API and web services
5. Validates the `/api/health` endpoint

### Required GitHub Secrets

Set these in your repo: **Settings → Secrets and variables → Actions**

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Production server IP or hostname |
| `DEPLOY_USER` | SSH username (e.g. `ubuntu`, `deploy`) |
| `DEPLOY_SSH_KEY` | Private SSH key (the server must have the corresponding public key in `~/.ssh/authorized_keys`) |
| `DEPLOY_PORT` | SSH port (default: 22) |

The `GITHUB_TOKEN` secret is provided automatically by GitHub Actions for GHCR access.

---

## Nginx Configuration (HTTPS)

The included `client/nginx.conf` serves the React SPA on port 80. For production HTTPS:

1. **Use a reverse proxy** (Nginx, Caddy, or a cloud load balancer) in front of the containers
2. Configure SSL termination at the reverse proxy level
3. Forward traffic to port 80 (web) and 8000 (api)

**Caddy example** (simplest option — auto-HTTPS):
```caddyfile
yourdomain.com {
  handle /api/* {
    reverse_proxy localhost:8000
  }
  handle /uploads/* {
    reverse_proxy localhost:8000
  }
  handle {
    reverse_proxy localhost:80
  }
}
```

---

## Updating After Code Changes

```bash
# On your local machine — push to main
git push origin main

# GitHub Actions will automatically:
# 1. Run CI
# 2. Build new images
# 3. Deploy to production with zero-downtime rolling update
```

For manual updates on the server:
```bash
cd /opt/ayura
git pull origin main

# Restart with new images
docker compose up -d --build
```

---

## Backup Strategy

```bash
# MongoDB backup
docker compose exec mongodb mongodump --uri="mongodb://user:pass@localhost/ayura" --out=/tmp/mongodump
docker compose cp mongodb:/tmp/mongodump ./mongodump_$(date +%Y%m%d)

# ChromaDB vectors (can be regenerated from source JSON, but faster to backup)
docker compose cp api:/app/data/chromadb ./chromadb_backup_$(date +%Y%m%d)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API returns `500` on plan generation | Check `docker compose logs api` for LLM API key errors |
| `COOKIE_SECURE=True` breaking local dev | Set `APP_ENV=development` or `COOKIE_SECURE=false` in local `.env` |
| ML models not found at startup | Run `build_vectors.py` and `train_models.py` inside the container |
| ChromaDB empty (no RAG context in plans) | Run `python scripts/build_vectors.py` inside the API container |
| Redis connection error | Check `REDIS_URL` matches the `redis` service name in docker-compose |
| Google OAuth redirect mismatch | Ensure `GOOGLE_REDIRECT_URI` exactly matches the URI in Google Console |

---

## `docker compose up` Freshness Checklist

On a **fresh server with only Docker installed**, the app starts in full with just:

```bash
# Clone repo
git clone https://github.com/your-org/ayura.git /opt/ayura
cd /opt/ayura

# Configure environment
cp .env.example .env
# Edit .env — fill all REPLACE_* values

# Start databases and app
docker compose up -d

# One-time data setup (first deploy only)
docker compose run --rm api bash -c "cd /app/scripts && python generate_training_data.py && python train_models.py && python build_vectors.py"

# Verify
curl http://localhost:8000/api/health
```

✅ The app is then fully operational.

> [!NOTE]
> The only things `docker compose up` **cannot** do automatically are the ML model training
> and ChromaDB vector build (first deploy only). Everything else
> — service startup, dependency ordering, health checks, and restart-on-failure — is handled
> automatically by Docker Compose.
