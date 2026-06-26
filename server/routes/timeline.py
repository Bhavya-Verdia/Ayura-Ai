"""
Ayura AI - Health Timeline Routes

Surfaces the per-user chronological health feed (db.timeline) consumed by the
Health Timeline page. Events are written by several producers:
  - progress_logged  (routes/progress.py)
  - symptom_logged / reminder_set  (services/chat_service.py)
  - plan_generated / adaptation_triggered  (services/audit_service.log_plan_generated)

The append-only `db.audit_log` remains the compliance trail; `db.timeline` is
the user-facing feed. This endpoint normalizes the (intentionally loose) stored
documents into a stable shape the frontend can render directly.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()

# Some producers store `details` as a bare string. Map the event type to the
# dict key the frontend renderer expects so those still display nicely.
_STRING_DETAIL_KEY = {
    "symptom_logged": "symptom",
    "reminder_set": "reminder",
}


def _normalize(doc: dict) -> dict:
    """Convert a raw timeline document into the stable API shape."""
    event_type = doc.get("event_type", "")

    raw_details = doc.get("details")
    if isinstance(raw_details, dict):
        details = raw_details
    elif isinstance(raw_details, str) and raw_details:
        details = {_STRING_DETAIL_KEY.get(event_type, "info"): raw_details}
    else:
        details = {}

    ts = doc.get("timestamp") or doc.get("created_at") or doc.get("date")
    timestamp = ts.isoformat() if isinstance(ts, datetime) else (ts if isinstance(ts, str) else None)

    return {
        "id": str(doc.get("_id")),
        "event_type": event_type,
        "timestamp": timestamp,
        "source": doc.get("source"),
        "details": details,
    }


@router.get("")
async def get_timeline(
    offset: int = 0,
    limit: int = 10,
    event_type: str | None = None,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Return a paginated slice of the user's health timeline, newest first."""
    query: dict = {"user_id": user.id}
    if event_type:
        query["event_type"] = event_type

    offset = max(0, offset)
    limit = min(max(1, limit), 50)

    cursor = (
        db.timeline.find(query)
        .sort("timestamp", -1)
        .skip(offset)
        .limit(limit)
    )
    return [_normalize(doc) async for doc in cursor]
