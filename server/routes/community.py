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
            detail="Too many posts. Please wait before posting again.",
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


class ReportRequest(BaseModel):
    reason: str = Field(default="", max_length=300)


# Posts hit by this many distinct reporters are auto-hidden pending review.
_REPORT_HIDE_THRESHOLD = 3


@router.get("")
async def list_community_posts(
    offset: int = 0,
    limit: int = 20,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """List visible community posts, newest first (auto-hidden posts excluded)."""
    limit = min(limit, 50)
    cursor = db.community_posts.find({"hidden": {"$ne": True}}).sort("created_at", -1).skip(offset).limit(limit)
    posts = []
    async for doc in cursor:
        posts.append({
            "id": doc["_id"],
            "author_name": doc.get("author_name", "Anonymous"),
            "content": doc["content"],
            "like_count": len(doc.get("likes", [])),
            "liked_by_me": user.id in doc.get("likes", []),
            "is_mine": doc.get("user_id") == user.id,
            "reported_by_me": user.id in doc.get("reported_by", []),
            "comment_count": doc.get("comment_count", 0),
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
        "is_mine": True,
        "reported_by_me": False,
        "comment_count": 0,
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


@router.post("/{post_id}/report")
async def report_post(
    post_id: str,
    req: ReportRequest,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Flag a post. Once distinct reporters reach the threshold, it is auto-hidden."""
    post = await db.community_posts.find_one({"_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["user_id"] == user.id:
        raise HTTPException(status_code=400, detail="You cannot report your own post")

    reported_by = post.get("reported_by", [])
    if user.id in reported_by:
        return {"reported": True, "already_reported": True}

    new_count = len(reported_by) + 1
    update = {
        "$addToSet": {"reported_by": user.id},
        "$push": {"reports": {
            "user_id": user.id, "reason": req.reason[:300],
            "ts": datetime.now(timezone.utc),
        }},
    }
    hidden = new_count >= _REPORT_HIDE_THRESHOLD
    if hidden:
        update["$set"] = {"hidden": True}
    await db.community_posts.update_one({"_id": post_id}, update)
    return {"reported": True, "hidden": hidden}


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
    await db.community_comments.delete_many({"post_id": post_id})


class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=400)


@router.get("/{post_id}/comments")
async def list_comments(
    post_id: str,
    offset: int = 0,
    limit: int = 50,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """List comments on a post, oldest first."""
    limit = min(limit, 100)
    cursor = db.community_comments.find({"post_id": post_id}).sort("created_at", 1).skip(offset).limit(limit)
    out = []
    async for c in cursor:
        out.append({
            "id": c["_id"],
            "author_name": c.get("author_name", "Anonymous"),
            "content": c["content"],
            "is_mine": c.get("user_id") == user.id,
            "created_at": c["created_at"].isoformat() if isinstance(c["created_at"], datetime) else c["created_at"],
        })
    return out


@router.post("/{post_id}/comments", status_code=201)
async def add_comment(
    post_id: str,
    req: CommentRequest,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Add a comment to a post (content-moderated)."""
    post = await db.community_posts.find_one({"_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _moderate_content(req.content)

    comment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.community_comments.insert_one({
        "_id": comment_id, "post_id": post_id, "user_id": user.id,
        "author_name": user.name, "content": req.content, "created_at": now,
    })
    await db.community_posts.update_one({"_id": post_id}, {"$inc": {"comment_count": 1}})
    return {
        "id": comment_id, "author_name": user.name, "content": req.content,
        "is_mine": True, "created_at": now.isoformat(),
    }


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Delete a comment (author or admin only)."""
    comment = await db.community_comments.find_one({"_id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["user_id"] != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.community_comments.delete_one({"_id": comment_id})
    # Only decrement when positive so a retried/raced delete (or a legacy post whose
    # count drifted) can't drive comment_count negative.
    await db.community_posts.update_one(
        {"_id": comment["post_id"], "comment_count": {"$gt": 0}},
        {"$inc": {"comment_count": -1}},
    )
