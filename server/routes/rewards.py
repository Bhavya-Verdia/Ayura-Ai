"""
Ayura AI — Streak and badge routes. The rules are in `services/rewards.py`.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.rewards import evaluate

router = APIRouter()


@router.get("")
async def get_rewards(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    return await evaluate(db, user)


@router.post("/seen")
async def mark_seen(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """The client has shown the new badges; stop announcing them."""
    await db.user_badges.update_many({"user_id": user.id, "seen_at": None},
                                     {"$set": {"seen_at": datetime.now(timezone.utc)}})
    return {"ok": True}
