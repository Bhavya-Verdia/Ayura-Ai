"""
Ayura AI - Feedback Route
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import uuid

from schemas.feedback_schema import FeedbackCreate, FeedbackDocument
from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()

@router.post("", status_code=201)
async def submit_feedback(
    req: FeedbackCreate,
    user: UserDocument = Depends(get_current_user),
    db = Depends(get_mongodb),
):
    """Submit a new feedback report."""
    feedback_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    doc = {
        "_id": feedback_id,
        "user_id": user.id,
        "type": req.type.value,
        "description": req.description,
        "url": req.url,
        "created_at": now,
    }
    
    await db.feedback.insert_one(doc)
    
    return {"id": feedback_id, "status": "success"}
