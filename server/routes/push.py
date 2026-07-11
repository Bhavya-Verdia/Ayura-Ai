"""
Ayura AI - Web Push subscriptions
Stores per-device PushSubscription objects so the notification service can
light up a phone even when the app is closed. Delivery itself lives in
services/notification_service._send_push; this router only manages the
subscription lifecycle.
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from config import settings
from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str = Field(..., min_length=10)
    auth: str = Field(..., min_length=5)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(..., min_length=20, max_length=1000)
    keys: PushKeys
    expirationTime: float | None = None


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(..., min_length=20, max_length=1000)


@router.get("/vapid-public-key")
async def vapid_public_key(user: UserDocument = Depends(get_current_user)):
    """Application server key the browser needs to create a subscription.
    `enabled: false` tells the client to hide push UI entirely."""
    return {"enabled": bool(settings.VAPID_PUBLIC_KEY), "public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(
    sub: PushSubscriptionIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Upsert a device subscription. Keyed by endpoint: re-subscribing the same
    device (or the browser rotating the subscription) replaces the old row, and
    an endpoint can only ever belong to one user."""
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push is not configured on this server")
    await db.push_subscriptions.update_one(
        {"endpoint": sub.endpoint},
        {
            "$set": {
                "user_id": user.id,
                "subscription": sub.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )
    return {"subscribed": True}


@router.delete("/subscribe")
async def unsubscribe(
    req: PushUnsubscribeIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Remove a device subscription (only the caller's own)."""
    await db.push_subscriptions.delete_one({"endpoint": req.endpoint, "user_id": user.id})
    return {"subscribed": False}
