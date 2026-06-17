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
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        logger.info("Sentry initialized for error tracking.")

    await init_mongodb()
    from database.mongodb import get_mongodb
    from core.kb_cache import kb_cache
    await kb_cache.load(get_mongodb())
    
    init_chromadb()
    
    logger.info(f"{settings.APP_NAME} is ready!")

    from core.cache import cache_manager
    await cache_manager.connect()

    yield

    # --- Shutdown ---
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_mongodb()
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
        return response

app.add_middleware(SecurityHeadersMiddleware)


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
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "mongodb": "connected" if is_mongodb_available() else "unavailable",
        "chromadb": "connected" if is_chromadb_available() else "unavailable",
    }


@app.get("/api/weather", tags=["Weather"])
async def get_weather(lat: float | None = None, lon: float | None = None):
    """Get current weather and its Ayurvedic impact."""
    from services.weather_service import fetch_weather
    data = await fetch_weather(lat, lon)
    if data is None:
        return {"available": False, "message": "Weather data unavailable. Configure WEATHER_API_KEY."}
    return {"available": True, **data}


@app.get("/api/health/metrics", tags=["Health Check"], dependencies=[Depends(require_admin_token)])
async def metrics_check():
    return metrics_registry.snapshot()
