"""
Ayura AI - Community Feed Routes
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()


class CreatePostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


@router.get("")
async def list_community_posts(
    offset: int = 0,
    limit: int = 20,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """List community posts, newest first."""
    limit = min(limit, 50)
    cursor = db.community_posts.find({}).sort("created_at", -1).skip(offset).limit(limit)
    posts = []
    async for doc in cursor:
        posts.append({
            "id": doc["_id"],
            "author_name": doc.get("author_name", "Anonymous"),
            "content": doc["content"],
            "like_count": len(doc.get("likes", [])),
            "liked_by_me": user.id in doc.get("likes", []),
            "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
        })
    return posts


@router.post("", status_code=201)
async def create_post(
    req: CreatePostRequest,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Create a new community post."""
    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": post_id,
        "user_id": user.id,
        "author_name": user.name,
        "content": req.content,
        "likes": [],
        "created_at": now,
    }
    await db.community_posts.insert_one(doc)
    return {
        "id": post_id,
        "author_name": user.name,
        "content": req.content,
        "like_count": 0,
        "liked_by_me": False,
        "created_at": now.isoformat(),
    }


@router.post("/{post_id}/like")
async def toggle_like(
    post_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Toggle like on a community post."""
    post = await db.community_posts.find_one({"_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    likes = post.get("likes", [])
    if user.id in likes:
        await db.community_posts.update_one({"_id": post_id}, {"$pull": {"likes": user.id}})
        liked = False
        like_count = len(likes) - 1
    else:
        await db.community_posts.update_one({"_id": post_id}, {"$addToSet": {"likes": user.id}})
        liked = True
        like_count = len(likes) + 1

    return {"liked": liked, "like_count": like_count}


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Delete a post (only author can delete)."""
    post = await db.community_posts.find_one({"_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["user_id"] != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.community_posts.delete_one({"_id": post_id})
