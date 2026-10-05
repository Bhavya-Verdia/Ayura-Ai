"""
Ayura AI — Workout Log Routes

The gym plan's sets, as performed. One document per (plan, week, day, exercise)
in `db.workout_logs`; logging again edits it, and logging no sets removes it.
What is logged feeds the next plan's loads (see `services/workout_log.py`).
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.workout_log import block_summary, log_key

router = APIRouter()


class LoggedSet(BaseModel):
    kg: float = Field(0, ge=0, le=500, description="0 for a bodyweight set")
    reps: int = Field(..., ge=0, le=100)


class WorkoutLogIn(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=120)
    week: int = Field(..., ge=1, le=4)
    day: int = Field(..., ge=1, le=7)
    exercise_id: str = Field(..., min_length=1, max_length=120)
    sets: list[LoggedSet] = Field(default_factory=list, max_length=12)
    effort: Optional[Literal["easy", "right", "hard"]] = None


def _library_names() -> dict:
    from core.kb_cache import kb_cache
    from services.gym_plan_engine import gym_exercises
    return {e["id"]: e["name"] for e in (kb_cache.gym_exercises or gym_exercises)}


@router.post("/logs")
async def log_exercise(
    body: WorkoutLogIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    names = _library_names()
    if body.exercise_id not in names:
        raise HTTPException(status_code=422, detail="Unknown exercise")
    plan = await db.plan_history.find_one(
        {"_id": body.plan_id, "user_id": user.id, "plan_type": "gym"}, {"_id": 1})
    if not plan:
        raise HTTPException(status_code=404, detail="Gym plan not found")

    key = log_key(user.id, body.plan_id, body.week, body.day, body.exercise_id)
    sets = [s.model_dump() for s in body.sets if s.reps > 0]
    if not sets:
        await db.workout_logs.delete_one({"_id": key, "user_id": user.id})
        return {"id": key, "deleted": True}
    now = datetime.now(timezone.utc)
    doc = {
        "_id": key, "user_id": user.id, "plan_id": body.plan_id,
        "week": body.week, "day": body.day,
        "exercise_id": body.exercise_id, "exercise_name": names[body.exercise_id],
        "sets": sets, "effort": body.effort, "updated_at": now,
    }
    await db.workout_logs.replace_one({"_id": key, "user_id": user.id}, doc, upsert=True)
    return {"id": key, "deleted": False, "updated_at": now.isoformat()}


@router.get("/logs")
async def list_logs(
    plan_id: str = Query(..., min_length=1, max_length=120),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    cursor = db.workout_logs.find({"user_id": user.id, "plan_id": plan_id})
    out = []
    async for e in cursor:
        e["id"] = e.pop("_id")
        e.pop("user_id", None)
        if isinstance(e.get("updated_at"), datetime):
            e["updated_at"] = e["updated_at"].isoformat()
        out.append(e)
    return {"logs": out}


@router.get("/summary")
async def plan_summary(
    plan_id: str = Query(..., min_length=1, max_length=120),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    record = await db.plan_history.find_one(
        {"_id": plan_id, "user_id": user.id, "plan_type": "gym"})
    if not record:
        raise HTTPException(status_code=404, detail="Gym plan not found")
    data = record.get("plan_data") or {}
    entries = [e async for e in db.workout_logs.find({"user_id": user.id, "plan_id": plan_id})]
    return block_summary(data.get("gym_plan") or data, entries)
