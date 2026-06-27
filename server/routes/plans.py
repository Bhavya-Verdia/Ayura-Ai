"""
Ayura AI - Plan Generation Routes (Full 4-tier AI pipeline wired)

Orchestration helpers (engine generation, locking, ARQ job runner, enqueue)
live in routes/plan_runner.py; this module holds the FastAPI route handlers.
"""

from datetime import datetime, timezone
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import BackgroundTasks

from database.mongodb import get_mongodb
from core.logger import logger
from schemas.user_schema import UserDocument, PlanHistoryDocument
from schemas.plan_schema import PlanGenerationRequest, PlanRatingRequest, PlanResponse
from routes.profile import get_current_user
from services.audit_service import log_plan_generated
from core.kb_cache import kb_cache

from routes.plan_runner import (
    _sanitize_prompt_input,
    _check_plan_cache,
    _generate_feature_via_engine,
    _enqueue_plan,
    _plan_guard,
    PREGNANCY_BLOCKED_FEATURES,
    assert_not_pregnancy_blocked,
)

import json
import re

router = APIRouter()

# --- Route Handlers (return job_id instantly) ---

@router.post("/yoga")
async def generate_yoga_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.yoga_plan_engine import generate_yoga_plan as engine_generate
    from services.yoga_plan_enricher import enrich_yoga_plan

    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})

    if not prefs_doc or not prefs_doc.get("yoga"):
        raise HTTPException(status_code=422, detail="Complete yoga preferences first")

    yoga_prefs = prefs_doc.get("yoga")
    is_prenatal = user.pregnancy_or_nursing

    # Inject current Ayurvedic season so engine can apply Ritucharya pose boosts
    from engine.seasonal import get_current_season
    season_info = get_current_season()
    user_profile["current_season"] = season_info.name.lower()

    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "yoga", user_profile, yoga_prefs, force_regenerate)
    if cached_plan:
        return cached_plan

    # 2. Generate new plan (per-user lock + global LLM semaphore)
    async with _plan_guard(user.id, "yoga"):
        if is_prenatal:
            yoga_poses = [p for p in kb_cache.yoga_poses if p.get("pregnancy_safe") is True]
        else:
            yoga_poses = kb_cache.yoga_poses
        pranayama_list = kb_cache.pranayama or None  # None triggers file-based fallback in engine

        # Dynamic protocol fallback: generate LLM mini-protocols for conditions not in the 30-protocol DB
        from services.yoga_plan_engine import _PROTOCOL_MAP as _engine_proto_map
        from services.yoga_plan_engine import yoga_poses as _engine_poses, pranayama_list as _engine_prana
        user_conditions = user_profile.get("medical_history") or []
        unknown_conds = [
            c for c in user_conditions
            if c.lower() not in _engine_proto_map
            and c.lower().replace(" ", "_") not in _engine_proto_map
        ]
        extra_protocols: dict = {}
        if unknown_conds:
            try:
                from services.yoga_condition_fallback import generate_dynamic_protocols
                pose_ids = [p["id"] for p in (yoga_poses or _engine_poses)]
                prana_ids = [p["id"] for p in (pranayama_list or _engine_prana)]
                extra_protocols = await generate_dynamic_protocols(unknown_conds, pose_ids, prana_ids)
            except Exception as _dyn_err:
                from core.logger import logger
                logger.warning(f"Dynamic protocol generation skipped: {_dyn_err}")

        raw_plan = engine_generate(user_profile, yoga_prefs, yoga_poses or None, pranayama_list,
                                   extra_protocols=extra_protocols)
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
    from services.diet_plan_enricher import enrich_diet_plan

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

    # 2. Generate new plan (per-user lock + global LLM semaphore)
    async with _plan_guard(user.id, "diet"):
        from services.diet_llm_generator import generate_diet_plan_llm

        # Inject season (same as yoga route) so Ritucharya block is populated
        from engine.seasonal import get_current_season
        season_info = get_current_season()
        user_profile["current_season"] = season_info.name.lower()

        # Inject pregnancy flag so LLM brief adds hard constraints
        user_profile["pregnancy_or_nursing"] = user.pregnancy_or_nursing or False

        # Primary path: LLM-generated clinical plan
        enriched_plan = await generate_diet_plan_llm(user_profile, diet_prefs)

        # Fallback: rule engine + enricher if LLM fails
        if enriched_plan is None:
            from core.logger import logger
            logger.warning(f"LLM diet generation failed for {user.id}; falling back to rule engine")
            diet_foods = kb_cache.diet_foods or None
            raw_plan = engine_generate(user_profile, diet_prefs, diet_foods)
            enriched_plan = await enrich_diet_plan(raw_plan, user_profile, diet_prefs)
            # Same deterministic Ahara safety scan the LLM path gets
            from services.ahara_safety import apply_ahara_safety
            enriched_plan = apply_ahara_safety(
                enriched_plan, diet_prefs.get("food_allergies") or [],
                diet_prefs.get("food_intolerances") or [])

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

    # Routine-specific prefs (Tier C) — fall back to diet prefs for backward compat
    routine_prefs = (prefs_doc or {}).get("routine") or (prefs_doc or {}).get("diet")
    if not routine_prefs:
        raise HTTPException(status_code=422, detail="Complete daily routine preferences first")

    prefs_to_pass = {"routine": routine_prefs, "diet": (prefs_doc or {}).get("diet") or {}}

    # Tier B: fetch gym/yoga plan histories if integration is requested
    integrate_gym  = routine_prefs.get("integrate_gym_plan", False)
    integrate_yoga = routine_prefs.get("integrate_yoga_plan", False)
    gym_plan_data  = None
    yoga_plan_data = None

    if integrate_gym:
        gym_hist = await db.plan_history.find_one(
            {"user_id": user.id, "plan_type": "gym"},
            sort=[("generated_at", -1)]
        )
        if gym_hist:
            gym_plan_data = gym_hist.get("plan_data", {}).get("gym_plan") or gym_hist.get("plan_data", {})

    if integrate_yoga:
        yoga_hist = await db.plan_history.find_one(
            {"user_id": user.id, "plan_type": "yoga"},
            sort=[("generated_at", -1)]
        )
        if yoga_hist:
            yoga_plan_data = yoga_hist.get("plan_data", {}).get("yoga_plan") or yoga_hist.get("plan_data", {})

    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "routine", user_profile, prefs_to_pass, force_regenerate)
    if cached_plan:
        return cached_plan

    # 2. Generate new plan (engine first, then LLM enrichment for coaching rationale)
    async with _plan_guard(user.id, "routine"):
        from engine.seasonal import get_current_season
        season_info = get_current_season()
        user_profile["current_season"] = season_info.name.lower()

        raw_plan = engine_generate(
            user_profile,
            prefs_to_pass,
            gym_plan_data=gym_plan_data,
            yoga_plan_data=yoga_plan_data,
        )

        from services.routine_enricher import enrich_routine_plan
        enriched_plan = await enrich_routine_plan(raw_plan, user_profile, prefs_to_pass)

        plan_id = enriched_plan.get("plan_id")
        model_used = enriched_plan.get("enrichment_model", "services.routine_engine")

        history = PlanHistoryDocument(
            _id=plan_id,
            user_id=user.id,
            plan_type="routine",
            generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
            model_used=model_used,
            preference_hash=pref_hash,
            plan_data={
                "routine_plan": enriched_plan,
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            generated_at=datetime.now(timezone.utc)
        )
        await db.plan_history.insert_one(history.model_dump(by_alias=True))

    return enriched_plan

@router.post("/gym")
async def generate_gym_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.gym_plan_engine import generate_gym_plan as engine_generate
    from services.gym_plan_enricher import enrich_gym_plan

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

    # 2. Generate new plan (per-user lock + global LLM semaphore)
    async with _plan_guard(user.id, "gym"):
        if is_prenatal:
            gym_exercises = [e for e in kb_cache.gym_exercises if e.get("pregnancy_safe") is True] or None
        else:
            gym_exercises = kb_cache.gym_exercises or None
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
    from services.panchakarma_enricher import enrich_panchakarma_plan

    # Pregnancy gate — contraindicated; matches the holistic/worker paths (403, not a filtered plan)
    assert_not_pregnancy_blocked(user, "panchakarma")

    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})

    if not prefs_doc or not prefs_doc.get("panchakarma"):
        raise HTTPException(status_code=422, detail="Complete panchakarma preferences first")

    panchakarma_prefs = prefs_doc.get("panchakarma")

    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "panchakarma", user_profile, panchakarma_prefs, force_regenerate)
    if cached_plan:
        return cached_plan

    # 2. Generate new plan (per-user lock + global LLM semaphore)
    async with _plan_guard(user.id, "panchakarma"):
        panchakarma_therapies = kb_cache.panchakarma_protocols
        # None triggers the engine's bundled-JSON fallback (kb_* Mongo collections
        # have no seeder, so kb_cache is empty unless populated externally).
        raw_plan = engine_generate(user_profile, panchakarma_prefs, panchakarma_therapies or None)
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

    # Pregnancy gate — contraindicated; matches the holistic/worker paths
    assert_not_pregnancy_blocked(user, "remedies")

    user_profile = user.model_dump()

    if "symptoms" not in req:
        raise HTTPException(status_code=422, detail="Request body must contain 'symptoms' list")

    # Remedies don't have a preference_hash cache, but still need lock + semaphore
    async with _plan_guard(user.id, "remedies"):
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

        await log_plan_generated(
            db=db,
            user_id=user.id,
            plan_id=plan_id,
            plan_type="remedies",
            model_used=model_used,
            is_adaptation=False,
        )

    return enriched_plan


