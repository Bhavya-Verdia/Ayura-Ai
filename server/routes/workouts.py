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
from schemas.preferences_schema import GYM_INJURY_OPTIONS
from services.gym_week_adjust import FEELINGS, RED_FLAGS, week_adjustments
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


# ── The weekly check-in, and what it changes ─────────────────────────────────
#
# The log says what was lifted; it cannot say that a knee started hurting, that
# the week was spent ill, or that the sets were done through chest pain. Those
# are the three things a coach asks before writing the next week, and the next
# week's weights are not the only thing they change: pain goes onto the injury
# list both gym and yoga read, and a red flag stops the conversation about load.

class GymCheckinIn(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=120)
    week: int = Field(..., ge=1, le=4)
    feeling: Optional[Literal["too_easy", "right", "too_hard"]] = None
    pain_areas: list[str] = Field(default_factory=list, max_length=13)
    pain_note: Optional[str] = Field(None, max_length=300)
    unwell: bool = False
    red_flags: list[str] = Field(default_factory=list, max_length=4)
    # The person ticks "add these to my injuries" — a pain reported once is not
    # silently made a standing restriction on both plans.
    add_to_injuries: bool = False


async def _gym_plan(db, user_id: str, plan_id: str) -> dict:
    record = await db.plan_history.find_one(
        {"_id": plan_id, "user_id": user_id, "plan_type": "gym"})
    if not record:
        raise HTTPException(status_code=404, detail="Gym plan not found")
    data = record.get("plan_data") or {}
    return data.get("gym_plan") or data


@router.post("/checkins")
async def save_checkin(
    body: GymCheckinIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    unknown = [a for a in body.pain_areas if a not in GYM_INJURY_OPTIONS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown pain area: {unknown}")
    unknown = [f for f in body.red_flags if f not in RED_FLAGS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown symptom: {unknown}")
    await _gym_plan(db, user.id, body.plan_id)

    now = datetime.now(timezone.utc)
    key = f"{user.id}:{body.plan_id}:{body.week}"
    doc = {"_id": key, "user_id": user.id, **body.model_dump(exclude={"add_to_injuries"}),
           "updated_at": now}
    await db.gym_checkins.replace_one({"_id": key, "user_id": user.id}, doc, upsert=True)

    added: list[str] = []
    if body.add_to_injuries and body.pain_areas:
        prefs = await db.user_preferences.find_one({"user_id": user.id}) or {}
        have = set((prefs.get("gym") or {}).get("injuries") or []) | set(
            (prefs.get("yoga") or {}).get("injuries") or [])
        added = [a for a in body.pain_areas if a not in have]
        if added:
            # Both forms, as a save of either form does — but only into a form
            # that exists, since a partial document reads as preferences set.
            push = {f"{form}.injuries": {"$each": added}
                    for form in ("gym", "yoga") if prefs.get(form)}
            if push:
                await db.user_preferences.update_one(
                    {"user_id": user.id},
                    {"$addToSet": push, "$set": {"updated_at": now}})
            else:
                added = []
    # Newly declared injuries change what the gates allow, which the current
    # plan was built without — rebuilding is the only way it reflects them.
    return {"id": key, "injuries_added": added, "rebuild_recommended": bool(added)}


@router.get("/checkins")
async def list_checkins(
    plan_id: str = Query(..., min_length=1, max_length=120),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    out = []
    async for c in db.gym_checkins.find({"user_id": user.id, "plan_id": plan_id}):
        c["id"] = c.pop("_id")
        c.pop("user_id", None)
        if isinstance(c.get("updated_at"), datetime):
            c["updated_at"] = c["updated_at"].isoformat()
        out.append(c)
    return {"checkins": out, "feelings": list(FEELINGS),
            "red_flags": RED_FLAGS}


@router.get("/adjustments")
async def adjustments(
    plan_id: str = Query(..., min_length=1, max_length=120),
    week: int = Query(..., ge=1, le=4),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Next week's weights from last week's sets and check-in. Computed on read:
    the plan in history stays the prescription that was made."""
    plan = await _gym_plan(db, user.id, plan_id)
    entries = [e async for e in db.workout_logs.find(
        {"user_id": user.id, "plan_id": plan_id, "week": week - 1})]
    checkin = await db.gym_checkins.find_one(
        {"_id": f"{user.id}:{plan_id}:{week - 1}", "user_id": user.id})
    return week_adjustments(plan, entries, checkin, week)
