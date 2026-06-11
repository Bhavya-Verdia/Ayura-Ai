"""
Ayura AI - Plan Generation Routes (Full 4-tier AI pipeline wired)
"""

from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from arq import create_pool
from arq.connections import RedisSettings
import asyncio
from fastapi import BackgroundTasks

from config import settings
from database.mongodb import get_mongodb
from schemas.user_schema import UserDocument, PlanHistoryDocument
from schemas.plan_schema import PlanGenerationRequest, PlanRatingRequest, PlanResponse
from schemas.preferences_schema import (
    GymPreferences, YogaPreferences, DietPreferences,
    PanchakarmaPreferences, RemedyPreferences,
)
from routes.profile import get_current_user
from services.plan_diff import build_plan_diff
from services.audit_service import log_plan_generated
from core.cache import cache_manager
from core.kb_cache import kb_cache


import hashlib
import json

async def _check_plan_cache(db: AsyncIOMotorDatabase, user_id: str, plan_type: str, user_profile: dict, feature_prefs: dict, force_regenerate: bool):
    if force_regenerate:
        return None, None
        
    relevant_data = {
        "dosha": user_profile.get("dominant_dosha"),
        "pregnancy": user_profile.get("pregnancy_or_nursing"),
        "allergies": user_profile.get("allergies"),
        "symptoms": user_profile.get("current_symptoms"),
        "injuries": user_profile.get("injuries_or_limitations"),
        "feature_prefs": feature_prefs
    }
    pref_hash = hashlib.sha256(json.dumps(relevant_data, sort_keys=True).encode()).hexdigest()
    
    latest_plan = await db.plan_history.find_one(
        {"user_id": user_id, "plan_type": plan_type, "preference_hash": pref_hash},
        sort=[("generated_at", -1)]
    )
    if latest_plan:
        return latest_plan.get("plan_data", {}).get(f"{plan_type}_plan", latest_plan.get("plan_data")), pref_hash
    return None, pref_hash


router = APIRouter()

PLAN_DATA_KEYS = {
    "routine": "routine_plan",
    "gym": "gym_plan",
    "yoga": "yoga_plan",
    "diet": "diet_plan",
    "panchakarma": "panchakarma_plan",
    "remedies": "home_remedies",
    "medicines": "medicines",
}

# ─── Per-User Plan Generation Lock ────────────────────────────────────────────

async def _acquire_plan_lock(user_id: str, plan_type: str, ttl: int = 300) -> bool:
    """Try to acquire a Redis lock for plan generation. Returns False if already locked.

    TTL defaults to 5 minutes — long enough for any plan generation to complete.
    Falls back to True (no lock) if Redis is unavailable.
    """
    try:
        if cache_manager.redis_client is None:
            await cache_manager.connect()
        if cache_manager.redis_client:
            lock_key = f"plan_lock:{user_id}:{plan_type}"
            acquired = await cache_manager.redis_client.set(lock_key, "1", nx=True, ex=ttl)
            return bool(acquired)
    except Exception as e:
        from core.logger import logger
        logger.warning(f"Redis plan lock failed ({e}); falling back to no-lock")
    return True  # no Redis → allow (graceful degradation)


async def _release_plan_lock(user_id: str, plan_type: str) -> None:
    """Release the per-user plan generation lock."""
    try:
        if cache_manager.redis_client:
            await cache_manager.redis_client.delete(f"plan_lock:{user_id}:{plan_type}")
    except Exception:
        pass


# ─── ARQ Connection Pool ──────────────────────────────────────────────────────

_arq_pool = None

async def get_arq_pool():
    """Get or create the ARQ Redis connection pool for background jobs."""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379"))
    return _arq_pool

# ─── Feature Preferences Loader ──────────────────────────────────────────────

