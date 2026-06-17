"""
Ayura AI - Notification Service
Creates notification records and delivers them via email.
"""

import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def create_and_deliver_notification(
    db,
    user_id: str,
    title: str,
    body: str,
    notif_type: str = "info",
    background_tasks=None,
) -> dict:
    """Insert a notification record and optionally send an email."""
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": body,
        "type": notif_type,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db.notifications.insert_one(doc)

    if background_tasks is not None:
        background_tasks.add_task(_send_notification_email, db, user_id, title, body)
    else:
        # Fire-and-forget when no BackgroundTasks context is available
        import asyncio
        asyncio.create_task(_send_notification_email(db, user_id, title, body))

    return doc


async def _send_notification_email(db, user_id: str, title: str, body: str) -> None:
    try:
        user = await db.users.find_one({"_id": user_id})
        if not user or not user.get("email"):
            return
        prefs = await db.user_preferences.find_one({"user_id": user_id}) or {}
        if prefs.get("email_notifications") is False:
            return
        from services.email_service import send_notification_email
        await send_notification_email(user["email"], title, body)
    except Exception as e:
        logger.error(f"Notification email failed for user {user_id}: {e}")
