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

# Bake ChromaDB's ONNX embedding model into the image.
#
# Without this the model is fetched on first use, which on a fresh container means
# all WEB_CONCURRENCY gunicorn workers downloading the same 79 MB archive to the
# same path at once and unpacking over each other. Observed in production on the
# 2026-08-13 deploy: /api/health was unreachable for the first ~15 seconds while
# four workers pulled the file, and every worker then logged
#   INVALID_PROTOBUF: Load model from .../model.onnx failed
# because it read a model another worker was still extracting. The app stays up —
# the warm-up failure is only a warning — so what the user gets is RAG silently
# returning nothing until the race settles. Downloading once at build time removes
# the stampede, the corruption window and the slow first request together.
RUN python -c "\
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2; \
ONNXMiniLM_L6_V2()._download_model_if_not_exists()" && \
    chown -R appuser:appuser /app/.cache

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