async def _load_feature_preferences(db: AsyncIOMotorDatabase, user_id: str, plan_type: str) -> dict:
    """
    Load saved feature-specific preferences for the given plan type.
    Falls back to schema defaults if the user hasn't set preferences yet.
    Returns a flat dict ready to merge into user_profile.
    """
    doc = await db.user_preferences.find_one({"user_id": user_id}) or {}

    # Map plan_type to storage key and schema
    schema_map = {
        "gym": ("gym", GymPreferences),
        "yoga": ("yoga", YogaPreferences),
        "diet": ("diet", DietPreferences),
        "panchakarma": ("panchakarma", PanchakarmaPreferences),
        "remedies": ("remedies", RemedyPreferences),
        "medicines": ("remedies", RemedyPreferences),   # shared
        "holistic": (None, None),
    }

    storage_key, schema_cls = schema_map.get(plan_type, (None, None))
    if storage_key is None or schema_cls is None:
        return {}

    saved = doc.get(storage_key)
    if saved:
        try:
            prefs = schema_cls(**saved)
        except Exception:
            prefs = schema_cls()  # fall back to defaults on invalid data
    else:
        prefs = schema_cls()  # use defaults

    return prefs.model_dump()


# ─── Background Job Runner ────────────────────────────────────────────────────

