from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import json
import re

def _sanitize(text: str, max_len: int = 500) -> str:
    text = re.sub(r'(?i)(system\s*:|assistant\s*:|<<\s*SYS\s*>>|<\|.*?\|>)', '', text)
    text = re.sub(r'(?i)(ignore\s+(all\s+)?previous\s+instructions?|forget\s+(everything|all)|jailbreak|bypass)', '', text)
    return text.strip()[:max_len]

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb
from ai.llm_client import llm_client
from services.chat_service import apply_chat_side_effects
from services.notification_service import create_and_deliver_notification

router = APIRouter()

class WeeklyCheckinRequest(BaseModel):
    # Unified weekly check-in — 1-5 scale (1 = poor/low, 5 = excellent/high)
    energy: int = Field(..., ge=1, le=5)
    digestion: int = Field(..., ge=1, le=5)
    sleep: int = Field(..., ge=1, le=5)
    stress: Optional[int] = Field(None, ge=1, le=5)
    adherence: int = Field(..., ge=1, le=5)
    symptoms: List[str] = Field(default_factory=list)
    menstrual_phase: Optional[bool] = None
    disease_stage_updates: Optional[dict] = None
    what_felt_good: Optional[str] = Field(None, max_length=1000)

class WeeklyCheckinResponse(BaseModel):
    insight: str
    adapted_plans: List[str] = []

async def _grounded_insight(user, req, old_vikriti, new_vikriti, old_dom, new_dom, shifted, safe_felt_good) -> str:
    trend = f"shifted toward {new_dom}" if shifted else "held steady"
    prompt = f"""You are the Ayura AI Health Assistant reviewing a user's weekly check-in.
Constitution (Prakriti): {user.dominant_dosha}
Last week's imbalance (Vikriti): {old_vikriti}, dominant {old_dom}
This week's imbalance (Vikriti): {new_vikriti}, dominant {new_dom} — it {trend}
This week's self-ratings (1-5 scale, 1=poor 5=excellent): energy {req.energy}, digestion {req.digestion}, sleep {req.sleep}, plan adherence {req.adherence}
What felt good: {safe_felt_good}

Write a brief (1-2 sentence), warm, SPECIFIC insight grounded in this ACTUAL data — reference their real trend and ratings, not generic praise.
Respond ONLY with valid JSON: {{"insight": "..."}}"""
    try:
        resp = await llm_client.generate(
            prompt=prompt, system_prompt="You are an Ayurvedic AI. Reply in JSON.", json_mode=True, max_tokens=200)
        return json.loads(resp).get("insight") or "Thanks for checking in — your plans stay tuned to your latest reading."
    except Exception:
        return "Thanks for checking in — your plans stay tuned to your latest reading."


@router.post("/weekly", response_model=WeeklyCheckinResponse)
async def submit_weekly_checkin(req: WeeklyCheckinRequest, background_tasks: BackgroundTasks, user: UserDocument = Depends(get_current_user)):
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc)
    safe_symptoms = [_sanitize(s, max_len=100) for s in req.symptoms]
    safe_felt_good = _sanitize(req.what_felt_good or "", max_len=500)

    # 1. Save the raw weekly check-in
    await db.weekly_checkins.insert_one({
        "user_id": user.id, "energy": req.energy, "digestion": req.digestion,
        "sleep": req.sleep, "stress": req.stress, "adherence": req.adherence,
        "symptoms": req.symptoms, "what_felt_good": req.what_felt_good, "timestamp": now,
    })

    # 2. Record reported symptoms (so plan regeneration reflects them)
    if req.symptoms:
        await db.users.update_one(
            {"_id": user.id}, {"$addToSet": {"current_symptoms": {"$each": req.symptoms}}})
        user.current_symptoms = list({*(user.current_symptoms or []), *req.symptoms})

    # 3. Run the SAME Vikriti refinement as /profile/vikriti-checkin (unified loop)
    from services.vikriti_service import compute_vikriti_update, vikriti_shifted
    update, old_vikriti = compute_vikriti_update(
        user, symptoms=req.symptoms, sleep=req.sleep, digestion=req.digestion,
        stress=req.stress, menstrual_phase=req.menstrual_phase,
        disease_stage_updates=req.disease_stage_updates,
    )
    await db.users.update_one({"_id": user.id}, {"$set": update})
    for k, v in update.items():
        setattr(user, k, v)

    new_vikriti = update["vikriti_scores"]
    old_dom = max(old_vikriti, key=old_vikriti.get) if old_vikriti else None
    new_dom = update["vikriti_dominant"]
    shifted = vikriti_shifted(old_vikriti, new_vikriti)

    # 4. GROUNDED adaptation — regenerate only when the imbalance actually moved,
    #    and only plans the user already has. No shift → no (misleading) "adapted".
    plans_to_adapt: list[str] = []
    if shifted:
        from services.chat_service import fetch_active_plans
        existing = await fetch_active_plans(db, user.id)
        plans_to_adapt = [p for p in ("diet", "yoga", "medicines", "panchakarma") if p in existing]
        if plans_to_adapt:
            feedback = (f"Weekly check-in — Vikriti shifted {old_dom}→{new_dom}. "
                        f"Energy={req.energy}, Digestion={req.digestion}, Sleep={req.sleep}, Symptoms={safe_symptoms}")
            background_tasks.add_task(apply_chat_side_effects, db, user.id, [], plans_to_adapt, feedback)
            plan_names = ", ".join(p.title() for p in plans_to_adapt)
            background_tasks.add_task(
                create_and_deliver_notification, db, user.id,
                "Your plans were refreshed",
                f"Your imbalance moved toward {new_dom.title()}, so your {plan_names} plan(s) were updated.",
                "adaptation",
            )

    # 5. Insight grounded in the REAL trend
    insight = await _grounded_insight(user, req, old_vikriti, new_vikriti, old_dom, new_dom, shifted, safe_felt_good)
    return WeeklyCheckinResponse(insight=insight, adapted_plans=plans_to_adapt)


@router.get("/history")
async def get_checkin_history(
    limit: int = 12,
    user: UserDocument = Depends(get_current_user),
):
    """Return the user's past weekly check-ins, most recent first."""
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    cursor = db.weekly_checkins.find({"user_id": user.id}).sort("timestamp", -1).limit(min(limit, 52))
    history = []
    async for doc in cursor:
        ts = doc.get("timestamp")
        history.append({
            "energy":       doc.get("energy"),
            "digestion":    doc.get("digestion"),
            "sleep":        doc.get("sleep"),
            "adherence":    doc.get("adherence"),
            "symptoms":     doc.get("symptoms", []),
            "what_felt_good": doc.get("what_felt_good") or "",
            "timestamp":    ts.isoformat() if isinstance(ts, datetime) else str(ts),
        })
    return history
