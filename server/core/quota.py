"""Per-user daily usage quotas for billed LLM operations.

The per-minute rate limiter caps *burst*; it does nothing about a single
authenticated account issuing plan generations steadily all day. Every plan
generation and chat turn is a paid Azure/Gemini call, so each user also gets a
daily allowance, counted in MongoDB so it holds across worker processes and
restarts (the rate limiter's in-memory fallback does not).

Counters live in `usage_quota`, one document per (user, bucket, UTC day), and
are reaped by a TTL index on `expires_at` (see database/mongodb.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from config import settings
from core.logger import logger

# Bucket names — keep in sync with the quota settings in config.py
PLAN_BUCKET = "plan"
CHAT_BUCKET = "chat"


def _day_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


async def consume_quota(
    db,
    user_id: str,
    bucket: str,
    limit: int,
    *,
    cost: int = 1,
    exempt: bool = False,
) -> None:
    """Charge `cost` uses against today's allowance; raise 429 once exhausted.

    `cost` lets one request bill for the work it actually causes — a holistic
    generation fans out to six engine+enricher pairs and should not cost the
    same as a single feature.

    Increments *before* checking, so concurrent requests cannot race past the
    limit together. Fails open: if the counter store is unreachable we log and
    allow the request, because losing the cost ceiling for a few minutes beats
    taking plan generation down with it.
    """
    if exempt or not settings.QUOTA_ENABLED or limit <= 0:
        return

    now = datetime.now(timezone.utc)
    doc_id = f"{user_id}:{bucket}:{_day_key(now)}"

    try:
        doc = await db.usage_quota.find_one_and_update(
            {"_id": doc_id},
            {
                "$inc": {"count": max(1, cost)},
                "$setOnInsert": {
                    "user_id": user_id,
                    "bucket": bucket,
                    "day": _day_key(now),
                    # Keep a day of slack past the window so a support query can
                    # still see yesterday's usage.
                    "expires_at": now + timedelta(days=2),
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except Exception as exc:  # counter unavailable — see docstring
        logger.warning("Quota check skipped for %s/%s: %s", user_id, bucket, exc)
        return

    # Mocked/omitted collections in tests return non-dict sentinels; treat an
    # unreadable counter the same as an unavailable one.
    if not isinstance(doc, dict):
        return

    count = doc.get("count")
    if not isinstance(count, int) or count <= limit:
        return

    reset_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    retry_after = max(1, int((reset_at - now).total_seconds()))
    logger.warning("Daily %s quota exhausted for user %s (%d/%d)", bucket, user_id, count, limit)
    raise HTTPException(
        status_code=429,
        detail=(
            f"You've reached today's limit of {limit} "
            f"{'plan generations' if bucket == PLAN_BUCKET else 'chat messages'}. "
            "It resets at midnight UTC."
        ),
        headers={"Retry-After": str(retry_after)},
    )


async def consume_plan_quota(db, user, cost: int = 1) -> None:
    """Charge a plan generation against the caller's daily allowance."""
    await consume_quota(
        db,
        user.id,
        PLAN_BUCKET,
        settings.DAILY_PLAN_QUOTA,
        cost=cost,
        exempt=bool(getattr(user, "is_admin", False)),
    )


async def consume_chat_quota(db, user) -> None:
    """Charge one chat turn against the caller's daily allowance."""
    await consume_quota(
        db,
        user.id,
        CHAT_BUCKET,
        settings.DAILY_CHAT_QUOTA,
        exempt=bool(getattr(user, "is_admin", False)),
    )
