"""
Ayura AI — Meal Log Routes

The diet plan's meals, as eaten. One document per (plan, week, day, slot) in
`db.meal_logs`; logging again edits it, and a null status removes it. What is logged
shapes the next diet plan (see `services/diet_log.py`).
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.diet_checkin import DIGESTION, HUNGER, PROBLEMS, RED_FLAGS, proposal, week_foods
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


async def _diet_doc(db, user_id: str, plan_id: str, projection=None):
    return await db.plan_history.find_one(
        {"user_id": user_id,
         "$or": [{"_id": plan_id}, {"plan_data.diet_plan.plan_id": plan_id}]},
        projection or {"plan_data.diet_plan.diet_weeks": 1}, sort=[("generated_at", -1)])


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
                              bmi_category=user.bmi_category, profile=_profile_bits(user))
    return {"adaptation": hist["adaptation"], "summary": hist["summary"]}


# ── Weekly check-in ──────────────────────────────────────────────────────────

class TroubleFood(BaseModel):
    food: str = Field(..., min_length=1, max_length=60)
    problem: Literal[PROBLEMS]  # type: ignore[valid-type]


class DietCheckinIn(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=120)
    week: int = Field(..., ge=1, le=4)
    hunger: Literal[HUNGER] = "right"  # type: ignore[valid-type]
    digestion: List[Literal[DIGESTION]] = Field(default_factory=list, max_length=4)  # type: ignore[valid-type]
    trouble_foods: List[TroubleFood] = Field(default_factory=list, max_length=8)
    red_flags: List[Literal[RED_FLAGS]] = Field(default_factory=list, max_length=5)  # type: ignore[valid-type]
    # Ticked by the patient after a reaction: a reaction reported once is not made a
    # standing allergy silently.
    add_allergies: List[str] = Field(default_factory=list, max_length=10)


def _profile_bits(user: UserDocument) -> dict:
    return {"age": user.age, "pregnancy_or_nursing": bool(user.pregnancy_or_nursing),
            "bmi_category": user.bmi_category}


@router.post("/checkins")
async def save_diet_checkin(
    body: DietCheckinIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    from schemas.preferences_schema import FOOD_ALLERGIES

    doc = await _diet_doc(db, user.id, body.plan_id,
                          {"plan_data.diet_plan.diet_weeks": 1, "rebuilds": 1})
    plan = ((doc or {}).get("plan_data") or {}).get("diet_plan")
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    served = {f["id"]: f for f in week_foods(plan, body.week)}
    unknown = [t.food for t in body.trouble_foods if t.food not in served]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Not in week {body.week} of this plan: {unknown}")
    bad = [a for a in body.add_allergies if a not in FOOD_ALLERGIES]
    if bad:
        raise HTTPException(status_code=422, detail=f"Unknown allergy: {bad}")

    now = datetime.now(timezone.utc)
    key = f"{user.id}:{body.plan_id}:{body.week}"
    record = {"_id": key, "user_id": user.id,
              **body.model_dump(exclude={"add_allergies"}), "updated_at": now}
    # Dedupe trouble foods, keeping the first problem named.
    seen, trouble = set(), []
    for t in record["trouble_foods"]:
        if t["food"] not in seen:
            seen.add(t["food"])
            trouble.append(t)
    record["trouble_foods"] = trouble
    await db.diet_checkins.replace_one({"_id": key, "user_id": user.id}, record, upsert=True)

    added: list[str] = []
    if body.add_allergies:
        prefs = await db.user_preferences.find_one({"user_id": user.id}, {"diet": 1}) or {}
        have = set((prefs.get("diet") or {}).get("food_allergies") or []) | set(user.allergies or [])
        added = [a for a in dict.fromkeys(body.add_allergies) if a not in have]
        if added:
            # Both places an allergy is declared, as onboarding and the diet form do;
            # the diet path reads their union (`diet_allergies`).
            if prefs.get("diet"):
                await db.user_preferences.update_one(
                    {"user_id": user.id},
                    {"$addToSet": {"diet.food_allergies": {"$each": added}},
                     "$set": {"updated_at": now}})
            await db.users.update_one({"_id": user.id},
                                      {"$addToSet": {"allergies": {"$each": added}}})
    return {"id": key, "allergies_added": added,
            "proposal": proposal(record, _profile_bits(user))}


@router.get("/checkins")
async def list_diet_checkins(
    plan_id: str = Query(..., min_length=1, max_length=120),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Every check-in on this plan, the foods served each week (for the picker), and
    what the latest check-in would change in the weeks still to come."""
    doc = await _diet_doc(db, user.id, plan_id,
                          {"plan_data.diet_plan.diet_weeks": 1, "rebuilds": 1})
    plan = ((doc or {}).get("plan_data") or {}).get("diet_plan")
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    out = []
    async for c in db.diet_checkins.find({"user_id": user.id, "plan_id": plan_id}):
        c["id"] = c.pop("_id")
        c.pop("user_id", None)
        for k in ("updated_at", "rebuilt_at"):
            if isinstance(c.get(k), datetime):
                c[k] = c[k].isoformat()
        out.append(c)
    out.sort(key=lambda c: c["week"])
    latest = out[-1] if out else None
    return {
        "checkins": out,
        # Week four too: nothing is left to rebuild, but a food reported then is kept
        # out of the next plan.
        "week_foods": {w: week_foods(plan, w) for w in (1, 2, 3, 4)},
        "proposal": proposal(latest, _profile_bits(user)),
        "rebuilds": [{**r, "at": r["at"].isoformat() if isinstance(r.get("at"), datetime) else r.get("at")}
                     for r in (doc or {}).get("rebuilds") or []],
    }


