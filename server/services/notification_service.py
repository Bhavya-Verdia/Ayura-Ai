"""
Ayura AI - Notification Service
Creates notification records and delivers them via email + web push.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

# Strong references to fire-and-forget delivery tasks: asyncio only holds weak
# refs to running tasks, so an unreferenced task can be garbage-collected
# mid-flight and the email/push silently never sends.
_delivery_tasks: set = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _delivery_tasks.add(task)
    task.add_done_callback(_delivery_tasks.discard)


async def create_and_deliver_notification(
    db,
    user_id: str,
    title: str,
    body: str,
    notif_type: str = "info",
    background_tasks=None,
    url: str = "/notifications",
) -> dict:
    """Insert a notification record and deliver it via email + web push."""
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
        background_tasks.add_task(_send_push, db, user_id, title, body, url)
    else:
        # Fire-and-forget when no BackgroundTasks context is available
        _spawn(_send_notification_email(db, user_id, title, body))
        _spawn(_send_push(db, user_id, title, body, url))

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


async def _send_push(db, user_id: str, title: str, body: str, url: str = "/notifications") -> None:
    """Deliver to every subscribed device. Dead subscriptions (404/410 from the
    push service) are pruned so the collection self-heals as browsers rotate or
    revoke endpoints. pywebpush is synchronous (requests under the hood), so
    each send runs in a worker thread to keep the event loop free."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return
    try:
        from pywebpush import webpush, WebPushException

        prefs = await db.user_preferences.find_one({"user_id": user_id}) or {}
        if prefs.get("push_notifications") is False:
            return

        payload = json.dumps({"title": title, "body": body, "url": url})
        async for sub in db.push_subscriptions.find({"user_id": user_id}):
            try:
                await asyncio.to_thread(
                    webpush,
                    subscription_info=sub["subscription"],
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                    ttl=3600,
                )
            except WebPushException as e:
                status = getattr(e.response, "status_code", None)
                if status in (404, 410):
                    await db.push_subscriptions.delete_one({"_id": sub["_id"]})
                else:
                    logger.warning(f"Push delivery failed for user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Push channel failed for user {user_id}: {e}")
