"""
Ayura AI - User Profile Routes
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
import uuid as uuid_mod
from datetime import datetime, timezone

from database.mongodb import get_mongodb
from schemas.user_schema import UserDocument
import hashlib
import json as _json

from schemas.user_schema import (
    UserProfileUpdate, UserProfileResponse, DoshaQuizAnswers,
    DoshaAssessmentRequest, VikritiCheckInRequest, PlanFeedbackRequest,
    DoshaValidationRequest,
)
from schemas.auth_schema import ChangePasswordRequest
from services.auth_service import get_current_user_id, get_token_claims, hash_password, verify_password
from config import settings
from engine.dosha_analyzer import score_dosha_quiz

router = APIRouter()


async def get_user_id(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias=settings.ACCESS_TOKEN_COOKIE),
) -> str:
    """Lightweight auth dependency: decodes JWT and returns user_id without a DB lookup.

    Use this on routes that only need to scope queries by user_id
    (e.g. notifications, reminders, community, progress log, export).
    For routes that need the full user profile, use get_current_user instead.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif access_cookie:
        token = access_cookie
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return get_current_user_id(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def get_current_user(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias=settings.ACCESS_TOKEN_COOKIE),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
) -> UserDocument:
    """Dependency: extract current user from JWT token."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif access_cookie:
        token = access_cookie

    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    try:
        user_id = get_current_user_id(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    user_dict = await db.users.find_one({"_id": user_id})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserDocument(**user_dict)


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(user: UserDocument = Depends(get_current_user)):
    """Get the current user's full profile."""
    return user


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    update: UserProfileUpdate,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update user profile (onboarding or edit)."""
    update_data = update.model_dump(exclude_unset=True)

    # Calculate BMI if height and weight are provided
    height = update_data.get("height_cm", user.height_cm)
    weight = update_data.get("weight_kg", user.weight_kg)
    if height and weight:
        bmi = weight / ((height / 100) ** 2)
        update_data["bmi"] = round(bmi, 1)
        if bmi < 18.5:
            update_data["bmi_category"] = "underweight"
        elif bmi < 25:
            update_data["bmi_category"] = "normal"
        elif bmi < 30:
            update_data["bmi_category"] = "overweight"
        else:
            update_data["bmi_category"] = "obese"

    # Determine dominant dosha if scores provided
    if "dosha_scores" in update_data and update_data["dosha_scores"]:
        scores = update_data["dosha_scores"]
        if isinstance(scores, dict):
            dosha_vals = {"vata": scores.get("vata", 0), "pitta": scores.get("pitta", 0), "kapha": scores.get("kapha", 0)}
        else:
            dosha_vals = {"vata": scores.vata, "pitta": scores.pitta, "kapha": scores.kapha}
            update_data["dosha_scores"] = {"vata": scores.vata, "pitta": scores.pitta, "kapha": scores.kapha}
        sorted_doshas = sorted(dosha_vals.items(), key=lambda x: x[1], reverse=True)
        update_data["dominant_dosha"] = sorted_doshas[0][0]
        update_data["secondary_dosha"] = sorted_doshas[1][0]

    # Apply updates
    for key, value in update_data.items():
        setattr(user, key, value)

    # Check if onboarding is complete (all essential fields filled)
    # Does NOT require goal — goals are now per-feature via preferences API
    if all([user.gender, user.age, user.height_cm, user.weight_kg]):
        if user.dosha_scores or user.dominant_dosha:
            user.onboarding_complete = True

    user.updated_at = datetime.now(timezone.utc)
    
    update_dict = {}
    for key in update_data.keys():
        update_dict[key] = getattr(user, key)
    
    update_dict["updated_at"] = user.updated_at
    if getattr(user, "onboarding_complete", False):
        update_dict["onboarding_complete"] = True
        
    await db.users.update_one(
        {"_id": user.id},
        {"$set": update_dict}
    )

    return user





@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Upload a profile avatar image. Saves to disk and stores URL (not Base64)."""
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use: {allowed}")

    MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB
    file_bytes = await file.read()
    if len(file_bytes) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_AVATAR_BYTES // (1024*1024)}MB.")

    # Magic-byte MIME verification — extension alone is spoofable
    _MAGIC = [
        (b'\xff\xd8\xff', 'image/jpeg'),
        (b'\x89PNG\r\n\x1a\n', 'image/png'),
    ]
    header = file_bytes[:12]
    detected = None
    for magic, mime in _MAGIC:
        if header.startswith(magic):
            detected = mime
            break
    if detected is None and header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        detected = 'image/webp'
    if detected is None:
        raise HTTPException(status_code=400, detail="File content is not a valid image (JPEG, PNG, or WebP).")

    # Upload logic (S3/R2 or local fallback)
    filename = f"{user.id}_{uuid_mod.uuid4().hex[:8]}{ext}"
    
    if settings.S3_BUCKET_NAME and settings.AWS_ACCESS_KEY_ID:
        import boto3
        import io
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )
        
        # Delete old avatar from S3 if it exists and is an S3 URL
        if user.avatar_url and settings.S3_BUCKET_NAME in user.avatar_url:
            try:
                old_key = user.avatar_url.split("/")[-1]
                s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=f"avatars/{old_key}")
            except Exception as e:
                pass # Non-fatal

        # Upload new avatar
        object_key = f"avatars/{filename}"
        try:
            s3_client.upload_fileobj(
                io.BytesIO(file_bytes),
                settings.S3_BUCKET_NAME,
                object_key,
                ExtraArgs={"ContentType": file.content_type or "image/jpeg"}
            )
            
            # Construct public URL (assuming public-read or CDN is configured)
            # For R2/S3, typically it's https://<bucket>.s3.<region>.amazonaws.com/<key>
            # Or if custom domain: https://assets.yourdomain.com/<key>
            # Here we'll return a generic S3 url if endpoint is not set, else construct from endpoint
            if settings.S3_ENDPOINT_URL:
                avatar_url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{object_key}"
            else:
                region = settings.S3_REGION_NAME or "us-east-1"
                avatar_url = f"https://{settings.S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{object_key}"
        except ClientError as e:
            raise HTTPException(status_code=500, detail="Failed to upload image to cloud storage")
            
    else:
        # Fallback: Delete old avatar file if it was a local upload
        if user.avatar_url and user.avatar_url.startswith("/uploads/"):
            old_path = os.path.join(settings.UPLOADS_DIR, os.path.basename(user.avatar_url))
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except OSError:
                pass

        # Save to uploads directory
        file_path = os.path.join(settings.UPLOADS_DIR, filename)
        os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        avatar_url = f"/uploads/{filename}"

    user.updated_at = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {"avatar_url": avatar_url, "updated_at": user.updated_at}}
    )

    return {"avatar_url": avatar_url, "message": "Avatar uploaded successfully"}


