"""
Ayura AI - Feature Preference Routes

Lazily collects feature-specific inputs when the user first requests a plan.
Stored in the 'user_preferences' MongoDB collection (one document per user).

Endpoints:
    GET  /api/preferences/{feature}   - retrieve saved preferences for a feature
    POST /api/preferences/{feature}   - save/update preferences for a feature
    GET  /api/preferences             - retrieve all preferences for the user
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from typing import Literal

from database.mongodb import get_mongodb
from schemas.user_schema import UserDocument
from schemas.preferences_schema import (
    GymPreferences,
    YogaPreferences,
    DietPreferences,
    PanchakarmaPreferences,
    RemedyPreferences,
    RoutinePreferences,
    PreferencesResponse,
)
from routes.profile import get_current_user

router = APIRouter()

# Valid feature names
FeatureType = Literal["gym", "yoga", "diet", "panchakarma", "remedies", "medicines", "routine"]

# Map feature name to its schema class
PREFERENCE_SCHEMAS = {
    "gym": GymPreferences,
    "yoga": YogaPreferences,
    "diet": DietPreferences,
    "panchakarma": PanchakarmaPreferences,
    "remedies": RemedyPreferences,
    "medicines": RemedyPreferences,   # medicines shares remedy preferences
    "routine": RoutinePreferences,
}


async def _get_user_preferences(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    """Fetch the user_preferences document. Returns empty dict if not found."""
    doc = await db.user_preferences.find_one({"user_id": user_id})
    return doc or {}


# ─── GET all preferences ──────────────────────────────────────────────────────

@router.get("/")
async def get_all_preferences(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Retrieve all saved feature preferences for the current user.
    Returns a dict with feature names as keys.
    """
    doc = await _get_user_preferences(db, user.id)
    # Remove internal fields
    doc.pop("_id", None)
    doc.pop("user_id", None)
    doc.pop("updated_at", None)
    return {
        "user_id": user.id,
        "preferences": doc,
        "is_set": bool(doc),
    }


# ─── GET preferences for one feature ─────────────────────────────────────────

@router.get("/{feature}", response_model=PreferencesResponse)
async def get_feature_preferences(
    feature: FeatureType,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Retrieve saved preferences for a specific feature.
    Returns defaults if the user has not yet set them.
    """
    if feature not in PREFERENCE_SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Unknown feature '{feature}'")

    doc = await _get_user_preferences(db, user.id)
    # medicines shares the remedies preference document
    storage_key = "remedies" if feature == "medicines" else feature
    saved = doc.get(storage_key)

    if saved:
        return PreferencesResponse(feature=feature, preferences=saved, is_set=True)
    else:
        # Return schema defaults
        schema_class = PREFERENCE_SCHEMAS[feature]
        defaults = schema_class().model_dump()
        return PreferencesResponse(feature=feature, preferences=defaults, is_set=False)


# ─── POST gym preferences ─────────────────────────────────────────────────────

@router.post("/gym", response_model=PreferencesResponse)
async def save_gym_preferences(
    prefs: GymPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update gym workout preferences.
    Includes gym_goal, workout schedule, equipment, and exercise preferences.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "gym": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="gym", preferences=prefs_dict, is_set=True)


# ─── POST yoga preferences ────────────────────────────────────────────────────

@router.post("/yoga", response_model=PreferencesResponse)
async def save_yoga_preferences(
    prefs: YogaPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update yoga practice preferences.
    Includes yoga_goal, experience level, style, schedule.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "yoga": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="yoga", preferences=prefs_dict, is_set=True)


# ─── POST diet preferences ────────────────────────────────────────────────────

@router.post("/diet", response_model=PreferencesResponse)
async def save_diet_preferences(
    prefs: DietPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update diet preferences.
    Includes diet_goal, dietary type, allergies (safety-critical), cuisine, cooking skill.

    NOTE: food_allergies are stored here and are used as HARD EXCLUSIONS during
    plan generation — they are never passed to the LLM, always applied deterministically.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "diet": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="diet", preferences=prefs_dict, is_set=True)


# ─── POST panchakarma preferences ────────────────────────────────────────────

@router.post("/panchakarma", response_model=PreferencesResponse)
async def save_panchakarma_preferences(
    prefs: PanchakarmaPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update Panchakarma / detox preferences.
    Includes panchakarma_goal, experience, available days, setting (home vs clinic).
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "panchakarma": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="panchakarma", preferences=prefs_dict, is_set=True)


# ─── POST remedies & medicines preferences (shared) ──────────────────────────

@router.post("/remedies", response_model=PreferencesResponse)
async def save_remedy_preferences(
    prefs: RemedyPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update remedy preferences.
    Captures symptom severity, duration, and previous medicine history.
    No 'goal' field — symptoms ARE the goal for remedies and medicines.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "remedies": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="remedies", preferences=prefs_dict, is_set=True)


@router.post("/routine", response_model=PreferencesResponse)
async def save_routine_preferences(
    prefs: RoutinePreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update daily routine (Dinacharya) preferences.
    Includes wake preference, occupation type, Agni self-report, and gym/yoga integration flags.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "routine": prefs_dict,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="routine", preferences=prefs_dict, is_set=True)


@router.post("/medicines", response_model=PreferencesResponse)
async def save_medicines_preferences(
    prefs: RemedyPreferences,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """
    Save or update medicine preferences (shared with remedies).
    Medicines and remedies share the same preference document.
    """
    prefs_dict = prefs.model_dump()
    await db.user_preferences.update_one(
        {"user_id": user.id},
        {"$set": {
            "remedies": prefs_dict,   # shared storage key
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return PreferencesResponse(feature="medicines", preferences=prefs_dict, is_set=True)
