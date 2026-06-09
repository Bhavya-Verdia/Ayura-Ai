"""
Ayura AI - Pydantic Schemas for User Profile

Core user profile fields — collected during onboarding and shared across all features.
Feature-specific goals and preferences live in schemas/preferences_schema.py.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime


class UserDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    email: str
    password_hash: Optional[str] = None
    name: str = "User"
    avatar_url: Optional[str] = None
    auth_provider: str = "local"
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    phone_number: Optional[str] = None
    is_verified: bool = False
    is_admin: bool = False
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None

    # ── Dosha Profile ──────────────────────────────────────────────────────────
    dosha_scores: Optional[dict] = None
    dominant_dosha: Optional[str] = None
    secondary_dosha: Optional[str] = None
    dosha_confidence: Optional[int] = None          # 0-100 — set after quiz

    # ── Physical & Activity ────────────────────────────────────────────────────
    fitness_level: Optional[str] = None
    activity_level: Optional[str] = None
    injuries_or_limitations: Optional[list[str]] = None   # NEW — bad_knee / lower_back / shoulder / wrist

    # ── Health Profile ─────────────────────────────────────────────────────────
    medical_history: Optional[list[str]] = None
    allergies: Optional[list[str]] = None                  # NEW — gluten / dairy / nuts / etc.
    current_symptoms: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None

    # ── Lifestyle Signals ──────────────────────────────────────────────────────
    stress_level: Optional[str] = None                     # NEW — low / moderate / high / severe
    digestion_quality: Optional[str] = None                # NEW — weak / moderate / strong
    sleep_quality: Optional[str] = None                    # NEW — poor / fair / good

    # ── Safety ────────────────────────────────────────────────────────────────
    pregnancy_or_nursing: Optional[bool] = None            # NEW — CRITICAL safety gate

    # ── Deprecated — use per-feature goals in preferences_schema.py ───────────
    goal: Optional[str] = None

    onboarding_complete: bool = False
    created_at: datetime
    updated_at: datetime


class DoshaScores(BaseModel):
    vata: float = Field(..., ge=0, le=100)
    pitta: float = Field(..., ge=0, le=100)
    kapha: float = Field(..., ge=0, le=100)


class UserProfileUpdate(BaseModel):
    """
    Sent during onboarding (Step 1 & 3) or any profile edit.

    Step 1 — Basic Profile: name, gender, age, height_cm, weight_kg, pregnancy_or_nursing
    Step 2 — Dosha Quiz:    submitted via POST /api/profile/dosha-quiz (separate endpoint)
    Step 3 — Health:        medical_history, allergies, current_symptoms, current_medications,
                            fitness_level, activity_level, injuries_or_limitations,
                            stress_level, digestion_quality, sleep_quality

    NOTE: Feature-specific goals (gym_goal, diet_goal, etc.) live in preferences_schema.py
          and are submitted to POST /api/preferences/{feature}, NOT here.
    """
    # ── Step 1: Basic Profile ────────────────────────────────────────────────
    name: Optional[str] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    age: Optional[int] = Field(None, ge=10, le=120)
    height_cm: Optional[float] = Field(None, ge=50, le=300)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)

    # SAFETY CRITICAL — must be checked before ANY plan generation
    pregnancy_or_nursing: Optional[bool] = Field(
        None,
        description="True if user is pregnant or nursing. Blocks many features for safety."
    )

    # ── Step 3: Health Profile ───────────────────────────────────────────────
    # Structured checklists — see MEDICAL_HISTORY_OPTIONS in constants.py
    medical_history: Optional[list[str]] = None
    allergies: Optional[list[str]] = Field(
        None,
        description="gluten / dairy / nuts_tree / peanuts / soy / eggs / shellfish / fish / sesame"
    )
    current_symptoms: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None

    # ── Shared Preferences ───────────────────────────────────────────────────
    fitness_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")
    activity_level: Optional[str] = Field(None, pattern="^(sedentary|light|moderate|active|very_active)$")
    injuries_or_limitations: Optional[list[str]] = Field(
        None,
        description="bad_knee / lower_back / shoulder / wrist / neck / ankle / hip"
    )
    stress_level: Optional[str] = Field(
        None,
        pattern="^(low|moderate|high|severe)$",
        description="Current stress level"
    )
    digestion_quality: Optional[str] = Field(
        None,
        pattern="^(weak|moderate|strong)$",
        description="Ayurvedic Agni assessment"
    )
    sleep_quality: Optional[str] = Field(
        None,
        pattern="^(poor|fair|good)$",
        description="Current sleep quality"
    )

    # ── Dosha (set by quiz endpoint, but allow direct update too) ─────────────
    dominant_dosha: Optional[str] = Field(None, pattern="^(vata|pitta|kapha)$")
    dosha_scores: Optional[dict] = None

    # ── Deprecated global goal — kept for backwards compatibility only ─────────
    # Prefer per-feature goals in GymPreferences, YogaPreferences, etc.
    goal: Optional[str] = Field(
        None,
        pattern="^(weight_loss|muscle_gain|flexibility|balance|detox|general_wellness)$",
        description="DEPRECATED: Use per-feature goals via POST /api/preferences/{feature}"
    )


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    auth_provider: str = "local"
    is_verified: bool = False
    is_admin: bool = False

    # Basic profile
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None

    # Dosha
    dosha_scores: Optional[dict] = None
    dominant_dosha: Optional[str] = None
    secondary_dosha: Optional[str] = None
    dosha_confidence: Optional[int] = None

    # Physical
    fitness_level: Optional[str] = None
    activity_level: Optional[str] = None
    injuries_or_limitations: Optional[list[str]] = None

    # Health
    medical_history: Optional[list[str]] = None
    allergies: Optional[list[str]] = None
    current_symptoms: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None

    # Lifestyle
    stress_level: Optional[str] = None
    digestion_quality: Optional[str] = None
    sleep_quality: Optional[str] = None

    # Safety
    pregnancy_or_nursing: Optional[bool] = None

    # Deprecated
    goal: Optional[str] = None

    onboarding_complete: bool = False


class PlanHistoryDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    user_id: str
    plan_type: str
    generation_method: str = "agentic"
    model_used: Optional[str] = None
    plan_data: dict = Field(default_factory=dict)
    preference_hash: Optional[str] = None
    generated_at: datetime


class DoshaQuizAnswers(BaseModel):
    """
    Validated payload for the dosha quiz.

    Expects: {"answers": {"1": 3, "2": 5, "3": 1, ...}}
    Each question ID maps to an integer 1-5 representing the selected option.
    Scoring uses per-question dosha weights (see DOSHA_QUIZ_SCORING in profile.py).
    Supports up to 30 questions (25 standard + 5 optional Vikriti questions).
    """
    model_config = ConfigDict(populate_by_name=True)
    answers: dict[str, int]

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: dict[str, int]) -> dict[str, int]:
        if not v:
            raise ValueError("Answers dict cannot be empty")
        if len(v) < 10:
            raise ValueError("At least 10 answers required for a valid dosha assessment")
        if len(v) > 30:
            raise ValueError("Too many answers — expected at most 30 questions")
        for q_id, rating in v.items():
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise ValueError(f"Answer for question '{q_id}' must be an integer between 1 and 5")
        return v
