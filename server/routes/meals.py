"""
Ayura AI — Meal Log Routes

The diet plan's meals, as eaten. One document per (plan, week, day, slot) in
`db.meal_logs`; logging again edits it, and a null status removes it. What is logged
shapes the next diet plan (see `services/diet_log.py`).
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.diet_log import SLOTS, diet_history, log_key, summarise

router = APIRouter()

_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class MealLogIn(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=120)
    week: int = Field(..., ge=1, le=4)
    day: Literal[_DAYS]  # type: ignore[valid-type]
    slot: Literal[SLOTS]  # type: ignore[valid-type]
    # None removes the log.
    status: Optional[Literal["eaten", "partly", "skipped", "swapped"]] = None
    # What was eaten instead. Free text, shown back to the patient only; it is not
    # parsed into foods, because a guess at what "had poha" contained is not a log.
    swapped_with: Optional[str] = Field(None, max_length=120)


async def _diet_doc(db, user_id: str, plan_id: str):
    return await db.plan_history.find_one(
        {"user_id": user_id,
         "$or": [{"_id": plan_id}, {"plan_data.diet_plan.plan_id": plan_id}]},
        {"plan_data.diet_plan.diet_weeks": 1}, sort=[("generated_at", -1)])


@router.post("/logs")
async def log_meal(
    body: MealLogIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    key = log_key(user.id, body.plan_id, body.week, body.day, body.slot)
    if body.status is None:
        await db.meal_logs.delete_one({"_id": key, "user_id": user.id})
        return {"id": key, "deleted": True}
    doc = await _diet_doc(db, user.id, body.plan_id)
    weeks = (((doc or {}).get("plan_data") or {}).get("diet_plan") or {}).get("diet_weeks")
    if not weeks:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    week = next((w for w in weeks if w.get("week_number") == body.week), None)
    meal = (((week or {}).get("daily_plan") or {}).get(body.day) or {}).get(body.slot)
    if not isinstance(meal, dict):
        raise HTTPException(status_code=422, detail="No such meal in this plan")
    now = datetime.now(timezone.utc)
    record = {
        "_id": key, "user_id": user.id, "plan_id": body.plan_id,
        "week": body.week, "day": body.day, "slot": body.slot, "status": body.status,
        "meal_name": meal.get("meal_name") or meal.get("name"),
        # The foods, copied now: the log must still mean something after the plan
        # it was made against is regenerated.
        "foods": [c.get("food") for c in meal.get("components") or [] if c.get("food")],
        "updated_at": now,
    }
    if body.status == "swapped" and body.swapped_with:
        record["swapped_with"] = body.swapped_with.strip()
    await db.meal_logs.replace_one({"_id": key, "user_id": user.id}, record, upsert=True)
    return {"id": key, "deleted": False, "updated_at": now.isoformat()}


@router.get("/logs")
async def get_meal_logs(
    plan_id: str = Query(..., min_length=1, max_length=120),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    logs = await db.meal_logs.find(
        {"user_id": user.id, "plan_id": plan_id}, {"user_id": 0}).to_list(length=200)
    for l in logs:
        if isinstance(l.get("updated_at"), datetime):
            l["updated_at"] = l["updated_at"].isoformat()
    return {"logs": logs, "summary": summarise(logs)}


@router.get("/adaptation")
async def get_adaptation(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """What the next diet plan will change because of the log — said before the
    patient regenerates, so the change is not a surprise."""
    prefs = await db.user_preferences.find_one({"user_id": user.id}, {"diet": 1}) or {}
    hist = await diet_history(db, user.id, goal=(prefs.get("diet") or {}).get("diet_goal"),
                              bmi_category=user.bmi_category)
    return {"adaptation": hist["adaptation"], "summary": hist["summary"]}