# ── Another dish ─────────────────────────────────────────────────────────────

class MealReplaceIn(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=120)
    week: int = Field(..., ge=1, le=4)
    day: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    slot: Literal["breakfast", "lunch", "snack", "dinner"]
    # Put back the meal the plan first served here.
    undo: bool = False


@router.post("/replace")
async def replace_meal_route(
    body: MealReplaceIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Another dish from this plan in place of one meal (`services/diet_meal_swap`).
    No generation is billed; the day is returned with its totals recomputed."""
    from services.diet_allowed_foods import allowed_foods
    from services.diet_brief_builder import diet_allergies, diet_conditions
    from services.diet_meal_swap import replace_meal, restore_meal
    from services.diet_week_generator import _scan

    doc = await _diet_doc(db, user.id, body.plan_id, {"plan_data.diet_plan": 1})
    plan = ((doc or {}).get("plan_data") or {}).get("diet_plan")
    if not plan or not plan.get("diet_weeks"):
        raise HTTPException(status_code=404, detail="Diet plan not found")
    idx = next((i for i, w in enumerate(plan["diet_weeks"])
                if w.get("week_number") == body.week), None)
    if idx is None:
        raise HTTPException(status_code=422, detail="No such week in this plan")

    try:
        if body.undo:
            day = restore_meal(plan, body.week, body.day, body.slot)
        else:
            prefs = (await db.user_preferences.find_one({"user_id": user.id}, {"diet": 1}) or {}).get("diet") or {}
            profile = user.model_dump()
            hist = await diet_history(db, user.id, goal=prefs.get("diet_goal"),
                                      bmi_category=user.bmi_category, profile=_profile_bits(user))
            profile["diet_log"] = hist["adaptation"]
            # Today's food list, and anything the plan's own screen excluded when it
            # was written (a rare disease's classified Apathya is not re-asked here).
            screen = allowed_foods(profile, prefs)
            excluded_then = set((plan.get("composition_report") or {}).get("excluded_foods") or {})
            allowed_ids = {f["id"] for f in screen["allowed"]} - excluded_then
            allergies = diet_allergies(profile, prefs)
            intolerances = prefs.get("food_intolerances") or []
            conditions = diet_conditions(profile, prefs)
            pregnant = bool(profile.get("pregnancy_or_nursing"))

            def is_safe(meal):
                probe = {"diet_weeks": [{"week_number": body.week,
                                         "daily_plan": {body.day: {body.slot: meal}}}]}
                return not _scan(probe, allergies, intolerances, prefs.get("dietary_type"),
                                 conditions, {}, pregnant)

            day = replace_meal(plan, body.week, body.day, body.slot,
                               allowed_ids=allowed_ids, is_safe=is_safe)
            if day is None:
                raise HTTPException(status_code=409,
                                    detail="No other dish in your plan suits this meal.")
    except KeyError:
        raise HTTPException(status_code=422, detail="No such meal in this plan")
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))

    update = {f"plan_data.diet_plan.diet_weeks.{idx}.daily_plan.{body.day}": day}
    # `weekly_plan` is week 1's days again, kept for older readers of the plan.
    if body.week == 1 and plan.get("weekly_plan"):
        update[f"plan_data.diet_plan.weekly_plan.{body.day}"] = day
    await db.plan_history.update_one({"_id": doc["_id"], "user_id": user.id}, {"$set": update})
    return {"week": body.week, "day_name": body.day, "day": day}
