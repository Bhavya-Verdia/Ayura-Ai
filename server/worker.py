"""
Ayura AI - Background Worker (ARQ)
Processes AI plan generations asynchronously to avoid starving the main FastAPI process.

Run with: `arq worker.WorkerSettings`
"""

import asyncio
import logging
from arq.connections import RedisSettings
from arq import cron
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
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        )
        logger.info("Sentry initialized for worker.")

    # Init Motor (MongoDB)
    await init_mongodb()

    # Load kb_cache so plan jobs can access yoga poses, exercises, etc.
    from database.mongodb import get_mongodb
    from core.kb_cache import kb_cache
    await kb_cache.load(get_mongodb())

    # Init ChromaDB
    init_chromadb()

    logger.info("ARQ Worker is ready!")


async def shutdown(ctx):
    """Clean up resources on worker shutdown."""
    logger.info("Shutting down ARQ Worker...")
    await close_mongodb()
    logger.info("Worker resources cleaned up.")


async def dispatch_due_reminders(ctx):
    """Check for reminders due within the current minute and deliver notifications."""
    from datetime import datetime, timezone
    from database.mongodb import get_mongodb
    from services.notification_service import create_and_deliver_notification

    db = get_mongodb()
    now = datetime.now(timezone.utc)
    current_time_str = now.strftime("%H:%M")
    current_day = now.strftime("%A").lower()  # e.g. "monday"

    # Find active reminders matching current time and day
    cursor = db.reminders.find({
        "is_active": True,
        "time": current_time_str,
        "$or": [
            {"days": []},                  # empty = every day
            {"days": current_day},         # exact string match
            {"days": {"$in": [current_day]}},  # element in list
        ],
    })

    async for reminder in cursor:
        try:
            await create_and_deliver_notification(
                db,
                user_id=reminder["user_id"],
                title=reminder.get("title", "Reminder"),
                body=f"Time for your {reminder.get('reminder_type', 'wellness')} activity: {reminder.get('title', '')}",
                notif_type="reminder",
            )
        except Exception as e:
            logger.error(f"Failed to dispatch reminder {reminder.get('_id')}: {e}")


async def _advance_reminder(db, reminder: dict):
    """Placeholder — reminders use time+days schedule, not a next_due timestamp."""
    pass


class WorkerSettings:
    """Configuration for the ARQ worker process."""
    functions = [_run_plan_job, dispatch_due_reminders]
    cron_jobs = [
        cron(dispatch_due_reminders, minute=set(range(60))),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379")
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    max_tries = 3
    job_timeout = settings.PLAN_TIMEOUT_SECONDS + 30
