"""
Ayura AI - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config import settings
from core.metrics import metrics_registry
from core.admin import require_admin_token
from core.rate_limit import InMemoryRateLimitMiddleware
from database.mongodb import init_mongodb, close_mongodb
from database.chromadb_client import init_chromadb
from routes import (
    admin,
    auth,
    checkin,
    chat,
    community,
    export,
    feedback,
    notifications,
    plans,
    preferences,
    privacy,
    profile,
    progress,
    reminders,
    timeline,
)
import os
import time
import logging
from core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for the application."""
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME}...")

    # Validate production secrets before anything else
    settings.validate_production_secrets()

    # Initialize Sentry
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            environment=settings.APP_ENV,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        )
        logger.info("Sentry initialized for error tracking.")

    await init_mongodb()
    from database.mongodb import get_mongodb
    from core.kb_cache import kb_cache
    await kb_cache.load(get_mongodb())

    init_chromadb()
    # Warm the embedding model off the event loop so the first chat request
    # doesn't pay the cold ONNX model load. Non-blocking; failures are harmless.
    import asyncio as _asyncio
    from database.chromadb_client import warm_embeddings
    _asyncio.create_task(_asyncio.to_thread(warm_embeddings))

    from core.cache import cache_manager
    await cache_manager.connect()

    yield

    # --- Shutdown ---
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_mongodb()
    await cache_manager.disconnect()
    logger.info(f"{settings.APP_NAME} shut down cleanly.")

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Holistic Health Platform — Gym, Yoga, Diet, Ayurveda, Remedies",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {str(exc)}")
    content = {"detail": "Internal Server Error"}
    if settings.DEBUG:
        content["message"] = str(exc)
    return JSONResponse(status_code=500, content=content)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.TRUSTED_HOST_LIST,
)

# --- Compression ---
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    InMemoryRateLimitMiddleware,
    default_limit=settings.RATE_LIMIT_PER_MINUTE,
    auth_limit=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    enabled=settings.RATE_LIMIT_ENABLED,
    redis_url=settings.REDIS_URL,
)

# --- Security Headers ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://accounts.google.com https://api.github.com wss: ws:; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that declare a body larger than max_bytes via Content-Length.
    Individual routes (avatar upload) enforce their own tighter limits on the
    actual payload, so 5 MB is intentionally generous here.
    """
    MAX_BYTES = 5 * 1024 * 1024  # 5 MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request body too large (max {self.MAX_BYTES // (1024 * 1024)} MB)."},
                    )
            except ValueError:
                pass
        return await call_next(request)

app.add_middleware(BodySizeLimitMiddleware)


# --- Request Logging Middleware ---
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        if not request.url.path.startswith("/uploads"):
            logging.getLogger("ayura.access").info(
                "%s %s %s %dms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response

app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/profile", tags=["User Profile"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["Feature Preferences"])
app.include_router(plans.router, prefix="/api/plans", tags=["Plan Generation"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chatbot"])
app.include_router(checkin.router, prefix="/api/checkin", tags=["Weekly Check-in"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["Health Timeline"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["Reminders"])
app.include_router(privacy.router, prefix="/api/privacy", tags=["Privacy"])
app.include_router(community.router, prefix="/api/community", tags=["Community"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])



# --- Static Files (avatar uploads) ---
uploads_dir = settings.UPLOADS_DIR
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/api/health", tags=["Health Check"])
async def health_check():
    from database.mongodb import is_mongodb_available
    from database.chromadb_client import is_chromadb_available
    from fastapi.responses import JSONResponse as _JSONResponse

    mongo_ok = is_mongodb_available()
    chroma_ok = is_chromadb_available()
    payload = {
        "status": "healthy" if mongo_ok else "degraded",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "mongodb": "connected" if mongo_ok else "unavailable",
        "chromadb": "connected" if chroma_ok else "unavailable",
    }
    # Return 503 so load balancers and uptime monitors detect a broken worker
    return _JSONResponse(status_code=200 if mongo_ok else 503, content=payload)


@app.get("/api/weather", tags=["Weather"])
async def get_weather(lat: float | None = None, lon: float | None = None):
    """Get current weather and its Ayurvedic impact."""
    from services.weather_service import fetch_weather
    data = await fetch_weather(lat, lon)
    if data is None:
        return {"available": False, "message": "Weather data unavailable. Configure WEATHER_API_KEY."}
    return {"available": True, **data}


@app.get("/api/ready", tags=["Health Check"])
async def readiness_check():
    """Readiness probe — returns 503 until MongoDB is connected AND the
    KB cache has finished loading.  Use this as the k8s readinessProbe or
    load-balancer health target so cold workers don't receive traffic while
    startup is still in progress."""
    from database.mongodb import is_mongodb_available
    from core.kb_cache import kb_cache
    from fastapi.responses import JSONResponse as _JSONResponse

    mongo_ok = is_mongodb_available()
    kb_ok    = kb_cache.loaded
    ready    = mongo_ok and kb_ok

    return _JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready":    ready,
            "mongodb":  "connected" if mongo_ok else "unavailable",
            "kb_cache": "loaded"    if kb_ok    else "loading",
        },
    )


@app.get("/api/health/metrics", tags=["Health Check"], dependencies=[Depends(require_admin_token)])
async def metrics_check():
    return metrics_registry.snapshot()