@router.patch("/password")
async def change_password(
    req: ChangePasswordRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Change password for local auth users."""
    if user.auth_provider != "local":
        raise HTTPException(status_code=400, detail="Password change not available for Google OAuth accounts.")

    if not user.password_hash or not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    user.password_hash = hash_password(req.new_password)
    user.updated_at = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {"password_hash": user.password_hash, "updated_at": user.updated_at}}
    )

    return {"message": "Password changed successfully."}


@router.post("/dosha-quiz", response_model=UserProfileResponse)
async def submit_dosha_quiz(
    payload: DoshaQuizAnswers,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Score a dosha quiz using per-question weighted scoring (see engine/dosha_analyzer.py)."""
    result = score_dosha_quiz(payload.answers)
    dosha_scores = {"vata": result["vata"], "pitta": result["pitta"], "kapha": result["kapha"]}
    dominant_dosha = result["dominant_dosha"]
    secondary_dosha = result["secondary_dosha"]
    dosha_confidence = result["dosha_confidence"]

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {
            "dosha_scores": dosha_scores,
            "dominant_dosha": dominant_dosha,
            "secondary_dosha": secondary_dosha,
            "dosha_confidence": dosha_confidence,
            "updated_at": now,
        }}
    )
    user.dosha_scores = dosha_scores
    user.dominant_dosha = dominant_dosha
    user.secondary_dosha = secondary_dosha
    user.dosha_confidence = dosha_confidence
    user.updated_at = now
    return user


