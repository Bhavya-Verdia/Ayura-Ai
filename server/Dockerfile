# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run stage
FROM python:3.12-slim

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY . .

# Create uploads and data directories with proper permissions
RUN mkdir -p uploads/avatars data/chromadb && \
    chown -R appuser:appuser /app

# appuser is a system user with no home dir; point HOME at the (writable) app dir
# so libraries that cache under ~/.cache (e.g. ChromaDB's ONNX embedding model)
# have a writable location instead of failing on /home/appuser.
ENV HOME=/app

USER appuser

EXPOSE 8000

# Worker count is env-driven so it can be tuned per host (gunicorn reads
# WEB_CONCURRENCY natively). Default 4; override at runtime, e.g.
#   docker run -e WEB_CONCURRENCY=$(nproc) ...
ENV WEB_CONCURRENCY=4

# Self-reported health for orchestrators / `docker ps`. Uses Python (curl is
# not installed in the runtime stage); urllib raises on non-2xx, so a degraded
# 503 from /api/health correctly marks the container unhealthy. start-period
# allows for MongoDB connect + KB cache load on cold start.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=4)"]

CMD ["gunicorn", "main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
