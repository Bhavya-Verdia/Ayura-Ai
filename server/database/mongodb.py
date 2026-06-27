"""
Ayura AI - MongoDB Connection (Motor Async Client)
Connects to a local or remote MongoDB instance.
Now serves as the PRIMARY database for all application data.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings
import logging
import certifi

logger = logging.getLogger("ayura.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_available: bool = False


async def init_mongodb():
    """Initialize MongoDB connection on startup. MANDATORY for app operation."""
    global _client, _db, _available
    try:
        url = settings.MONGO_URL
        client_kwargs = dict(
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,       # 50 conns/worker × 4 workers = 200 total — safe for Atlas M0/M2
            minPoolSize=2,
            maxIdleTimeMS=30000,  # return idle connections after 30s
        )
        # TLS (with certifi's CA bundle — fixes TLSV1_ALERT_INTERNAL_ERROR on macOS
        # OpenSSL 3.x) is only needed for Atlas / explicit-TLS connections. Plain
        # local `mongodb://` connections must NOT force TLS.
        _u = url.lower()
        if _u.startswith("mongodb+srv://") or "tls=true" in _u or "mongodb.net" in _u:
            client_kwargs["tlsCAFile"] = certifi.where()
        _client = AsyncIOMotorClient(url, **client_kwargs)
        # Ping to verify the server is reachable
        await _client.admin.command("ping")
        _db = _client[settings.MONGO_DB]

        # Spawn index creation in background to avoid blocking startup
        import asyncio
        asyncio.create_task(_create_indexes(_db))

        _available = True
        logger.info("MongoDB connected & index creation started. Ready for operations.")
    except Exception as exc:
        _available = False
        logger.error(f"CRITICAL: MongoDB unavailable ({exc}). Application cannot function without the database.")
        raise RuntimeError(f"MongoDB connection failed: {exc}") from exc


async def _create_indexes(db):
    try:
        # Users
        await db.users.create_index("email", unique=True)
        # Unique-if-present OAuth/phone ids. These MUST be partial (not sparse):
        # email/password signups store google_id/github_id/phone_number as explicit
        # null, and a sparse unique index treats null as a value — so the 2nd such
        # signup collides ("E11000 dup key: { google_id: null }"). A partial index
        # enforces uniqueness only on real string values. Drop+recreate to migrate
        # any pre-existing sparse index.
        for _f in ("google_id", "github_id", "phone_number"):
            _opts = dict(unique=True, partialFilterExpression={_f: {"$type": "string"}})
            try:
                await db.users.create_index(_f, **_opts)
            except Exception:
                try:
                    await db.users.drop_index(f"{_f}_1")
                    await db.users.create_index(_f, **_opts)
                except Exception as _e:
                    logger.warning(f"Could not migrate unique index for {_f}: {_e}")
        await db.refresh_tokens.create_index("jti", unique=True)
        await db.refresh_tokens.create_index([("user_id", 1), ("expires_at", -1)])
        await db.otps.create_index("phone_number", unique=True)
        await db.otps.create_index("expires_at", expireAfterSeconds=0)

        # Plan History
        await db.plan_history.create_index([("user_id", 1), ("generated_at", -1)])

        # Progress Logs
        await db.progress_logs.create_index([("user_id", 1), ("date", -1)])

        # Chat
        await db.chat_messages.create_index([("user_id", 1), ("session_id", 1)])
        await db.chat_messages.create_index([("session_id", 1), ("timestamp", 1)])
        await db.chat_sessions.create_index([("user_id", 1), ("updated_at", -1)])
        await db.reminders.create_index([("user_id", 1), ("created_at", -1)])
        await db.notifications.create_index([("user_id", 1), ("is_read", 1), ("created_at", -1)])
        await db.community_posts.create_index("created_at")
        await db.community_comments.create_index([("post_id", 1), ("created_at", 1)])
        await db.weekly_checkins.create_index([("user_id", 1), ("timestamp", -1)])
        await db.timeline.create_index([("user_id", 1), ("timestamp", -1)])
        # Plan jobs (background task tracking)
        await db.plan_jobs.create_index([("user_id", 1), ("created_at", -1)])
        await db.plan_jobs.create_index("status")
        # TTL: auto-delete completed jobs after 7 days
        await db.plan_jobs.create_index("completed_at", expireAfterSeconds=604800, sparse=True)
        await db.audit_log.create_index([("user_id", 1), ("timestamp", -1)])
        await db.audit_log.create_index("event_type")
        # Feature preferences (one document per user)
        await db.user_preferences.create_index("user_id", unique=True)
        # Feedback
        await db.feedback.create_index([("created_at", -1)])
    except Exception as e:
        logger.error(f"Failed to create indexes in background: {e}")


async def close_mongodb():
    """Close MongoDB connection on shutdown."""
    global _client, _available
    if _client:
        _client.close()
        _available = False
    logger.info("MongoDB connection closed")


def is_mongodb_available() -> bool:
    """Check if MongoDB is connected and ready."""
    return _available


def get_mongodb() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance. Raises error if unavailable."""
    if not _available or _db is None:
        raise RuntimeError("MongoDB is not initialized or unavailable.")
    return _db
