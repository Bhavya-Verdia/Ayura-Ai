"""
Ayura AI - Reminders Routes
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()


class ReminderRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    time: str = Field(..., description="HH:MM format")
    days: list[str] = Field(default_factory=list, description="List of days e.g. ['monday', 'wednesday']")
    reminder_type: str = Field(default="general", pattern="^(general|medication|exercise|meditation|checkin)$")
    is_active: bool = True


def _format_reminder(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "title": doc["title"],
        "time": doc["time"],
        "days": doc.get("days", []),
        "reminder_type": doc.get("reminder_type", "general"),
        "is_active": doc.get("is_active", True),
        "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
    }


@router.get("")
async def list_reminders(
    offset: int = 0,
    limit: int = 50,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """List all reminders for the current user."""
    cursor = db.reminders.find({"user_id": user.id}).sort("created_at", -1).skip(offset).limit(min(limit, 100))
    reminders = []
    async for doc in cursor:
        reminders.append(_format_reminder(doc))
    return reminders


@router.post("", status_code=201)
async def create_reminder(
    req: ReminderRequest,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Create a new reminder."""
    reminder_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": reminder_id,
        "user_id": user.id,
        "title": req.title,
        "time": req.time,
        "days": req.days,
        "reminder_type": req.reminder_type,
        "is_active": req.is_active,
        "created_at": now,
    }
    await db.reminders.insert_one(doc)
    return _format_reminder(doc)


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    req: ReminderRequest,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Update an existing reminder."""
    result = await db.reminders.update_one(
        {"_id": reminder_id, "user_id": user.id},
        {"$set": {
            "title": req.title, "time": req.time, "days": req.days,
            "reminder_type": req.reminder_type, "is_active": req.is_active,
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reminder not found")
    doc = await db.reminders.find_one({"_id": reminder_id})
    return _format_reminder(doc)


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Delete a reminder."""
    result = await db.reminders.delete_one({"_id": reminder_id, "user_id": user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reminder not found")
