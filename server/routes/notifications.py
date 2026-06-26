"""
Ayura AI - Notifications Routes
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()


@router.get("")
async def list_notifications(
    offset: int = 0,
    limit: int = 50,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """List notifications for the current user."""
    limit = min(limit, 100)
    cursor = db.notifications.find({"user_id": user.id}).sort("created_at", -1).skip(offset).limit(limit)
    notifications = []
    async for doc in cursor:
        notifications.append({
            "id": doc["_id"],
            "type": doc.get("type", "info"),
            "title": doc.get("title", ""),
            "message": doc.get("message", ""),
            "is_read": doc.get("is_read", False),
            "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
        })
    return notifications


@router.get("/unread-count")
async def get_unread_count(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Get count of unread notifications."""
    count = await db.notifications.count_documents({"user_id": user.id, "is_read": False})
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Mark a notification as read."""
    result = await db.notifications.update_one(
        {"_id": notification_id, "user_id": user.id},
        {"$set": {"is_read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Mark all notifications as read."""
    await db.notifications.update_many(
        {"user_id": user.id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Delete a single notification."""
    result = await db.notifications.delete_one({"_id": notification_id, "user_id": user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.delete("", status_code=200)
async def clear_notifications(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Clear all of the user's notifications."""
    result = await db.notifications.delete_many({"user_id": user.id})
    return {"deleted": result.deleted_count}
