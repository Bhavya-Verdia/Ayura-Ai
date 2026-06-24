"""
Ayura AI - Progress Tracking Routes
"""

from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import json
import uuid

from schemas.user_schema import UserDocument
from schemas.plan_schema import ProgressLogRequest, ProgressResponse
from routes.profile import get_current_user
from database.mongodb import get_mongodb
from ai.llm_client import llm_client
from core.cache import cache_manager

_SUMMARY_TTL = 14400  # 4 hours

router = APIRouter()


@router.post("/log")
async def log_progress(
    req: ProgressLogRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Log a daily progress entry."""
    now = datetime.now(timezone.utc)
    log_id = str(uuid.uuid4())

    log_doc = {
        "_id": log_id,
        "user_id": user.id,
        "date": now,
        "weight_kg": req.weight_kg,
        "adherence_percent": req.adherence_percent,
        "mood": req.mood,
        "plan_feedback": req.plan_feedback,
        "symptom_updates": req.symptom_updates or {},
    }
    await db.progress_logs.insert_one(log_doc)

    # Invalidate cached summary so next fetch reflects the new entry
    if cache_manager.redis_client:
        try:
            await cache_manager.redis_client.delete(f"ayura:progress_summary:{user.id}")
        except Exception:
            pass

    # Update user weight if provided
    if req.weight_kg:
        await db.users.update_one(
            {"_id": user.id},
            {"$set": {"weight_kg": req.weight_kg, "updated_at": now}}
        )

    # Log timeline event
    await db.timeline.insert_one({
        "user_id": user.id,
        "event_type": "progress_logged",
        "details": {
            "weight_kg": req.weight_kg,
            "adherence_percent": req.adherence_percent,
            "mood": req.mood,
        },
        "timestamp": now,
    })

    return {"id": log_id, "message": "Progress logged successfully", "logged_at": now.isoformat()}


@router.get("/summary", response_model=ProgressResponse)
async def get_progress_summary(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get a progress summary with trend analysis."""
    cache_key = f"ayura:progress_summary:{user.id}"
    if cache_manager.redis_client:
        try:
            cached = await cache_manager.redis_client.get(cache_key)
            if cached:
                return ProgressResponse(**json.loads(cached))
        except Exception:
            pass

    cursor = db.progress_logs.find({"user_id": user.id}).sort("date", -1).limit(30)
    logs = await cursor.to_list(length=30)

    if not logs:
        return ProgressResponse(
            current={"message": "No progress data yet. Log your first entry!"},
            trend="insufficient_data",
        )

    latest = logs[0]
    current = {
        "weight_kg": latest.get("weight_kg") or user.weight_kg,
        "bmi": user.bmi,
        "bmi_category": user.bmi_category,
        "mood": latest.get("mood"),
        "adherence_percent": latest.get("adherence_percent"),
        "last_logged": latest["date"].isoformat() if isinstance(latest["date"], datetime) else latest["date"],
        "total_entries": len(logs),
    }

    # Calculate trend from weight entries
    weight_entries = [(log["date"], log["weight_kg"]) for log in logs if log.get("weight_kg")]
    trend = "stable"
    if len(weight_entries) >= 3:
        recent_weights = [w for _, w in weight_entries[:5]]
        older_weights = [w for _, w in weight_entries[-5:]]
        avg_recent = sum(recent_weights) / len(recent_weights)
        avg_older = sum(older_weights) / len(older_weights)
        diff = avg_recent - avg_older
        if diff < -0.5:
            trend = "losing_weight"
        elif diff > 0.5:
            trend = "gaining_weight"
        else:
            trend = "stable"

    # Real consecutive-day streak: walk backwards from today counting unbroken logged days
    def _calc_streak(logs: list) -> int:
        logged_dates = set()
        for log in logs:
            raw = log.get("date")
            if isinstance(raw, datetime):
                logged_dates.add(raw.date())
        streak = 0
        check = date.today()
        while check in logged_dates:
            streak += 1
            check -= timedelta(days=1)
        return streak

    streak_data = {
        "current_streak_days": _calc_streak(logs),
        "total_entries": len(logs),
    }

    # LLM insight
    weekly_insight = None
    if len(logs) >= 3:
        try:
            adherence_vals = [l.get("adherence_percent") for l in logs[:7] if l.get("adherence_percent")]
            avg_adherence = round(sum(adherence_vals) / len(adherence_vals)) if adherence_vals else None
            mood_vals = [l.get("mood") for l in logs[:7] if l.get("mood")]
            prompt = f"""Generate a 1-sentence motivational wellness insight for a user.
            Current weight trend: {trend}. Average adherence: {avg_adherence}%. Recent moods: {mood_vals}.
            Dosha: {user.dominant_dosha}. Keep it positive and actionable."""
            weekly_insight = await llm_client.generate(prompt=prompt, max_tokens=100, temperature=0.7)
            weekly_insight = weekly_insight.strip()
        except Exception:
            weekly_insight = "Keep up the great work! Consistency is the key to lasting wellness."

    result = ProgressResponse(
        current=current,
        trend=trend,
        weekly_insight=weekly_insight,
        streak_data=streak_data,
    )
    if cache_manager.redis_client:
        try:
            await cache_manager.redis_client.setex(cache_key, _SUMMARY_TTL, result.model_dump_json())
        except Exception:
            pass
    return result


@router.get("/logs")
async def get_progress_logs(
    limit: int = 30,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Return the last N raw progress log entries for the authenticated user."""
    cursor = db.progress_logs.find({"user_id": user.id}).sort("date", -1).limit(min(limit, 90))
    logs = []
    async for doc in cursor:
        raw_date = doc.get("date")
        logs.append({
            "id": doc["_id"],
            "date": raw_date.isoformat() if isinstance(raw_date, datetime) else str(raw_date),
            "weight_kg": doc.get("weight_kg"),
            "adherence_percent": doc.get("adherence_percent"),
            "mood": doc.get("mood"),
            "plan_feedback": doc.get("plan_feedback") or "",
        })
    return logs
