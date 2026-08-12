"""
Ayura AI — Practice Session Routes

Records guided practice sessions run in the yoga session player. Until now the
yoga feature was a document: a four-week plan the user could read but that had
no idea whether anything in it was ever practised. Without that signal the
weekly check-in has to ask the user to estimate adherence from memory, and the
plan cannot adapt to what someone actually does.

Sessions land in `db.practice_sessions` (queryable history) and produce a
`practice_completed` event in `db.timeline` (the user-facing feed), matching how
progress and check-in events are already recorded.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()

# A session longer than this is a forgotten tab, not a practice. Recording it
# would poison the streak and the adherence average.
_MAX_SESSION_SECONDS = 4 * 60 * 60


class PracticeSessionLog(BaseModel):
    plan_id: str | None = None
    feature: str = Field("yoga", description="Which plan the session came from")
    week: int = Field(..., ge=1, le=4)
    day: int = Field(..., ge=1, le=7)
    duration_seconds: int = Field(..., ge=0, le=_MAX_SESSION_SECONDS)
    segments_total: int = Field(..., ge=0)
    segments_completed: int = Field(..., ge=0)
    completed: bool = Field(..., description="False if the user exited early")
    skipped_pose_ids: list[str] = Field(default_factory=list, max_length=60)


class PracticeSessionResponse(BaseModel):
    id: str
    logged_at: str
    current_streak_days: int
    sessions_this_week: int


def _completion_percent(log: PracticeSessionLog) -> int:
    if log.segments_total <= 0:
        return 100 if log.completed else 0
    return round(min(log.segments_completed / log.segments_total, 1.0) * 100)


async def _streak_days(db: AsyncIOMotorDatabase, user_id, today: datetime) -> int:
    """Consecutive days up to today with at least one session.

    Counted over distinct practice *days*, so two sessions in one day do not
    inflate the streak, and a session already logged today does not break it.
    """
    since = today - timedelta(days=60)
    cursor = db.practice_sessions.find(
        {"user_id": user_id, "started_at": {"$gte": since}},
        {"started_at": 1},
    )
    days = {d["started_at"].date() async for d in cursor if d.get("started_at")}
    if not days:
        return 0

    streak, cursor_day = 0, today.date()
    # A streak stays alive until yesterday's practice is also missing — otherwise
    # it would read as broken every morning before that day's session.
    if cursor_day not in days:
        cursor_day -= timedelta(days=1)
    while cursor_day in days:
        streak += 1
        cursor_day -= timedelta(days=1)
    return streak


@router.post("/session", response_model=PracticeSessionResponse)
async def log_practice_session(
    req: PracticeSessionLog,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Record a practice session the user ran in the session player."""
    if req.segments_completed > req.segments_total:
        raise HTTPException(400, "segments_completed cannot exceed segments_total")

    now = datetime.now(timezone.utc)
    started_at = now - timedelta(seconds=req.duration_seconds)

    doc = {
        "user_id": user.id,
        "plan_id": req.plan_id,
        "feature": req.feature,
        "week": req.week,
        "day": req.day,
        "duration_seconds": req.duration_seconds,
        "segments_total": req.segments_total,
        "segments_completed": req.segments_completed,
        "completion_percent": _completion_percent(req),
        "completed": req.completed,
        "skipped_pose_ids": req.skipped_pose_ids,
        "started_at": started_at,
        "logged_at": now,
    }
    result = await db.practice_sessions.insert_one(doc)

    await db.timeline.insert_one({
        "user_id": user.id,
        "event_type": "practice_completed",
        "source": req.feature,
        "details": {
            "feature": req.feature,
            "week": req.week,
            "day": req.day,
            "duration_minutes": round(req.duration_seconds / 60),
            "completion_percent": doc["completion_percent"],
            "completed": req.completed,
        },
        "timestamp": now,
    })

    week_start = now - timedelta(days=7)
    sessions_this_week = await db.practice_sessions.count_documents(
        {"user_id": user.id, "started_at": {"$gte": week_start}}
    )

    return PracticeSessionResponse(
        id=str(result.inserted_id),
        logged_at=now.isoformat(),
        current_streak_days=await _streak_days(db, user.id, now),
        sessions_this_week=sessions_this_week,
    )


@router.get("/summary")
async def practice_summary(
    days: int = 30,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Practice history for the dashboard and the weekly check-in."""
    days = max(1, min(days, 365))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    cursor = db.practice_sessions.find(
        {"user_id": user.id, "started_at": {"$gte": since}}
    ).sort("started_at", -1)
    sessions = [s async for s in cursor]

    total_seconds = sum(s.get("duration_seconds", 0) for s in sessions)
    finished = sum(1 for s in sessions if s.get("completed"))

    return {
        "window_days": days,
        "session_count": len(sessions),
        "completed_count": finished,
        "total_minutes": round(total_seconds / 60),
        "average_minutes": round(total_seconds / 60 / len(sessions)) if sessions else 0,
        "current_streak_days": await _streak_days(db, user.id, now),
        "recent": [
            {
                "week": s.get("week"),
                "day": s.get("day"),
                "feature": s.get("feature"),
                "duration_minutes": round(s.get("duration_seconds", 0) / 60),
                "completion_percent": s.get("completion_percent"),
                "completed": s.get("completed"),
                "started_at": s["started_at"].isoformat() if s.get("started_at") else None,
            }
            for s in sessions[:20]
        ],
    }