async def _run_plan_job(
    ctx: dict,
    job_id: str,
    plan_type: str,
    user_id: str,
    req_mode: str,
    req_feedback: str | None,
    req_previous_plan_id: str | None,
    user_profile: dict,
) -> None:
    """Background worker: runs AI plan generation and writes result to plan_jobs.
    
    Called via ARQ worker.
    Stores job status (pending → running → done | failed) in plan_jobs collection.
    """
    db = get_mongodb()
    try:
        await db.plan_jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}}
        )

        rating_prefs = await _get_rating_preferences(db, user_id)
        user_profile["rating_preferences"] = rating_prefs

        PLAN_TIMEOUT = settings.PLAN_TIMEOUT_SECONDS
        final_state: dict = {}

        if req_mode == "agentic":
            if plan_type == "holistic":
                from ai.agents.plan_graph import plan_graph
                previous = await _get_plan_record_for_adaptation(db, user_id, req_previous_plan_id) if req_feedback else None
                previous_data = previous.get("plan_data", {}) if previous else {}
                initial_state = {
                    "user_profile": user_profile,
                    "ml_analysis": {}, "rag_context": {},
                    "gym_plan": previous_data.get("gym_plan"),
                    "yoga_plan": previous_data.get("yoga_plan"),
                    "diet_plan": previous_data.get("diet_plan"),
                    "panchakarma_plan": previous_data.get("panchakarma_plan"),
                    "home_remedies": previous_data.get("home_remedies"),
                    "medicines": previous_data.get("medicines"),
                    "seasonal_guidance": previous_data.get("seasonal_guidance"),
                    "daily_tip": previous_data.get("daily_tip"),
                    "health_risks": [], "safety_checks": {}, "model_used": None,
                    "errors": [], "feedback": req_feedback, "is_adaptation": bool(req_feedback),
                    "adaptation_summary": None, "other_plans_context": None,
                }
                final_state = await asyncio.wait_for(plan_graph.ainvoke(initial_state), timeout=PLAN_TIMEOUT)
                full_plan_data = {
                    "user_summary": {"name": user_profile.get("name"), "dominant_dosha": user_profile.get("dominant_dosha")},
                    "gym_plan": final_state.get("gym_plan"),
                    "yoga_plan": final_state.get("yoga_plan"),
                    "diet_plan": final_state.get("diet_plan"),
                    "panchakarma_plan": final_state.get("panchakarma_plan"),
                    "home_remedies": final_state.get("home_remedies"),
                    "medicines": final_state.get("medicines"),
                    "seasonal_guidance": final_state.get("seasonal_guidance"),
                    "daily_tip": final_state.get("daily_tip"),
                    "health_risks": final_state.get("health_risks", []),
                    "safety_checks": final_state.get("safety_checks", {}),
                    "adaptation_summary": final_state.get("adaptation_summary"),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generation_method": req_mode,
                    "model_used": final_state.get("model_used"),
                }
                if req_feedback and previous:
                    full_plan_data["source_plan_id"] = previous["_id"]
                    full_plan_data["version_diff"] = build_plan_diff(previous.get("plan_data"), full_plan_data)
            else:
                from ai.agents.plan_graph import generate_single_plan
                other_plans_context = await _fetch_other_plans(db, user_id, plan_type)
                final_state = await asyncio.wait_for(
                    generate_single_plan(plan_type, user_profile, other_plans_context),
                    timeout=PLAN_TIMEOUT
                )
                plan_data_key = PLAN_DATA_KEYS[plan_type]
                full_plan_data = {
                    "user_summary": {"name": user_profile.get("name"), "dominant_dosha": user_profile.get("dominant_dosha")},
                    plan_data_key: final_state.get(plan_data_key),
                    "health_risks": final_state.get("health_risks", []),
                    "safety_checks": final_state.get("safety_checks", {}),
                    "adaptation_summary": final_state.get("adaptation_summary"),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generation_method": req_mode,
                    "model_used": final_state.get("model_used"),
                }
                if req_feedback:
                    previous = await _get_plan_record_for_adaptation(db, user_id, req_previous_plan_id)
                    if previous:
                        full_plan_data["source_plan_id"] = previous["_id"]
                        full_plan_data["version_diff"] = build_plan_diff(previous.get("plan_data"), full_plan_data)
        else:
            plan_data_key = PLAN_DATA_KEYS.get(plan_type, "gym_plan")
            empty_value = [] if plan_data_key in {"home_remedies", "medicines"} else {}
            full_plan_data = {
                "user_summary": {"name": user_profile.get("name"), "dominant_dosha": user_profile.get("dominant_dosha")},
                plan_data_key: empty_value,
                "health_risks": [], "safety_checks": {"generation_mode": "rule_based"},
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generation_method": req_mode, "model_used": "rule_based",
            }

        # Persist plan to history
        plan_id = str(uuid.uuid4())
        cache_params = {
            "user_id": user_id, "mode": req_mode, "feedback": req_feedback,
            "goal": user_profile.get("goal"),
            "dominant_dosha": user_profile.get("dominant_dosha"),
            "medical_history": user_profile.get("medical_history"),
        }
        if not req_feedback:
            await cache_manager.set_plan(plan_type, cache_params, full_plan_data)

        history = PlanHistoryDocument(
            _id=plan_id, user_id=user_id, plan_type=plan_type,
            generation_method=req_mode,
            model_used=full_plan_data.get("model_used"),
            plan_data=full_plan_data,
            generated_at=datetime.now(timezone.utc)
        )
        await db.plan_history.insert_one(history.model_dump(by_alias=True))
        
        # Audit logging for ALL plans (especially medicines/remedies)
        await log_plan_generated(
            db=db,
            user_id=user_id,
            plan_id=plan_id,
            plan_type=plan_type,
            model_used=full_plan_data.get("model_used"),
            is_adaptation=req_feedback is not None
        )

        # Mark job done
        full_plan_data["id"] = plan_id
        await db.plan_jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "done",
                "plan_id": plan_id,
                "result": full_plan_data,
                "completed_at": datetime.now(timezone.utc),
            }}
        )
    except Exception as exc:
        from core.logger import logger
        logger.error("Plan job %s failed: %s", job_id, exc)
        await db.plan_jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "failed",
                "error": str(exc)[:500],
                "completed_at": datetime.now(timezone.utc),
            }}
        )
    finally:
        user_id_from_profile = user_profile.get("_user_id", user_id)
        await _release_plan_lock(user_id_from_profile, plan_type)


# ─── Plan generation entry point (async job) ──────────────────────────────────