@router.post("/dosha-assessment", response_model=UserProfileResponse)
async def submit_dosha_assessment(
    req: DoshaAssessmentRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """LLM-powered Prakriti + Vikriti assessment from physical traits + current symptoms."""
    from engine.dosha_analyzer import assess_dosha_with_llm
    from core.cache import cache_manager

    user_profile_ctx = {
        "age": user.age,
        "gender": user.gender,
        "stress_level": user.stress_level,
        "sleep_quality": user.sleep_quality,
        "digestion_quality": user.digestion_quality,
        "medical_history": user.medical_history,
        "fitness_level": user.fitness_level,
    }

    _cache_input = {
        "traits": req.physical_traits.model_dump(),
        "symptoms": sorted(req.current_symptoms),
        "age": user.age,
        "gender": user.gender,
        "stress": user.stress_level,
        "sleep": user.sleep_quality,
        "digestion": user.digestion_quality,
    }
    _cache_key = "dosha_assess:" + hashlib.sha256(
        _json.dumps(_cache_input, sort_keys=True).encode()
    ).hexdigest()
    _CACHE_TTL = 60 * 60 * 24  # 24 hours

    result = None
    if cache_manager.redis_client:
        try:
            _cached = await cache_manager.redis_client.get(_cache_key)
            if _cached:
                result = _json.loads(_cached)
        except Exception:
            pass

    if result is None:
        result = await assess_dosha_with_llm(
            req.physical_traits.model_dump(),
            req.current_symptoms,
            user_profile=user_profile_ctx,
        )
        if cache_manager.redis_client:
            try:
                await cache_manager.redis_client.setex(_cache_key, _CACHE_TTL, _json.dumps(result))
            except Exception:
                pass

    from engine.dosha_analyzer import _vikriti_secondary as _vs_da
    now = datetime.now(timezone.utc)
    update_fields = {
        "dosha_scores": result["prakriti"],
        "dominant_dosha": result["prakriti_dominant"],
        "secondary_dosha": result["prakriti_secondary"],
        "dosha_confidence": result["confidence_score"],
        "vikriti_scores": result["vikriti"],
        "vikriti_dominant": result["vikriti_dominant"],
        "vikriti_secondary": _vs_da(result["vikriti"]),
        "dosha_constitution_type": result["constitution_type"],
        "dosha_explanation": result["explanation"],
        "dosha_immediate_focus": result["immediate_focus"],
        "dosha_key_signals": result["key_signals"],
        "dosha_contradictions": result.get("contradictions", []),
        "primary_gunas": result.get("primary_gunas", []),
        "manas_prakriti": result.get("manas_prakriti"),
        "prakriti_classical_type": result.get("prakriti_classical_type"),
        "prakriti_classical_name": result.get("prakriti_classical_name"),
        "ama_indicator": result.get("ama_indicator", "none"),
        "updated_at": now,
    }

    for key, value in update_fields.items():
        setattr(user, key, value)

    if all([user.gender, user.age, user.height_cm, user.weight_kg]):
        update_fields["onboarding_complete"] = True
        user.onboarding_complete = True

    await db.users.update_one({"_id": user.id}, {"$set": update_fields})
    return user


@router.post("/vikriti-checkin", response_model=UserProfileResponse)
async def vikriti_checkin(
    req: VikritiCheckInRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Weekly Vikriti update with adaptive blending, prakriti anchoring, and history tracking."""
    from engine.dosha_analyzer import (
        _apply_seasonal_correction,
        _blend_vikriti,
        _compute_symptom_signal,
        _confidence_from_checkins,
        _lifestyle_pulse_signal,
        _symptom_persistence_weights,
        _vikriti_secondary,
    )

    old_vikriti = user.vikriti_scores or {"vata": 33, "pitta": 33, "kapha": 34}
    prakriti = user.dosha_scores
    existing_history: list = user.vikriti_history or []

    meaningful = [s for s in req.current_symptoms if s != "feeling_balanced"]
    persistence_weights = _symptom_persistence_weights(meaningful, existing_history) if meaningful else None
    symptom_signal = _compute_symptom_signal(meaningful, persistence_weights) if meaningful else {}
    lifestyle_signal = _lifestyle_pulse_signal(
        req.sleep_this_week,
        req.stress_this_week,
        req.digestion_this_week,
    )

    blended = _blend_vikriti(
        old_vikriti, symptom_signal, len(meaningful), prakriti, lifestyle_signal or None
    )
    blended = _apply_seasonal_correction(blended)

    # Menstrual phase: Pitta naturally elevates during menstruation (classical artava teaching)
    if req.menstrual_phase and user.gender == "female":
        blended["pitta"] = min(68, round(blended.get("pitta", 33) * 1.12))
        _menses_total = sum(blended.values()) or 1
        blended = {d: round(v / _menses_total * 100) for d, v in blended.items()}
        _diff = 100 - sum(blended.values())
        if _diff != 0:
            blended[max(blended, key=blended.get)] += _diff

    new_checkin_count = (user.checkin_count or 0) + 1
    new_confidence = _confidence_from_checkins(
        user.dosha_confidence or 35, new_checkin_count
    )

    now = datetime.now(timezone.utc)
    vikriti_dominant = max(blended, key=blended.get)
    vikriti_sec = _vikriti_secondary(blended)

    # Rolling 12-week history — store symptoms and pulse values for persistence tracking
    history_entry = {
        "scores": blended,
        "dominant": vikriti_dominant,
        "symptom_count": len(meaningful),
        "symptoms": meaningful,
        "pulse": {
            "sleep": req.sleep_this_week,
            "stress": req.stress_this_week,
            "digestion": req.digestion_this_week,
        },
        "ts": now.isoformat(),
    }
    updated_history = (existing_history + [history_entry])[-12:]

    update = {
        "vikriti_scores": blended,
        "vikriti_dominant": vikriti_dominant,
        "vikriti_secondary": vikriti_sec,
        "dosha_confidence": new_confidence,
        "checkin_count": new_checkin_count,
        "vikriti_history": updated_history,
        "last_vikriti_checkin": now,
        "updated_at": now,
    }
    await db.users.update_one({"_id": user.id}, {"$set": update})
    for k, v in update.items():
        setattr(user, k, v)
    return user


@router.post("/plan-feedback", response_model=UserProfileResponse)
async def submit_plan_feedback(
    req: PlanFeedbackRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Record plan improvement feedback; adjusts Vikriti scores slightly."""
    from engine.dosha_analyzer import _apply_seasonal_correction

    now = datetime.now(timezone.utc)
    vikriti = dict(user.vikriti_scores or {"vata": 33, "pitta": 33, "kapha": 34})
    dominant = user.vikriti_dominant

    if dominant:
        if not req.improved:
            vikriti[dominant] = min(100, round(vikriti[dominant] * 1.06))
        else:
            vikriti[dominant] = max(5, round(vikriti[dominant] * 0.95))
        total = sum(vikriti.values()) or 1
        vikriti = {d: round(v / total * 100) for d, v in vikriti.items()}
        vikriti = _apply_seasonal_correction(vikriti)

    from engine.dosha_analyzer import _vikriti_secondary as _vs_pf
    new_dominant = max(vikriti, key=vikriti.get)

    # Track consecutive "not working" signal for re-assessment trigger
    if not req.improved:
        new_streak = (user.plan_not_working_streak or 0) + 1
    else:
        new_streak = 0

    update = {
        "vikriti_scores": vikriti,
        "vikriti_dominant": new_dominant,
        "vikriti_secondary": _vs_pf(vikriti),
        "plan_not_working_streak": new_streak,
        "last_plan_feedback": now,
        "updated_at": now,
    }
    await db.users.update_one({"_id": user.id}, {"$set": update})
    for k, v in update.items():
        setattr(user, k, v)
    user.plan_not_working_streak = new_streak
    return user


@router.post("/dosha-validation", response_model=UserProfileResponse)
async def submit_dosha_validation(
    req: DoshaValidationRequest,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """14-day plan validation: adjusts Vikriti and confidence based on reported improvement."""
    from engine.dosha_analyzer import _apply_seasonal_correction, _anchor_to_prakriti

    now = datetime.now(timezone.utc)
    vikriti = dict(user.vikriti_scores or {"vata": 33, "pitta": 33, "kapha": 34})
    prakriti = user.dosha_scores
    dominant = user.vikriti_dominant
    confidence_score = user.dosha_confidence or 35

    if dominant:
        if req.improved:
            # Plans are working — pull vikriti toward prakriti (recovery signal).
            # If prakriti exists, blend 15% toward it; otherwise just reduce dominant.
            if prakriti:
                vikriti = {
                    d: round(0.85 * vikriti.get(d, 33) + 0.15 * prakriti.get(d, 33))
                    for d in ["vata", "pitta", "kapha"]
                }
            else:
                vikriti[dominant] = max(10, round(vikriti[dominant] * 0.90))
            confidence_score = min(92, confidence_score + 8)
        else:
            # Plans are not working — imbalance is persisting or worsening.
            vikriti[dominant] = min(70, round(vikriti[dominant] * 1.06))
            confidence_score = max(20, confidence_score - 5)

        total = sum(vikriti.values()) or 1
        vikriti = {d: round(v / total * 100) for d, v in vikriti.items()}
        diff = 100 - sum(vikriti.values())
        if diff != 0:
            vikriti[max(vikriti, key=vikriti.get)] += diff

        if prakriti:
            vikriti = _anchor_to_prakriti(vikriti, prakriti)
        vikriti = _apply_seasonal_correction(vikriti)

    from engine.dosha_analyzer import _vikriti_secondary as _vs_dv
    new_dominant = max(vikriti, key=vikriti.get)
    update = {
        "vikriti_scores": vikriti,
        "vikriti_dominant": new_dominant,
        "vikriti_secondary": _vs_dv(vikriti),
        "dosha_confidence": confidence_score,
        "last_dosha_validation": now,
        "updated_at": now,
    }
    await db.users.update_one({"_id": user.id}, {"$set": update})
    for k, v in update.items():
        setattr(user, k, v)
    user.needs_reassessment = (
        (user.plan_not_working_streak or 0) >= 3
        or (not req.improved and (user.dosha_confidence or 0) < 40)
    )
    return user


@router.post("/tongue-assessment")
async def tongue_assessment(
    file: UploadFile = File(...),
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Analyze tongue photo for Ayurvedic Vikriti indicators using GPT-4o vision."""
    import base64
    import json
    from ai.llm_client import llm_client
    from engine.dosha_analyzer import _apply_seasonal_correction

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Please upload a JPEG, PNG, or WebP image.")

    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be under 8 MB.")

    image_b64 = base64.b64encode(raw).decode()
    mime_type = file.content_type or "image/jpeg"

    system_prompt = (
        "You are an expert Ayurvedic physician (Vaidya) trained in Jihva Pareeksha (tongue diagnosis) "
        "from Charaka Samhita and Ashtanga Hridayam. "
        "Vata tongue: dry, cracked, rough, brownish, or thin. "
        "Pitta tongue: red or yellow coating, inflamed tip, blisters, sharp red edges. "
        "Kapha tongue: thick white or pale coating, swollen, moist, scalloped edges."
    )
    user_prompt = (
        "Analyze this tongue image for Ayurvedic Vikriti indicators. "
        'Respond ONLY with valid JSON: {"vata_signals": ["..."], "pitta_signals": ["..."], "kapha_signals": ["..."], '
        '"vikriti_adjustment": {"vata": <-10 to 10>, "pitta": <-10 to 10>, "kapha": <-10 to 10>}, '
        '"tongue_summary": "...", "confidence": "low|medium|high", "image_quality": "poor|adequate|good"}'
    )

    result_text = await llm_client.generate_vision(
        prompt=user_prompt,
        system_prompt=system_prompt,
        image_b64=image_b64,
        mime_type=mime_type,
    )

    try:
        result = json.loads(result_text)
        if "error" in result:
            raise HTTPException(status_code=503, detail="Vision assessment temporarily unavailable.")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Could not parse tongue assessment result.")

    from engine.dosha_analyzer import _anchor_to_prakriti
    old_vikriti = dict(user.vikriti_scores or {"vata": 33, "pitta": 33, "kapha": 34})
    adj = result.get("vikriti_adjustment", {})
    adjusted = {d: max(5, min(100, old_vikriti.get(d, 33) + adj.get(d, 0))) for d in ["vata", "pitta", "kapha"]}
    total = sum(adjusted.values()) or 1
    new_vikriti = {d: round(v / total * 100) for d, v in adjusted.items()}
    if user.dosha_scores:
        new_vikriti = _anchor_to_prakriti(new_vikriti, user.dosha_scores)
    from engine.dosha_analyzer import _vikriti_secondary as _vs_ta
    new_vikriti = _apply_seasonal_correction(new_vikriti)
    new_dominant = max(new_vikriti, key=new_vikriti.get)

    now = datetime.now(timezone.utc)
    await db.users.update_one({"_id": user.id}, {"$set": {
        "vikriti_scores": new_vikriti,
        "vikriti_dominant": new_dominant,
        "vikriti_secondary": _vs_ta(new_vikriti),
        "updated_at": now,
    }})

    return {
        "vikriti_scores": new_vikriti,
        "vikriti_dominant": new_dominant,
        "tongue_summary": result.get("tongue_summary", ""),
        "vata_signals": result.get("vata_signals", []),
        "pitta_signals": result.get("pitta_signals", []),
        "kapha_signals": result.get("kapha_signals", []),
        "confidence": result.get("confidence", "low"),
        "image_quality": result.get("image_quality", "adequate"),
    }
