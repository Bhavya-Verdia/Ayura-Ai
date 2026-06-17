"""
Ayura AI - Community Feed Routes
"""

import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import uuid

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()

# ─── Per-User Rate Limiter (5 posts / 60 min) ─────────────────────────────────

_POST_LIMIT = 5          # max posts per window
_POST_WINDOW = 3600      # 1-hour sliding window (seconds)
_user_post_times: dict[str, deque] = defaultdict(deque)


def _check_post_rate(user_id: str) -> None:
    """Raise 429 if the user has exceeded the posting rate limit."""
    now = time.monotonic()
    bucket = _user_post_times[user_id]
    # Evict timestamps outside the window
    while bucket and now - bucket[0] > _POST_WINDOW:
        bucket.popleft()
    if len(bucket) >= _POST_LIMIT:
        retry_after = max(1, int(_POST_WINDOW - (now - bucket[0])))
        raise HTTPException(
            status_code=429,
            detail=f"Too many posts. Please wait before posting again.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


# ─── Content Moderation ────────────────────────────────────────────────────────

# Minimal pattern-based filter — keeps the platform healthy without an external API.
_BLOCKED_PATTERNS = re.compile(
    r"\b("
    r"buy\s+(now|cheap|online)|"          # spam commerce
    r"click\s+here|visit\s+my\s+(site|link|profile)|"  # link spam
    r"make\s+money\s+fast|earn\s+\$|crypto\s+profit|"  # financial spam
    r"(?:http|ftp)s?://\S+"               # bare URLs (block all links)
    r")\b",
    re.IGNORECASE,
)

_REPEATED_CHARS = re.compile(r"(.)\1{9,}")  # same char repeated 10+ times → spam


def _moderate_content(content: str) -> None:
    """Raise 422 if the content violates community guidelines."""
    if _BLOCKED_PATTERNS.search(content):
        raise HTTPException(
            status_code=422,
            detail="Post contains content that is not allowed (spam, URLs, or promotional material).",
        )
    if _REPEATED_CHARS.search(content):
        raise HTTPException(
            status_code=422,
            detail="Post contains repetitive characters. Please write a meaningful message.",
        )


# ─── Routes ───────────────────────────────────────────────────────────────────

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
    # ── Safety gates ──────────────────────────────────────────────────────────
    _check_post_rate(user.id)   # rate limit: 5 posts / hour per user
    _moderate_content(req.content)  # content moderation

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
