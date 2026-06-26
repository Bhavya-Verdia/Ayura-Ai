"""
Ayura AI - Reminders Routes
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()

_TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"
_REMINDER_TYPES = "^(general|medication|exercise|meditation|checkin|yoga|diet|custom)$"
_VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


def _validate_tz(v: str) -> str:
    try:
        ZoneInfo(v)
    except Exception:
        raise ValueError(f"Invalid timezone: {v}")
    return v


def _validate_days(v: list[str]) -> list[str]:
    invalid = [d for d in v if d.lower() not in _VALID_DAYS]
    if invalid:
        raise ValueError(f"Invalid day(s): {', '.join(invalid)}")
    return [d.lower() for d in v]


class ReminderRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    time: str = Field(..., pattern=_TIME_PATTERN, description="HH:MM 24-hour format")
    days: list[str] = Field(default_factory=list, description="Lowercase day names, empty = every day")
    reminder_type: str = Field(default="general", pattern=_REMINDER_TYPES)
    is_active: bool = True
    timezone: str = Field(default="UTC", description="IANA timezone, e.g. Asia/Kolkata")
    description: str = Field(default="", max_length=500)

    _v_days = field_validator("days")(_validate_days)
    _v_tz = field_validator("timezone")(_validate_tz)


class ReminderUpdate(BaseModel):
    """Partial update — only the provided fields are changed (e.g. a toggle sends just is_active)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    time: Optional[str] = Field(None, pattern=_TIME_PATTERN)
    days: Optional[list[str]] = None
    reminder_type: Optional[str] = Field(None, pattern=_REMINDER_TYPES)
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("days")
    @classmethod
    def _v_days(cls, v):
        return _validate_days(v) if v is not None else v

    @field_validator("timezone")
    @classmethod
    def _v_tz(cls, v):
        return _validate_tz(v) if v is not None else v


def _format_reminder(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "title": doc["title"],
        "time": doc["time"],
        "days": doc.get("days", []),
        "reminder_type": doc.get("reminder_type", "general"),
        "is_active": doc.get("is_active", True),
        "timezone": doc.get("timezone", "UTC"),
        "description": doc.get("description", ""),
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
        "timezone": req.timezone,
        "description": req.description,
        "created_at": now,
    }
    await db.reminders.insert_one(doc)
    return _format_reminder(doc)


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    req: ReminderUpdate,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Update an existing reminder. Only the supplied fields change (partial update),
    so a toggle can send just `{is_active}` without re-sending title/time."""
    updates = req.model_dump(exclude_unset=True)
    if updates:
        result = await db.reminders.update_one(
            {"_id": reminder_id, "user_id": user.id},
            {"$set": updates},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reminder not found")
    doc = await db.reminders.find_one({"_id": reminder_id, "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Reminder not found")
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
