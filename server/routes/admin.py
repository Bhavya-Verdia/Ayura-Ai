"""
Admin diagnostics and operations.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.admin import require_admin_token
from core.metrics import metrics_registry
from database.mongodb import get_mongodb

router = APIRouter(dependencies=[Depends(require_admin_token)])


@router.get("/summary")
async def admin_summary(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    users = await db.users.count_documents({})
    onboarded = await db.users.count_documents({"onboarding_complete": True})
    plans = await db.plan_history.count_documents({})
    progress_logs = await db.progress_logs.count_documents({}) if "progress_logs" in await db.list_collection_names() else 0

    cursor = db.plan_history.find().sort("generated_at", -1).limit(10)
    recent_plans = await cursor.to_list(length=10)

    return {
        "counts": {
            "users": users,
            "onboarded_users": onboarded,
            "plans": plans,
            "progress_logs": progress_logs,
        },
        "recent_plans": [
            {
                "id": str(plan["_id"]),
                "user_id": str(plan["user_id"]),
                "generated_at": plan.get("generated_at", "").isoformat() if hasattr(plan.get("generated_at"), 'isoformat') else plan.get("generated_at"),
                "generation_method": plan.get("generation_method"),
                "model_used": plan.get("model_used"),
                "ratings": plan.get("plan_data", {}).get("ratings", {}),
                "safety_warnings": plan.get("plan_data", {}).get("safety_checks", {}).get("warnings", []),
            }
            for plan in recent_plans
        ],
        "metrics": metrics_registry.snapshot(),
    }


@router.get("/users")
async def admin_users(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    cursor = db.users.find().sort("created_at", -1).limit(100)
    users = await cursor.to_list(length=100)

    return [
        {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name"),
            "auth_provider": user.get("auth_provider"),
            "is_verified": user.get("is_verified", False),
            "onboarding_complete": user.get("onboarding_complete", False),
            "dominant_dosha": user.get("dominant_dosha"),
            "created_at": user.get("created_at", "").isoformat() if hasattr(user.get("created_at"), 'isoformat') else user.get("created_at"),
        }
        for user in users
    ]


@router.get("/feedback")
async def admin_feedback(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Retrieve all submitted user feedback."""
    cursor = db.feedback.find().sort("created_at", -1).limit(200)
    feedbacks = await cursor.to_list(length=200)

    # Batch resolve user emails
    user_ids = list(set(f["user_id"] for f in feedbacks))
    users_cursor = db.users.find({"_id": {"$in": user_ids}}, {"email": 1, "name": 1})
    user_map = {str(u["_id"]): u for u in await users_cursor.to_list(length=len(user_ids))}

    return [
        {
            "id": str(f["_id"]),
            "type": f.get("type"),
            "description": f.get("description"),
            "url": f.get("url"),
            "created_at": f.get("created_at", "").isoformat() if hasattr(f.get("created_at"), 'isoformat') else f.get("created_at"),
            "user": {
                "id": str(f["user_id"]),
                "email": user_map.get(str(f["user_id"]), {}).get("email", "Unknown"),
                "name": user_map.get(str(f["user_id"]), {}).get("name", "Unknown"),
            }
        }
        for f in feedbacks
    ]
