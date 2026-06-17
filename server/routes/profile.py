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
from schemas.user_schema import UserProfileUpdate, UserProfileResponse, DoshaQuizAnswers
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
