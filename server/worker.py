"""
Ayura AI - Background Worker (ARQ)
Processes AI plan generations asynchronously to avoid starving the main FastAPI process.

Run with: `arq worker.WorkerSettings`
"""

import asyncio
import logging
from arq.connections import RedisSettings
from config import settings
from database.mongodb import init_mongodb, close_mongodb
from database.chromadb_client import init_chromadb
from routes.plans import _run_plan_job

logger = logging.getLogger("ayura.worker")

async def startup(ctx):
    """Initialize resources for the worker."""
    logger.info("Initializing ARQ Worker resources...")
    
    # Init Sentry if configured
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        logger.info("Sentry initialized for worker.")

    # Init Motor (MongoDB)
    await init_mongodb()
    
    # Init ChromaDB
    init_chromadb()
    
    logger.info("ARQ Worker is ready!")


async def shutdown(ctx):
    """Clean up resources on worker shutdown."""
    logger.info("Shutting down ARQ Worker...")
    await close_mongodb()
    logger.info("Worker resources cleaned up.")


class WorkerSettings:
    """Configuration for the ARQ worker process."""
    functions = [_run_plan_job]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379")
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    max_tries = 3
    job_timeout = settings.PLAN_TIMEOUT_SECONDS + 30
