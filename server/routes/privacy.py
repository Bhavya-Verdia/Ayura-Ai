"""
Ayura AI - Privacy & GDPR Routes
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()


@router.get("/export")
async def export_user_data(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Export all user data as JSON (GDPR Article 20)."""
    # Gather all user data
    user_dict = user.model_dump()
    user_dict.pop("password_hash", None)  # Never export password hash

    cursor = db.plan_history.find({"user_id": user.id})
    plans = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        plans.append(doc)

    cursor = db.chat_messages.find({"user_id": user.id}, {"_id": 0})
    messages = await cursor.to_list(length=1000)

    cursor = db.progress_logs.find({"user_id": user.id}, {"_id": 0})
    progress = await cursor.to_list(length=1000)

    cursor = db.weekly_checkins.find({"user_id": user.id}, {"_id": 0})
    checkins = await cursor.to_list(length=100)

    export_data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "profile": user_dict,
        "plans": plans,
        "chat_messages": messages,
        "progress_logs": progress,
        "weekly_checkins": checkins,
    }

    content = json.dumps(export_data, indent=2, default=str)
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=ayura_data_{user.id[:8]}.json"}
    )


@router.delete("/account", status_code=200)
async def delete_account(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Permanently delete all user data (GDPR Article 17 - Right to Erasure)."""
    user_id = user.id

    # Delete all user-related data
    await db.users.delete_one({"_id": user_id})
    await db.plan_history.delete_many({"user_id": user_id})
    await db.chat_messages.delete_many({"user_id": user_id})
    await db.chat_sessions.delete_many({"user_id": user_id})
    await db.progress_logs.delete_many({"user_id": user_id})
    await db.weekly_checkins.delete_many({"user_id": user_id})
    await db.reminders.delete_many({"user_id": user_id})
    await db.notifications.delete_many({"user_id": user_id})
    await db.community_posts.delete_many({"user_id": user_id})
    await db.timeline.delete_many({"user_id": user_id})
    await db.refresh_tokens.delete_many({"user_id": user_id})

    return {"message": "Your account and all associated data have been permanently deleted."}