async def _enqueue_plan(
    plan_type: str,
    req: PlanGenerationRequest,
    user: UserDocument,
    db: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks
) -> dict:
    """Common handler: validates, loads preferences, checks cache, acquires lock, enqueues background job."""
    if not user.onboarding_complete:
        raise HTTPException(status_code=400, detail="Please complete onboarding first")

    # ── Pregnancy Safety Gate ─────────────────────────────────────────────────
    # Block sensitive features BEFORE any LLM call if user is pregnant/nursing
    PREGNANCY_BLOCKED_FEATURES = {"panchakarma", "remedies", "medicines"}
    if user.pregnancy_or_nursing and plan_type in PREGNANCY_BLOCKED_FEATURES:
        raise HTTPException(
            status_code=403,
            detail=(
                f"The {plan_type} feature is not available during pregnancy or nursing. "
                "Please consult your healthcare provider for personalised guidance."
            )
        )

    # ── Load Feature-Specific Preferences ────────────────────────────────────
    feature_prefs = await _load_feature_preferences(db, user.id, plan_type)

    # Extract the per-feature goal (e.g. gym_goal, yoga_goal, diet_goal)
    GOAL_FIELDS = {
        "gym": "gym_goal",
        "yoga": "yoga_goal",
        "diet": "diet_goal",
        "panchakarma": "panchakarma_goal",
    }
    feature_goal_key = GOAL_FIELDS.get(plan_type)
    feature_goal = feature_prefs.get(feature_goal_key) if feature_goal_key else None

    # ── Build User Profile Dict ───────────────────────────────────────────────
    user_profile = {
        "_user_id": user.id,
        "name": user.name,
        "gender": user.gender,
        "age": user.age,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "bmi": user.bmi,
        "bmi_category": user.bmi_category,
        "dosha_scores": user.dosha_scores,
        "dominant_dosha": user.dominant_dosha,
        "secondary_dosha": user.secondary_dosha,
        "dosha_confidence": user.dosha_confidence,
        "medical_history": user.medical_history or [],
        # Hard-exclusion lists — applied deterministically, never passed to LLM alone
        "allergies": user.allergies or [],
        "injuries_or_limitations": user.injuries_or_limitations or [],
        "current_symptoms": user.current_symptoms or [],
        "current_medications": user.current_medications or [],
        "fitness_level": user.fitness_level or "beginner",
        "activity_level": user.activity_level or "moderate",
        # Lifestyle signals
        "stress_level": user.stress_level,
        "digestion_quality": user.digestion_quality,
        "sleep_quality": user.sleep_quality,
        # Safety flags
        "pregnancy_or_nursing": user.pregnancy_or_nursing or False,
        # Deprecated global goal — kept for cache compatibility
        "goal": user.goal,
        # Per-feature goal (primary driver for this plan type)
        "feature_goal": feature_goal,
        # All feature-specific preferences merged in
        "feature_preferences": feature_prefs,
        "rating_preferences": {},  # loaded inside the background job
    }

    # ── Cache Lookup ──────────────────────────────────────────────────────────
    cache_params = {
        "user_id": user.id,
        "mode": req.mode,
        "feedback": req.feedback,
        # Use per-feature goal for cache key when available, fall back to global
        "goal": feature_goal or user.goal,
        "dominant_dosha": user.dominant_dosha,
        "medical_history": user.medical_history,
        # Include key preference fields in cache key so changed prefs bust cache
        "feature_prefs_hash": str(sorted(feature_prefs.items())) if feature_prefs else "",
    }

    if not req.feedback:
        cached_plan = await cache_manager.get_plan(plan_type, cache_params)
        if cached_plan:
            cached_plan["generated_at"] = datetime.now(timezone.utc).isoformat()
            plan_id = str(uuid.uuid4())
            history = PlanHistoryDocument(
                _id=plan_id, user_id=user.id, plan_type=plan_type,
                generation_method=req.mode,
                model_used=cached_plan.get("model_used"),
                plan_data=cached_plan,
                generated_at=datetime.now(timezone.utc)
            )
            await db.plan_history.insert_one(history.model_dump(by_alias=True))
            return {"job_id": None, "status": "done", "plan_id": plan_id, "result": {**cached_plan, "id": plan_id}}

    # ── Acquire Lock ──────────────────────────────────────────────────────────
    acquired = await _acquire_plan_lock(user.id, plan_type)
    if not acquired:
        raise HTTPException(
            status_code=409,
            detail=f"A {plan_type} plan is already being generated for your account. Please wait."
        )

    # ── Create Job Record ─────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())
    await db.plan_jobs.insert_one({
        "_id": job_id,
        "user_id": user.id,
        "plan_type": plan_type,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    # ── Schedule Background Generation ────────────────────────────────────────
    background_tasks.add_task(
        _run_plan_job,
        {}, job_id, plan_type, user.id, req.mode, req.feedback,
        req.previous_plan_id, user_profile
    )

    return {"job_id": job_id, "status": "pending", "plan_id": None, "result": None}


async def _get_plan_record_for_adaptation(
    db: AsyncIOMotorDatabase,
    user_id: str,
    previous_plan_id: str | None = None,
) -> dict | None:
    """Load the historical plan used as the source for an adaptation request."""
    if previous_plan_id:
        return await db.plan_history.find_one({"_id": previous_plan_id, "user_id": user_id})
    else:
        cursor = db.plan_history.find({"user_id": user_id}).sort("generated_at", -1).limit(1)
        plans = await cursor.to_list(length=1)
        return plans[0] if plans else None


async def _get_rating_preferences(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    cursor = db.plan_history.find({"user_id": user_id}).sort("generated_at", -1).limit(10)
    plans = await cursor.to_list(length=10)
    liked = []
    disliked = []
    notes = []
    for plan in plans:
        for section, rating in (plan.get("plan_data", {}).get("ratings") or {}).items():
            score = rating.get("score")
            note = rating.get("note")
            if score and score >= 4:
                liked.append(section)
            elif score and score <= 2:
                disliked.append(section)
            if note:
                notes.append({"section": section, "score": score, "note": note})
    return {
        "liked_sections": sorted(set(liked)),
        "disliked_sections": sorted(set(disliked)),
        "recent_notes": notes[:5],
    }


async def _fetch_other_plans(db: AsyncIOMotorDatabase, user_id: str, current_type: str) -> dict:
    context = {}
    types = ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]
    for t in types:
        if t != current_type:
            cursor = db.plan_history.find({"user_id": user_id, "plan_type": t}).sort("generated_at", -1).limit(1)
            plans = await cursor.to_list(length=1)
            if plans:
                context[f"{t}_plan"] = plans[0].get("plan_data", {})
    return context


# --- Route Handlers (return job_id instantly) ---

@router.post("/yoga")
async def generate_yoga_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.yoga_plan_engine import generate_yoga_plan as engine_generate
    from yoga_plan_enricher import enrich_yoga_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("yoga"):
        raise HTTPException(status_code=422, detail="Complete yoga preferences first")
        
    yoga_prefs = prefs_doc.get("yoga")
    is_prenatal = user.pregnancy_or_nursing
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "yoga", user_profile, yoga_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    if is_prenatal:
        yoga_poses = [p for p in kb_cache.yoga_poses if p.get("pregnancy_safe") == True]
    else:
        yoga_poses = kb_cache.yoga_poses
    pranayama_list = kb_cache.pranayama
    raw_plan = engine_generate(user_profile, yoga_prefs, yoga_poses, pranayama_list)
    enriched_plan = await enrich_yoga_plan(raw_plan, user_profile, yoga_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "services.yoga_plan_engine")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="yoga",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={
            "yoga_plan": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan


@router.post("/diet")
async def generate_diet_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.diet_plan_engine import generate_diet_plan as engine_generate
    from diet_plan_enricher import enrich_diet_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("diet"):
        raise HTTPException(status_code=422, detail="Complete diet preferences first")
        
    diet_prefs = prefs_doc.get("diet")
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "diet", user_profile, diet_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    diet_foods = kb_cache.diet_foods
    raw_plan = engine_generate(user_profile, diet_prefs, diet_foods)
    enriched_plan = await enrich_diet_plan(raw_plan, user_profile, diet_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "services.diet_plan_engine")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="diet",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={
            "diet_plan": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan


@router.post("/routine")
async def generate_routine_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.routine_engine import generate_routine_plan as engine_generate
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("diet"):
        raise HTTPException(status_code=422, detail="Complete diet preferences first to build your daily routine")
        
    diet_prefs = prefs_doc.get("diet")
    prefs_to_pass = {"diet": diet_prefs}
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "routine", user_profile, prefs_to_pass, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    diet_foods = kb_cache.diet_foods
    
    # Sync generation
    raw_plan = engine_generate(user_profile, prefs_to_pass, diet_foods)
    
    plan_id = raw_plan.get("plan_id")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="routine",
        generation_method="rule_based",
        model_used="services.routine_engine",
        preference_hash=pref_hash,
        plan_data={
            "routine_plan": raw_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return raw_plan

@router.post("/gym")
async def generate_gym_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.gym_plan_engine import generate_gym_plan as engine_generate
    from gym_plan_enricher import enrich_gym_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("gym"):
        raise HTTPException(status_code=422, detail="Complete gym preferences first")
        
    gym_prefs = prefs_doc.get("gym")
    is_prenatal = user.pregnancy_or_nursing
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "gym", user_profile, gym_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    if is_prenatal:
        gym_exercises = [e for e in kb_cache.gym_exercises if e.get("pregnancy_safe") == True]
    else:
        gym_exercises = kb_cache.gym_exercises
    raw_plan = engine_generate(user_profile, gym_prefs, gym_exercises)
    enriched_plan = await enrich_gym_plan(raw_plan, user_profile, gym_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "services.gym_plan_engine")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="gym",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={
            "gym_plan": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan


@router.post("/panchakarma")
async def generate_panchakarma_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.panchakarma_engine import generate_panchakarma_plan as engine_generate
    from panchakarma_enricher import enrich_panchakarma_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("panchakarma"):
        raise HTTPException(status_code=422, detail="Complete panchakarma preferences first")
        
    panchakarma_prefs = prefs_doc.get("panchakarma")
    is_prenatal = user.pregnancy_or_nursing
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "panchakarma", user_profile, panchakarma_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    if is_prenatal:
        panchakarma_therapies = [t for t in kb_cache.panchakarma_protocols if t.get("pregnancy_safe") == True]
    else:
        panchakarma_therapies = kb_cache.panchakarma_protocols
    raw_plan = engine_generate(user_profile, panchakarma_prefs, panchakarma_therapies)
    enriched_plan = await enrich_panchakarma_plan(raw_plan, user_profile, panchakarma_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "services.panchakarma_engine")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="panchakarma",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={
            "panchakarma_plan": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan


@router.post("/remedies")
async def generate_remedies_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.remedy_engine import filter_remedies, build_remedy_plan
    from services.remedy_enricher import enrich_remedies_plan
    
    user_profile = user.model_dump()
    
    if "symptoms" not in req:
        raise HTTPException(status_code=422, detail="Request body must contain 'symptoms' list")
        
    # 1. Engine Filter
    filtered_remedies = filter_remedies(user_profile, req)
    
    # 2. Engine Build
    raw_plan = build_remedy_plan(filtered_remedies, user_profile, req)
    
    # 3. LLM Enrichment
    enriched_plan = await enrich_remedies_plan(raw_plan, user_profile)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "rule_based")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="remedies",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=None,
        plan_data=enriched_plan,
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    from services.audit_service import log_plan_generated
    await log_plan_generated(db, user.id, "remedies")
    
    return enriched_plan


@router.post("/medicines")
async def generate_medicines_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.remedy_engine import generate_medicines_plan as engine_generate
    from remedy_enricher import enrich_medicines_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})
    
    if not prefs_doc or not prefs_doc.get("remedy"):
        raise HTTPException(status_code=422, detail="Complete medicines preferences first")
        
    medicines_prefs = prefs_doc.get("remedy")
    is_prenatal = user.pregnancy_or_nursing
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "medicines", user_profile, medicines_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    if is_prenatal:
        ayurvedic_remedies = [r for r in kb_cache.ayurvedic_remedies if r.get("pregnancy_safe") == True]
    else:
        ayurvedic_remedies = kb_cache.ayurvedic_remedies
    raw_plan = engine_generate(user_profile, medicines_prefs, ayurvedic_remedies, 'clinical_medicine')
    enriched_plan = await enrich_medicines_plan(raw_plan, user_profile, medicines_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "services.remedy_engine")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="medicines",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={
            "medicines": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan


@router.post("/generate")
async def generate_holistic_plan(req: PlanGenerationRequest, background_tasks: BackgroundTasks, user: UserDocument = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    return await _enqueue_plan("holistic", req, user, db, background_tasks)

@router.get("/job/{job_id}")
async def get_plan_job_status(
    job_id: str,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Poll the status of an async plan generation job.

    Returns:
        - status: "pending" | "running" | "done" | "failed"
        - result: full plan data when status == "done" (None otherwise)
        - error:  error message when status == "failed" (None otherwise)
        - plan_id: saved plan history id when status == "done" (None otherwise)
    """
    job = await db.plan_jobs.find_one({"_id": job_id, "user_id": user.id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "plan_type": job.get("plan_type"),
        "status": job.get("status"),
        "plan_id": job.get("plan_id"),
        "result": job.get("result"),
        "error": job.get("error"),
        "created_at": job["created_at"].isoformat() if isinstance(job.get("created_at"), datetime) else job.get("created_at"),
        "completed_at": job["completed_at"].isoformat() if isinstance(job.get("completed_at"), datetime) else job.get("completed_at"),
    }


@router.get("/latest", response_model=PlanResponse)
async def get_latest_plan(user: UserDocument = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    cursor = db.plan_history.find({"user_id": user.id}).sort("generated_at", -1).limit(1)
    plans = await cursor.to_list(length=1)
    if not plans:
        raise HTTPException(status_code=404, detail="No plans generated yet")
    plan = plans[0]
    plan_data = {**plan["plan_data"], "id": plan["_id"]}
    return PlanResponse(**plan_data)


@router.get("/history")
async def get_plan_history(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    offset: int = 0,
    limit: int = 20,
):
    limit = min(limit, 100)  # cap at 100
    cursor = db.plan_history.find({"user_id": user.id}).sort("generated_at", -1).skip(offset).limit(limit)
    plans = await cursor.to_list(length=limit)
    return [
        {
            "id": p["_id"],
            "plan_type": p.get("plan_type", "holistic"),
            "generation_method": p.get("generation_method", "rule_based"),
            "model_used": p.get("model_used"),
            "generated_at": p["generated_at"].isoformat() if isinstance(p["generated_at"], datetime) else p["generated_at"],
            "source_plan_id": p.get("plan_data", {}).get("source_plan_id"),
            "adaptation_summary": p.get("plan_data", {}).get("adaptation_summary"),
            "version_diff": p.get("plan_data", {}).get("version_diff"),
            "ratings": p.get("plan_data", {}).get("ratings", {}),
            "plan_data": {**p.get("plan_data", {}), "id": p["_id"]},
        }
        for p in plans
    ]


@router.post("/{plan_id}/rating")
async def rate_plan(
    plan_id: str,
    req: PlanRatingRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Store a user rating for an entire plan or a specific section."""
    plan = await db.plan_history.find_one({"_id": plan_id, "user_id": user.id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    ratings = dict(plan.get("plan_data", {}).get("ratings", {}))
    ratings[req.section] = {
        "score": req.score,
        "note": req.note,
        "rated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.plan_history.update_one(
        {"_id": plan_id},
        {"$set": {"plan_data.ratings": ratings}}
    )
    return {"message": "Rating saved", "ratings": ratings}


@router.get("/seasonal")
async def get_seasonal_guidance(user: UserDocument = Depends(get_current_user)):
    """Feature 8: Ritucharya - Get seasonal Ayurvedic guidance."""
    from services.seasonal_service import build_seasonal_guidance

    dosha = user.dominant_dosha or "pitta"
    try:
        return await build_seasonal_guidance(dosha)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate seasonal guidance: {str(e)}")


@router.get("/meditation")
async def get_guided_meditation(
    mood: str = "anxious", 
    duration_minutes: int = 5,
    user: UserDocument = Depends(get_current_user)
):
    """Feature 14: Guided Meditation Script Generation."""
    from ai.rag_pipeline import rag_pipeline
    from ai.llm_client import llm_client
    import json
    
    dosha = user.dominant_dosha or "vata"
    
    # TIER 2: Query RAG
    query = f"meditation script {mood} mood balancing {dosha} dosha"
    docs = await rag_pipeline.query(query, "ayurveda", n_results=2, dosha_filter=dosha)
    context = rag_pipeline.format_context(docs, max_chars=1000)
    
    # TIER 3: GenAI Response
    prompt = f"""
    You are an Ayurvedic Meditation Guide. Generate a {duration_minutes}-minute meditation script.
    
    USER DOSHA: {dosha}
    CURRENT MOOD/STATE: {mood}
    
    AYURVEDIC KNOWLEDGE:
    {context if context else 'Use standard dosha balancing meditation techniques.'}
    
    Return ONLY valid JSON in this exact format:
    {{
        "title": "Meditation Title",
        "focus": "Brief focus statement",
        "duration_minutes": {duration_minutes},
        "script": [
            {{"time": "0:00 - 1:00", "narration": "...", "breathing_cue": "..."}},
            {{"time": "1:00 - 2:00", "narration": "...", "breathing_cue": "..."}}
        ]
    }}
    """
    
    try:
        response = await llm_client.generate(prompt=prompt, system_prompt="You are a calming Ayurvedic Meditation Guide.", temperature=0.7, json_mode=True)
        return json.loads(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate meditation script: {str(e)}")


@router.post("/interaction-check")
async def check_interactions(
    herbs: list[str] = Body(...),
    user: UserDocument = Depends(get_current_user)
):
    """Feature 12: Drug-Herb Interaction Checker."""
    from engine.condition_filter import condition_filter
    from ai.rag_pipeline import rag_pipeline
    from ai.llm_client import llm_client
    
    medications = user.current_medications or []
    if not medications:
        return {"status": "safe", "warnings": [], "detailed_explanation": "No current medications reported."}
        
    # TIER 1: Deterministic check
    interaction_result = condition_filter.check_drug_herb_interactions(medications, herbs)
    warnings = interaction_result["warnings"]
    
    if not warnings:
        return {
            "status": "safe",
            "warnings": [],
            "general_warnings": interaction_result.get("general_warnings", []),
            "detailed_explanation": "No known dangerous interactions detected between your medications and these herbs.",
        }
        
    # TIER 2: RAG Retrieval
    rag_contexts = []
    for w in warnings:
        query = f"{w['herb']} interaction with {w['medication_category']} medication"
        docs = await rag_pipeline.query(query, "remedy", n_results=1)
        if docs:
            rag_contexts.append(docs[0]["content"])
            
    context = "\n".join(rag_contexts)
    
    # TIER 3: GenAI Response
    prompt = f"""
    You are an Ayurvedic Safety Assistant. Explain the following drug-herb interactions.
    
    USER MEDICATIONS: {medications}
    PROPOSED HERBS: {herbs}
    DETECTED RISKS: {warnings}
    
    MEDICAL CONTEXT: {context}
    
    Write a clear, professional warning about these interactions. 
    State explicitly that they must consult their doctor before proceeding.
    """
    
    try:
        warning_text = await llm_client.generate(prompt=prompt, system_prompt="You are a medical safety assistant.", temperature=0.3)
    except Exception:
        warning_text = "There are potential interactions between your medications and these herbs. Please consult your doctor immediately."
    
    return {
        "status": "warning",
        "warnings": warnings,
        "general_warnings": interaction_result.get("general_warnings", []),
        "detailed_explanation": warning_text
    }