@router.post("/medicines")
async def generate_medicines_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from services.remedy_engine import generate_medicines_plan as engine_generate
    from services.remedy_enricher import enrich_medicines_plan

    # Pregnancy gate — contraindicated; matches the holistic/worker paths
    assert_not_pregnancy_blocked(user, "medicines")

    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({"user_id": user.id})

    if not prefs_doc or not prefs_doc.get("remedies"):
        raise HTTPException(status_code=422, detail="Complete medicines preferences first")

    medicines_prefs = prefs_doc.get("remedies")

    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "medicines", user_profile, medicines_prefs, force_regenerate)
    if cached_plan:
        return cached_plan

    # 2. Generate new plan (per-user lock + global LLM semaphore)
    async with _plan_guard(user.id, "medicines"):
        raw_plan = engine_generate(user_profile, medicines_prefs, [], 'clinical_medicine')
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


@router.post("/stream")
async def stream_holistic_plan(
    req: dict = Body(default={}),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Stream holistic plan generation via Server-Sent Events.

    Each feature (gym, yoga, diet, panchakarma, remedies, medicines) streams its
    result as soon as it completes — the client doesn't wait for all 6 to finish.

    SSE event format per feature:
        event: feature
        data: {"feature": "gym", "status": "done", "data": {...}}

    Final event:
        event: complete
        data: {"plan_id": "...", "generated_at": "..."}

    Error event (per feature failure, non-fatal):
        event: feature
        data: {"feature": "yoga", "status": "error", "error": "..."}
    """
    from fastapi.responses import StreamingResponse
    from engine.seasonal import get_current_season
    import asyncio
    import uuid

    if not user.onboarding_complete:
        raise HTTPException(status_code=400, detail="Please complete onboarding first")
    if user.auth_provider == "local" and not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before generating plans.")

    season_info = get_current_season()
    # Build the profile from the full user document so every safety/personalisation
    # field (ama_indicator, ojas_level, koshtha, disease_stages, satmya, ...) reaches
    # the engines — the same dict shape the per-feature routes and worker path use.
    user_profile = user.model_dump()
    user_profile["_user_id"] = user.id
    user_profile["current_season"] = season_info.name.lower()

    # Pregnancy-blocked features (shared source of truth)
    feature_types = [
        ft for ft in ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]
        if not (user.pregnancy_or_nursing and ft in PREGNANCY_BLOCKED_FEATURES)
    ]

    async def event_generator():
        results: dict = {}
        queue: asyncio.Queue = asyncio.Queue()

        async def run_feature(ft: str):
            try:
                result = await _generate_feature_via_engine(db, user.id, ft, user_profile)
                await queue.put(("done", ft, result))
            except Exception as exc:
                await queue.put(("error", ft, str(exc)[:300]))

        # Launch all features concurrently. Keep a reference to the task list:
        # asyncio only holds weak references, so an unreferenced task can be
        # garbage-collected mid-flight. (Unused-by-name is intentional.)
        tasks = [asyncio.create_task(run_feature(ft)) for ft in feature_types]  # noqa: F841

        completed = 0
        while completed < len(feature_types):
            status, ft, payload = await queue.get()
            completed += 1
            if status == "done":
                results[ft] = payload
                event_data = json.dumps({"feature": ft, "status": "done", "data": payload}, default=str)
            else:
                event_data = json.dumps({"feature": ft, "status": "error", "error": payload})
            yield f"event: feature\ndata: {event_data}\n\n"

        # Save holistic plan to history
        plan_id = str(uuid.uuid4())
        generated_at = datetime.now(timezone.utc).isoformat()
        try:
            full_plan_data = {
                "user_summary": {"name": user.name, "dominant_dosha": user.dominant_dosha},
                "gym_plan": results.get("gym"),
                "yoga_plan": results.get("yoga"),
                "diet_plan": results.get("diet"),
                "panchakarma_plan": results.get("panchakarma"),
                "home_remedies": results.get("remedies"),
                "medicines": results.get("medicines"),
                "health_risks": [],
                "safety_checks": {"generation_mode": "engine_backed", "stream": True},
                "generated_at": generated_at,
                "generation_method": "agentic",
                "model_used": "engine+enricher",
                "id": plan_id,
            }
            history = PlanHistoryDocument(
                _id=plan_id, user_id=user.id, plan_type="holistic",
                generation_method="agentic", model_used="engine+enricher",
                plan_data=full_plan_data, generated_at=datetime.now(timezone.utc)
            )
            await db.plan_history.insert_one(history.model_dump(by_alias=True))
        except Exception as exc:
            from core.logger import logger
            logger.error("Stream: failed to save holistic plan: %s", exc)

        complete_data = json.dumps({"plan_id": plan_id, "generated_at": generated_at})
        yield f"event: complete\ndata: {complete_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

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
    before_id: str | None = None,
    limit: int = 20,
):
    """Return plan history newest-first. Pass `before_id` (a plan _id) for cursor pagination
    instead of skip-based offset, which is O(N) on large collections."""
    limit = min(limit, 100)
    query: dict = {"user_id": user.id}
    if before_id:
        # Fetch the cursor document's timestamp so we can range-scan the index
        anchor = await db.plan_history.find_one({"_id": before_id, "user_id": user.id}, {"generated_at": 1})
        if anchor:
            query["generated_at"] = {"$lt": anchor["generated_at"]}
    cursor = db.plan_history.find(query).sort("generated_at", -1).limit(limit)
    plans = await cursor.to_list(length=limit)
    items = [
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
    return {
        "items": items,
        "next_cursor": items[-1]["id"] if len(items) == limit else None,
    }


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
        logger.error("Failed to generate seasonal guidance: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate seasonal guidance. Please try again.")


@router.get("/meditation")
async def get_guided_meditation(
    mood: str = "anxious",
    duration_minutes: int = 5,
    user: UserDocument = Depends(get_current_user)
):
    """Feature 14: Guided Meditation Script Generation."""
    from ai.rag_pipeline import rag_pipeline
    from ai.llm_client import llm_client

    dosha = user.dominant_dosha or "vata"
    mood = _sanitize_prompt_input(mood, max_len=50)

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
        # Strip markdown code fences the LLM sometimes wraps the JSON in
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Meditation script could not be parsed. Please try again.")
    except Exception as e:
        logger.error("Failed to generate meditation script: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate meditation script. Please try again.")


@router.post("/interaction-check")
async def check_interactions(
    herbs: list[str] = Body(..., embed=True),
    medications: list[str] | None = Body(default=None, embed=True),
    user: UserDocument = Depends(get_current_user)
):
    """Drug-Herb Interaction Checker.

    `herbs` is the proposed Ayurvedic herb/formulation list. `medications` is
    optional — when omitted the user's stored `current_medications` are used, so
    the standalone "Ask before you take" tool can either rely on the saved profile
    or check against an ad-hoc medication list.
    """
    from engine.condition_filter import condition_filter
    from ai.rag_pipeline import rag_pipeline
    from ai.llm_client import llm_client

    herbs = [_sanitize_prompt_input(h, max_len=100) for h in (herbs or []) if h and h.strip()]
    if medications is None:
        medications = user.current_medications or []
    medications = [_sanitize_prompt_input(m, max_len=100) for m in (medications or []) if m and m.strip()]

    if not herbs:
        return {"status": "safe", "warnings": [], "general_warnings": [],
                "detailed_explanation": "Enter at least one herb or formulation to check."}
    if not medications:
        return {"status": "safe", "warnings": [], "general_warnings": [],
                "detailed_explanation": "No medications to cross-check. Add your current medications (or your saved profile) — and always confirm with your physician before combining."}

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

    # TIER 2: RAG Retrieval (parallel queries — one per warning)
    rag_results = await asyncio.gather(*[
        rag_pipeline.query(
            f"{w['herb']} interaction with {w['medication_category']} medication",
            "remedy", n_results=1
        )
        for w in warnings
    ])
    context = "\n".join(docs[0]["content"] for docs in rag_results if docs)

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


_REACTION_PLAN_TYPES = {"gym", "yoga", "diet", "routine", "panchakarma", "remedies", "medicines", "general"}
_REACTION_SEVERITIES = {"mild", "moderate", "severe"}


@router.post("/{plan_type}/report-reaction", status_code=201)
async def report_reaction(
    plan_type: str,
    item: str = Body(..., embed=True),
    reaction: str = Body(..., embed=True),
    severity: str = Body("moderate", embed=True),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Adverse-reaction loop: a user reports a reaction/flare to a plan item.

    Records it, writes a Health Timeline event + audit entry, and nudges
    re-assessment so the dashboard can prompt the user to refine their profile.
    """
    if plan_type not in _REACTION_PLAN_TYPES:
        raise HTTPException(status_code=400, detail="Unknown plan type")
    item = _sanitize_prompt_input(item, max_len=200)
    reaction = _sanitize_prompt_input(reaction, max_len=500)
    severity = severity.lower() if severity.lower() in _REACTION_SEVERITIES else "moderate"
    if not item or not reaction:
        raise HTTPException(status_code=422, detail="Both item and reaction are required")

    now = datetime.now(timezone.utc)
    details = {"plan_type": plan_type, "item": item, "reaction": reaction, "severity": severity}

    await db.plan_reactions.insert_one({"_id": str(uuid.uuid4()), "user_id": user.id, **details, "created_at": now})
    try:
        await db.timeline.insert_one({
            "user_id": user.id, "event_type": "reaction_reported",
            "details": details, "source": "user", "timestamp": now,
        })
    except Exception:
        pass
    try:
        from services.audit_service import log_health_event
        await log_health_event(db, user.id, "reaction_reported", details, source="user")
    except Exception:
        pass
    # A severe reaction is a strong signal the plan/profile needs revisiting.
    if severity == "severe":
        await db.users.update_one({"_id": user.id}, {"$set": {"needs_reassessment": True}})

    return {"status": "recorded", "severity": severity,
            "message": "Reaction logged. We've added it to your timeline — please consult a physician if symptoms persist or worsen."}

