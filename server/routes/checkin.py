from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import asyncio
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

router = APIRouter()

class WeeklyCheckinRequest(BaseModel):
    energy: int = Field(..., ge=1, le=10)
    digestion: int = Field(..., ge=1, le=10)
    sleep: int = Field(..., ge=1, le=10)
    adherence: int = Field(..., ge=1, le=10)
    symptoms: List[str] = Field(default_factory=list)
    what_felt_good: Optional[str] = Field(None, max_length=1000)

class WeeklyCheckinResponse(BaseModel):
    insight: str
    adapted_plans: List[str] = []

@router.post("/weekly", response_model=WeeklyCheckinResponse)
async def submit_weekly_checkin(req: WeeklyCheckinRequest, background_tasks: BackgroundTasks, user: UserDocument = Depends(get_current_user)):
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # 1. Save checkin to DB
    checkin_doc = {
        "user_id": user.id,
        "energy": req.energy,
        "digestion": req.digestion,
        "sleep": req.sleep,
        "adherence": req.adherence,
        "symptoms": req.symptoms,
        "what_felt_good": req.what_felt_good,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.weekly_checkins.insert_one(checkin_doc)

    # 2. Update user symptoms if any are reported
    if req.symptoms:
        await db.users.update_one(
            {"_id": user.id},
            {"$addToSet": {"current_symptoms": {"$each": req.symptoms}}}
        )

    # 3. Determine if adaptation is needed and generate insight
    safe_symptoms = [_sanitize(s, max_len=100) for s in req.symptoms]
    safe_felt_good = _sanitize(req.what_felt_good or "", max_len=500)

    prompt = f"""
You are the Ayura AI AI Health Assistant. The user just completed their weekly check-in.
USER PROFILE: Dosha: {user.dominant_dosha}

CHECK-IN SCORES (1-10, 10 is best):
- Energy: {req.energy}
- Digestion: {req.digestion}
- Sleep: {req.sleep}
- Plan Adherence: {req.adherence}

NEW SYMPTOMS REPORTED: {safe_symptoms}
WHAT FELT GOOD: {safe_felt_good}

TASK:
1. Provide a brief, encouraging "insight" (1-2 sentences) on their progress.
2. If their scores are low (<= 4) or they reported new symptoms, decide which plans need adaptation (gym, yoga, diet, panchakarma, remedies, medicines).

Respond ONLY with valid JSON:
{{
    "insight": "Your insight here",
    "plans_to_adapt": ["diet", "yoga"]
}}
"""
    try:
        response = await llm_client.generate(prompt=prompt, system_prompt="You are an Ayurvedic AI. Reply in JSON.", json_mode=True)
        resp_data = json.loads(response)
        insight = resp_data.get("insight", "Great job checking in this week!")
        plans_to_adapt = resp_data.get("plans_to_adapt", [])
    except Exception as e:
        insight = "Great job on your weekly check-in!"
        plans_to_adapt = []

    # 4. Trigger adaptation in background if needed
    if plans_to_adapt:
        feedback_text = f"Weekly checkin: Energy={req.energy}, Digestion={req.digestion}, Sleep={req.sleep}, Symptoms={safe_symptoms}"
        background_tasks.add_task(
            apply_chat_side_effects, db, user.id, [], plans_to_adapt, feedback_text
        )

    return WeeklyCheckinResponse(insight=insight, adapted_plans=plans_to_adapt)
