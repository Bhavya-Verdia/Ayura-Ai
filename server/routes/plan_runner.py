"""
Ayura AI - Plan generation orchestration helpers.

Extracted from routes/plans.py: the deterministic engine-backed feature
generation, per-user locking, ARQ pool/LLM concurrency guards, the background
job runner, and the shared enqueue handler. The route handlers in routes/plans.py
import from here. worker.py and chat_service.py also depend on this module
(_run_plan_job, _generate_feature_via_engine, PLAN_DATA_KEYS).
"""

from datetime import datetime, timezone
import uuid
import asyncio
import hashlib
import json
import re
from contextlib import asynccontextmanager

from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from arq import create_pool
from arq.connections import RedisSettings

from config import settings
from database.mongodb import get_mongodb
from schemas.user_schema import UserDocument, PlanHistoryDocument
from schemas.plan_schema import PlanGenerationRequest
from schemas.preferences_schema import (
    GymPreferences, YogaPreferences, DietPreferences,
    PanchakarmaPreferences, RemedyPreferences,
)
from services.plan_diff import build_plan_diff
from services.audit_service import log_plan_generated
from services.notification_service import create_and_deliver_notification
from core.cache import cache_manager
from core.kb_cache import kb_cache

def _sanitize_prompt_input(text: str, max_len: int = 200) -> str:
    """Strip common prompt-injection patterns and cap length."""
    text = re.sub(r'(?i)(system\s*:|assistant\s*:|<<\s*SYS\s*>>|<\|.*?\|>)', '', text)
    text = re.sub(r'(?i)(ignore\s+(all\s+)?previous\s+instructions?|forget\s+(everything|all)|jailbreak|bypass)', '', text)
    return text.strip()[:max_len]

