"""
Ayura AI — WhatsApp opt-in routes

A number is only used after its owner proves it: the user types it, ticks consent, and
enters the six-digit code sent to it. The code is stored hashed, expires in ten minutes,
allows five tries, and a new one can be asked for once a minute and five times a day.
Delivery rules are in `services/whatsapp_service.py`.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from config import settings
from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.whatsapp_service import available, mask, normalise_phone, send_template

router = APIRouter()

_CODE_TTL = timedelta(minutes=10)
_RESEND_AFTER = timedelta(seconds=60)
_MAX_TRIES = 5
_MAX_SENDS_PER_DAY = 5
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _hash(user_id: str, phone: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{user_id}:{phone}:{code}".encode(),
                    hashlib.sha256).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(ts):
    if isinstance(ts, datetime) and ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


class StartIn(BaseModel):
    phone: str = Field(..., min_length=7, max_length=24)
    consent: bool


class VerifyIn(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class SettingsIn(BaseModel):
    reminders: Optional[bool] = None
    daily: Optional[bool] = None
    daily_time: Optional[str] = None


def _status(user: UserDocument) -> dict:
    wa = getattr(user, "whatsapp", None) or {}
    return {
        "available": available(),
        "verified": bool(wa.get("verified_at")),
        "phone": mask(wa.get("phone")),
        "reminders": bool(wa.get("reminders")),
        "daily": bool(wa.get("daily")),
        "daily_time": wa.get("daily_time") or "07:00",
    }


@router.get("/status")
async def status(user: UserDocument = Depends(get_current_user)):
    return _status(user)


@router.post("/start")
async def start(
    body: StartIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    if not available():
        raise HTTPException(status_code=503, detail="WhatsApp messages are not available yet.")
    if not body.consent:
        raise HTTPException(status_code=422, detail="Tick the box to agree to WhatsApp messages.")
    phone = normalise_phone(body.phone)
    if not phone:
        raise HTTPException(status_code=422, detail="Enter a mobile number, with the country code if it is not Indian.")

    now = _now()
    prev = await db.whatsapp_verifications.find_one({"_id": user.id}) or {}
    last = _aware(prev.get("sent_at"))
    if last and now - last < _RESEND_AFTER:
        raise HTTPException(status_code=429, detail="Please wait a minute before asking for another code.")
    day = now.date().isoformat()
    sends = prev.get("sends", 0) if prev.get("sends_day") == day else 0
    if sends >= _MAX_SENDS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many codes today. Try again tomorrow.")

    code = f"{secrets.randbelow(900000) + 100000}"
    await db.whatsapp_verifications.update_one(
        {"_id": user.id},
        {"$set": {"user_id": user.id, "phone": phone, "code_hash": _hash(user.id, phone, code),
                  "expires_at": now + _CODE_TTL, "tries": 0, "sent_at": now,
                  "sends_day": day, "sends": sends + 1}},
        upsert=True)
    if not await send_template(phone, settings.WHATSAPP_TEMPLATE_OTP, [code], code_button=code):
        await db.whatsapp_verifications.delete_one({"_id": user.id})
        raise HTTPException(status_code=502, detail="Could not send the code. Check the number and try again.")
    return {"sent": True, "phone": mask(phone)}


@router.post("/verify")
async def verify(
    body: VerifyIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    doc = await db.whatsapp_verifications.find_one({"_id": user.id})
    if not doc:
        raise HTTPException(status_code=400, detail="Ask for a code first.")
    if _now() > _aware(doc["expires_at"]):
        raise HTTPException(status_code=400, detail="That code has expired. Ask for a new one.")
    if doc.get("tries", 0) >= _MAX_TRIES:
        raise HTTPException(status_code=429, detail="Too many attempts. Ask for a new code.")
    if not hmac.compare_digest(doc["code_hash"], _hash(user.id, doc["phone"], body.code)):
        await db.whatsapp_verifications.update_one({"_id": user.id}, {"$inc": {"tries": 1}})
        raise HTTPException(status_code=400, detail="That code is not right.")

    now = _now()
    wa = {"phone": doc["phone"], "verified_at": now, "consent_at": now,
          "reminders": True, "daily": False, "daily_time": "07:00"}
    await db.users.update_one({"_id": user.id}, {"$set": {"whatsapp": wa}})
    await db.whatsapp_verifications.delete_one({"_id": user.id})
    user.whatsapp = wa
    return _status(user)


@router.put("/settings")
async def update_settings(
    body: SettingsIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    wa = dict(getattr(user, "whatsapp", None) or {})
    if not wa.get("verified_at"):
        raise HTTPException(status_code=400, detail="Verify your WhatsApp number first.")
    changes = {}
    if body.reminders is not None:
        changes["reminders"] = body.reminders
    if body.daily is not None:
        changes["daily"] = body.daily
    if body.daily_time is not None:
        if not _TIME.match(body.daily_time):
            raise HTTPException(status_code=422, detail="Choose a time like 07:00.")
        changes["daily_time"] = body.daily_time
    if changes:
        await db.users.update_one({"_id": user.id}, {"$set": {f"whatsapp.{k}": v for k, v in changes.items()}})
        wa.update(changes)
    user.whatsapp = wa
    return _status(user)


@router.delete("")
async def stop(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Forget the number. Every WhatsApp message stops."""
    await db.users.update_one({"_id": user.id}, {"$unset": {"whatsapp": ""}})
    await db.whatsapp_verifications.delete_one({"_id": user.id})
    user.whatsapp = None
    return _status(user)