async def _check_plan_cache(db: AsyncIOMotorDatabase, user_id: str, plan_type: str, user_profile: dict, feature_prefs: dict, force_regenerate: bool):
    if force_regenerate:
        return None, None

    relevant_data = {
        "dosha": user_profile.get("dominant_dosha"),
        "vikriti": user_profile.get("vikriti_dominant"),
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


# ─── ARQ Connection Pool (double-checked locking to prevent race on startup) ──

_arq_pool = None
_arq_pool_lock: asyncio.Lock | None = None


def _get_arq_lock() -> asyncio.Lock:
    global _arq_pool_lock
    if _arq_pool_lock is None:
        _arq_pool_lock = asyncio.Lock()
    return _arq_pool_lock


async def get_arq_pool():
    """Get or create the ARQ Redis connection pool for background jobs."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool
    async with _get_arq_lock():
        if _arq_pool is None:
            _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379"))
    return _arq_pool


# ─── LLM Concurrency Guard ────────────────────────────────────────────────────
#
# Individual plan routes call LLM enrichers directly (not via ARQ).
# Without a cap, 50+ simultaneous requests would spawn 50+ concurrent HTTP
# calls to Azure OpenAI — exhausting the per-minute rate limit and causing
# cascading 429 failures for every user.
#
# 12 concurrent calls per worker × 4 workers = 48 total ≈ safe headroom
# under Azure OpenAI standard tier (50 RPM).

_LLM_SEMAPHORE: asyncio.Semaphore | None = None


def _get_llm_semaphore() -> asyncio.Semaphore:
    global _LLM_SEMAPHORE
    if _LLM_SEMAPHORE is None:
        _LLM_SEMAPHORE = asyncio.Semaphore(12)
    return _LLM_SEMAPHORE




@asynccontextmanager
async def _plan_guard(user_id: str, plan_type: str):
    """Per-user lock + global LLM semaphore for individual (non-ARQ) plan routes.

    Prevents:
    - A user double-clicking "Generate" from firing two simultaneous LLM calls
    - The LLM semaphore ensures at most 12 concurrent enrichments per worker
    """
    acquired = await _acquire_plan_lock(user_id, plan_type)
    if not acquired:
        raise HTTPException(
            status_code=409,
            detail=f"A {plan_type} plan is already being generated for your account. Please wait.",
        )
    try:
        async with _get_llm_semaphore():
            yield
    finally:
        await _release_plan_lock(user_id, plan_type)

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


# ─── Engine-backed feature generation (shared by holistic + agentic paths) ────

async def _generate_feature_via_engine(
    db: AsyncIOMotorDatabase,
    user_id: str,
    plan_type: str,
    user_profile: dict,
) -> dict | list:
    """Generate ONE feature plan through the deterministic engine + LLM enricher —
    the same KB-grounded path the per-feature endpoints use.

    The holistic and agentic single-plan paths call this so they no longer rely on
    un-grounded free-text LLM agents (which ignored the KB and could hallucinate
    formulations / asanas). Returns the enriched plan (dict, or list for
    remedies/medicines). On failure returns a safe empty value so a single feature
    failing never aborts a holistic plan.
    """
    from engine.seasonal import get_current_season
    season_info = get_current_season()
    profile = {**user_profile, "current_season": season_info.name.lower()}
    is_prenatal = bool(profile.get("pregnancy_or_nursing"))
    prefs = await _load_feature_preferences(db, user_id, plan_type)

    def _kb(attr):
        try:
            if getattr(kb_cache, "loaded", False):
                return getattr(kb_cache, attr, None) or None
        except Exception:
            pass
        return None  # engines fall back to their bundled JSON when KB is None

    try:
        if plan_type == "yoga":
            from services.yoga_plan_engine import generate_yoga_plan, yoga_poses as _ep
            from services.yoga_plan_enricher import enrich_yoga_plan
            base_poses = _kb("yoga_poses") or _ep
            poses = [p for p in base_poses if (not is_prenatal or p.get("pregnancy_safe"))]
            raw = generate_yoga_plan(profile, prefs, poses or None, _kb("pranayama"))
            return await enrich_yoga_plan(raw, profile, prefs)

        if plan_type == "gym":
            from services.gym_plan_engine import generate_gym_plan
            from services.gym_plan_enricher import enrich_gym_plan
            ex = _kb("gym_exercises")
            if is_prenatal and ex:
                ex = [e for e in ex if e.get("pregnancy_safe")] or None
            raw = generate_gym_plan(profile, prefs, ex)
            return await enrich_gym_plan(raw, profile, prefs)

        if plan_type == "diet":
            from services.diet_llm_generator import generate_diet_plan_llm
            enriched = await generate_diet_plan_llm(profile, prefs)
            if enriched is None:
                from services.diet_plan_engine import generate_diet_plan
                from services.diet_plan_enricher import enrich_diet_plan
                from services.ahara_safety import apply_ahara_safety
                raw = generate_diet_plan(profile, prefs, _kb("diet_foods"))
                enriched = await enrich_diet_plan(raw, profile, prefs)
                enriched = apply_ahara_safety(
                    enriched, prefs.get("food_allergies") or [], prefs.get("food_intolerances") or [])
            return enriched

        if plan_type == "panchakarma":
            if is_prenatal:
                return {"error": "Panchakarma is not available during pregnancy or nursing.", "blocked": True}
            from services.panchakarma_engine import generate_panchakarma_plan
            from services.panchakarma_enricher import enrich_panchakarma_plan
            raw = generate_panchakarma_plan(profile, prefs, _kb("panchakarma_protocols"))
            return await enrich_panchakarma_plan(raw, profile, prefs)

        if plan_type == "remedies":
            if is_prenatal:
                return []
            symptoms = profile.get("current_symptoms") or []
            if not symptoms:
                return []
            from services.remedy_engine import filter_remedies, build_remedy_plan
            from services.remedy_enricher import enrich_remedies_plan
            symptom_input = {"symptoms": symptoms}
            filtered = filter_remedies(profile, symptom_input)
            raw = build_remedy_plan(filtered, profile, symptom_input)
            return await enrich_remedies_plan(raw, profile)

        if plan_type == "medicines":
            if is_prenatal:
                return []
            from services.remedy_engine import generate_medicines_plan as _gen_meds
            from services.remedy_enricher import enrich_medicines_plan
            raw = _gen_meds(profile, prefs, [], "clinical_medicine")
            return await enrich_medicines_plan(raw, profile, prefs)

    except Exception as exc:
        from core.logger import logger
        logger.error("Engine generation failed for %s: %s", plan_type, exc)
        return [] if plan_type in ("remedies", "medicines") else {"error": str(exc)[:200]}

    return {"error": f"Unknown plan type: {plan_type}"}


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

        if req_mode == "agentic":
            if plan_type == "holistic":
                # Generate every feature through the KB-grounded deterministic engines
                # (same path as the per-feature endpoints) — NOT the un-grounded LLM
                # agents. All six run concurrently.
                feature_types = ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]
                results = await asyncio.wait_for(
                    asyncio.gather(*[
                        _generate_feature_via_engine(db, user_id, ft, user_profile)
                        for ft in feature_types
                    ]),
                    timeout=PLAN_TIMEOUT,
                )
                by_type = dict(zip(feature_types, results))

                # Seasonal guidance + daily tip are lightweight LLM/service extras
                seasonal_guidance = None
                try:
                    from services.seasonal_service import build_seasonal_guidance
                    dosha = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha") or "vata"
                    seasonal_guidance = await build_seasonal_guidance(dosha)
                except Exception:
                    pass

                previous = await _get_plan_record_for_adaptation(db, user_id, req_previous_plan_id) if req_feedback else None
                full_plan_data = {
                    "user_summary": {"name": user_profile.get("name"), "dominant_dosha": user_profile.get("dominant_dosha")},
                    "gym_plan": by_type.get("gym"),
                    "yoga_plan": by_type.get("yoga"),
                    "diet_plan": by_type.get("diet"),
                    "panchakarma_plan": by_type.get("panchakarma"),
                    "home_remedies": by_type.get("remedies"),
                    "medicines": by_type.get("medicines"),
                    "seasonal_guidance": seasonal_guidance,
                    "daily_tip": None,
                    "health_risks": [],
                    "safety_checks": {"generation_mode": "engine_backed"},
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generation_method": req_mode,
                    "model_used": "engine+enricher",
                }
                if req_feedback and previous:
                    full_plan_data["source_plan_id"] = previous["_id"]
                    full_plan_data["version_diff"] = build_plan_diff(previous.get("plan_data"), full_plan_data)
            else:
                # Single feature via the deterministic engine + enricher path.
                enriched = await asyncio.wait_for(
                    _generate_feature_via_engine(db, user_id, plan_type, user_profile),
                    timeout=PLAN_TIMEOUT,
                )
                plan_data_key = PLAN_DATA_KEYS[plan_type]
                full_plan_data = {
                    "user_summary": {"name": user_profile.get("name"), "dominant_dosha": user_profile.get("dominant_dosha")},
                    plan_data_key: enriched,
                    "health_risks": [],
                    "safety_checks": {"generation_mode": "engine_backed"},
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generation_method": req_mode,
                    "model_used": (enriched.get("enrichment_model") if isinstance(enriched, dict) else None) or "engine+enricher",
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

        # Notify user that their plan is ready
        plan_label = plan_type.replace("_", " ").title()
        notif_title = f"Your {plan_label} Plan is Ready" if not req_feedback else f"{plan_label} Plan Adapted"
        notif_body = (
            f"Your personalised {plan_label} plan has been generated. Open the Dashboard to view it."
            if not req_feedback
            else f"Your {plan_label} plan has been updated based on your feedback. Check the Dashboard."
        )
        try:
            await create_and_deliver_notification(
                db, user_id, notif_title, notif_body,
                notif_type="plan_ready" if not req_feedback else "adaptation",
            )
        except Exception:
            pass  # never block plan generation over a notification failure

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

    # ── Email Verification Gate ───────────────────────────────────────────────
    if user.auth_provider == "local" and not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address before generating plans. Check your inbox for a verification link.",
        )

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
        # Vikriti (current imbalance) — primary target for plan correction
        "vikriti_scores": user.vikriti_scores,
        "vikriti_dominant": user.vikriti_dominant,
        "vikriti_secondary": user.vikriti_secondary,
        "dosha_constitution_type": user.dosha_constitution_type,
        "dosha_immediate_focus": user.dosha_immediate_focus,
        "dosha_key_signals": user.dosha_key_signals or [],
        "checkin_count": user.checkin_count or 0,
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
        # Classical Ayurvedic fields
        "satmya": user.satmya,
        "disease_stages": user.disease_stages,
        "koshtha": user.koshtha,
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
    # Try ARQ (Redis-backed worker) first; fall back to in-process if Redis is unavailable.
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job(
            "_run_plan_job", job_id, plan_type, user.id, req.mode,
            req.feedback, req.previous_plan_id, user_profile
        )
    except Exception:
        from core.logger import logger
        logger.warning("ARQ enqueue failed — running plan job in-process as fallback")
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
    """Fetch the most recent plan of each type for cross-agent context.

    Uses a single aggregation (one round-trip) instead of N sequential queries.
    """
    other_types = [t for t in ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"] if t != current_type]
    pipeline = [
        {"$match": {"user_id": user_id, "plan_type": {"$in": other_types}}},
        {"$sort": {"generated_at": -1}},
        {"$group": {"_id": "$plan_type", "plan_data": {"$first": "$plan_data"}}},
    ]
    context: dict = {}
    async for doc in db.plan_history.aggregate(pipeline):
        context[f"{doc['_id']}_plan"] = doc.get("plan_data", {})
    return context
