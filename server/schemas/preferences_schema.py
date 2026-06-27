"""
Ayura AI - Feature-Specific Preference Schemas

Each feature collects its own goal and relevant inputs, stored separately
from the core user profile. Collected lazily on first plan request.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ─── Allowed value sets (used in validators + API docs) ──────────────────────

GYM_GOALS = {"fat_loss", "muscle_gain", "endurance", "strength", "general_fitness"}
YOGA_GOALS = {"flexibility", "stress_relief", "strength", "balance", "healing", "spiritual"}
DIET_GOALS = {"weight_loss", "muscle_support", "gut_health", "energy", "detox", "general_wellness"}
PK_GOALS = {"detox", "rejuvenation", "stress_relief", "seasonal_cleanse", "specific_condition"}

EQUIPMENT_OPTIONS = {"bodyweight", "dumbbells", "full_gym", "resistance_bands", "kettlebell", "barbell", "cables"}
YOGA_STYLES = {"hatha", "vinyasa", "restorative", "yin", "power", "ashtanga", "kundalini"}
DIETARY_TYPES = {"vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"}
FOOD_ALLERGIES = {"gluten", "dairy", "nuts_tree", "peanuts", "soy", "eggs", "shellfish", "fish", "sesame", "mustard"}
FOOD_INTOLERANCES = {"lactose", "fructose", "histamine", "fodmap"}


# ─── Gym Preferences ─────────────────────────────────────────────────────────

class GymPreferences(BaseModel):
    """Collected on first /api/plans/gym request."""

    # Per-feature goal (replaces the removed global goal)
    gym_goal: str = Field(
        "general_fitness",
        description="fat_loss / muscle_gain / endurance / strength / general_fitness"
    )

    # Schedule
    workout_days_per_week: int = Field(4, ge=2, le=7, description="How many days per week to train")
    workout_duration_minutes: int = Field(45, ge=20, le=90, description="Target session length in minutes")

    # Equipment
    available_equipment: list[str] = Field(
        default=["bodyweight"],
        description="Available equipment: bodyweight / dumbbells / full_gym / resistance_bands / kettlebell"
    )

    # Preferences & restrictions
    exercise_preferences: Optional[dict] = Field(
        None,
        description='{"likes": ["swimming"], "dislikes": ["running"]}'
    )
    training_style: str = Field(
        "hypertrophy",
        pattern="^(strength|hypertrophy|endurance|circuit)$",
        description="Preferred training style"
    )
    cardio_preference: str = Field(
        "moderate",
        pattern="^(none|light|moderate|heavy)$",
        description="Amount of cardio to include"
    )
    target_muscle_focus: str = Field(
        "full_body",
        pattern="^(full_body|upper|lower|core|back)$",
        description="Specific muscle focus if any"
    )

    strength_level: str = Field(
        "beginner",
        pattern="^(untrained|beginner|intermediate|advanced)$",
        description="Self-assessed lifting strength: untrained | beginner | intermediate | advanced"
    )

    @field_validator("gym_goal")
    @classmethod
    def validate_gym_goal(cls, v: str) -> str:
        if v not in GYM_GOALS:
            raise ValueError(f"gym_goal must be one of {GYM_GOALS}")
        return v

    @field_validator("available_equipment")
    @classmethod
    def validate_equipment(cls, v: list[str]) -> list[str]:
        invalid = set(v) - EQUIPMENT_OPTIONS
        if invalid:
            raise ValueError(f"Unknown equipment: {invalid}. Valid: {EQUIPMENT_OPTIONS}")
        return v


# ─── Yoga Preferences ────────────────────────────────────────────────────────

class YogaPreferences(BaseModel):
    """Collected on first /api/plans/yoga request."""

    # Per-feature goal
    yoga_goal: str = Field(
        "flexibility",
        description="flexibility / stress_relief / strength / balance / healing / spiritual"
    )

    # Experience & physical
    yoga_experience: str = Field(
        "beginner",
        pattern="^(none|beginner|intermediate|advanced)$",
        description="Yoga experience level"
    )
    flexibility_level: str = Field(
        "moderate",
        pattern="^(low|moderate|high)$",
        description="Current flexibility level"
    )

    # Style preferences
    yoga_style_preference: list[str] = Field(
        default=["hatha"],
        description="hatha / vinyasa / restorative / yin / power / ashtanga / kundalini"
    )

    # Schedule
    time_available_minutes: int = Field(30, ge=15, le=90, description="Time available per session")
    time_of_day_preference: str = Field(
        "morning",
        pattern="^(morning|evening|both)$",
        description="Preferred practice time"
    )

    # Holistic additions
    pranayama_interest: str = Field(
        "yes",
        pattern="^(yes|no|already_practice)$",
        description="Interest in breathing exercises"
    )
    meditation_interest: str = Field(
        "yes",
        pattern="^(yes|no)$",
        description="Interest in guided meditation"
    )
    indoor_outdoor: str = Field(
        "indoor",
        pattern="^(indoor|outdoor|both)$",
        description="Where they practice"
    )
    physical_limitations_detail: Optional[str] = Field(
        None,
        description="Specific limitations e.g., can't sit cross-legged"
    )

    @field_validator("yoga_goal")
    @classmethod
    def validate_yoga_goal(cls, v: str) -> str:
        if v not in YOGA_GOALS:
            raise ValueError(f"yoga_goal must be one of {YOGA_GOALS}")
        return v

    @field_validator("yoga_style_preference")
    @classmethod
    def validate_styles(cls, v: list[str]) -> list[str]:
        invalid = set(v) - YOGA_STYLES
        if invalid:
            raise ValueError(f"Unknown yoga style: {invalid}. Valid: {YOGA_STYLES}")
        return v


# ─── Diet Preferences ────────────────────────────────────────────────────────

class DietPreferences(BaseModel):
    """Collected on first /api/plans/diet request."""

    # Per-feature goal
    diet_goal: str = Field(
        "general_wellness",
        description="weight_loss / muscle_support / gut_health / energy / detox / general_wellness"
    )

    # Dietary type — CRITICAL, filters entire food selection
    dietary_type: str = Field(
        "vegetarian",
        description="vegetarian / vegan / eggetarian / non_vegetarian / pescatarian"
    )

    # Safety filters — NEVER passed to LLM, always hardcoded exclusion
    food_allergies: list[str] = Field(
        default=[],
        description="gluten / dairy / nuts_tree / peanuts / soy / eggs / shellfish / fish / sesame"
    )
    food_intolerances: list[str] = Field(
        default=[],
        description="lactose / fructose / histamine / fodmap"
    )

    # Personalization
    # Note: Meals are structured into Breakfast, Lunch, Snacks, Dinner automatically
    intermittent_fasting: str = Field(
        "no",
        pattern="^(no|12:12|14:10|16:8)$",
        description="Fasting window preference"
    )
    water_intake: str = Field(
        "1-2L",
        pattern="^(< 1L|1-2L|2-3L|> 3L)$",
        description="Current daily water intake"
    )
    gut_health_issue: str = Field(
        "healthy",
        pattern="^(acidity|constipation|bloating|ibs|healthy)$",
        description="Specific digestive issues"
    )
    fasting_days: list[str] = Field(
        default=[],
        description="Specific days user fasts (e.g., Monday, Ekadashi)"
    )

    @field_validator("diet_goal")
    @classmethod
    def validate_diet_goal(cls, v: str) -> str:
        if v not in DIET_GOALS:
            raise ValueError(f"diet_goal must be one of {DIET_GOALS}")
        return v

    @field_validator("dietary_type")
    @classmethod
    def validate_dietary_type(cls, v: str) -> str:
        if v not in DIETARY_TYPES:
            raise ValueError(f"dietary_type must be one of {DIETARY_TYPES}")
        return v

    @field_validator("food_allergies")
    @classmethod
    def validate_allergies(cls, v: list[str]) -> list[str]:
        invalid = set(v) - FOOD_ALLERGIES
        if invalid:
            raise ValueError(f"Unknown allergy: {invalid}. Valid: {FOOD_ALLERGIES}")
        return v


# ─── Panchakarma Preferences ─────────────────────────────────────────────────

class PanchakarmaPreferences(BaseModel):
    """Collected on first /api/plans/panchakarma request."""

    # Per-feature goal
    panchakarma_goal: str = Field(
        "detox",
        description="detox / rejuvenation / stress_relief / seasonal_cleanse / specific_condition"
    )

    # Experience and availability
    detox_experience: str = Field(
        "none",
        pattern="^(none|some|experienced)$",
        description="Prior Panchakarma experience level"
    )
    available_time_days: int = Field(7, ge=3, le=21, description="Days available for the program")

    # Setting — determines which therapies are available
    setting: str = Field(
        "home",
        pattern="^(home|clinic|both)$",
        description="home = mild home therapies only; clinic = full Panchakarma"
    )
    self_care_time_per_day: str = Field(
        "30 min",
        pattern="^(15 min|30 min|1 hour|2\\+ hours)$",
        description="Time available daily for therapies"
    )
    access_to_ayurvedic_herbs: str = Field(
        "willing_to_buy",
        pattern="^(yes|no|willing_to_buy)$",
        description="Can they procure specific herbs"
    )
    diet_adherence_ability: str = Field(
        "partial",
        pattern="^(strict|partial|lifestyle_only)$",
        description="Ability to follow strict Kitchari mono-diet"
    )

    # Environmental & Medical Context
    current_season: Optional[str] = Field(
        None,
        description="Current season (e.g., Grishma/Summer, Varsha/Monsoon) for Ritucharya alignment"
    )
    current_ayurvedic_medicines: list[str] = Field(
        default=[],
        description="Currently taken Ayurvedic medicines to ensure therapy safety"
    )

    @field_validator("panchakarma_goal")
    @classmethod
    def validate_pk_goal(cls, v: str) -> str:
        if v not in PK_GOALS:
            raise ValueError(f"panchakarma_goal must be one of {PK_GOALS}")
        return v


# ─── Remedy Preferences ──────────────────────────────────────────────────────

class RemedyPreferences(BaseModel):
    """
    Collected on first /api/plans/remedies or /api/plans/medicines request.
    Note: No 'goal' field — symptoms ARE the goal for these features.
    """

    # Symptom context — used to calibrate remedy strength and safety gating
    symptom_severity: Optional[dict[str, str]] = Field(
        None,
        description='Per-symptom severity: {"headache": "mild", "fatigue": "moderate", "joint_pain": "severe"}'
    )
    symptom_duration: Optional[dict[str, str]] = Field(
        None,
        description='Per-symptom duration: {"headache": "recent", "fatigue": "chronic"}'
        # recent | weeks | months | chronic
    )

    # Medicines-specific safety signals
    current_allopathic_medications: list[str] = Field(
        default=[],
        description="Current allopathic medication categories — used for drug-herb interaction safety gating"
    )
    ama_self_assessment: Optional[str] = Field(
        None,
        pattern="^(high|moderate|low)$",
        description="Self-reported Ama level — overrides profile-derived ama_indicator when set"
    )

    # History
    previous_ayurvedic_medicines: list[str] = Field(
        default=[],
        description="Ayurvedic medicines previously tried — avoids repetition, captures what worked"
    )
    ingredient_access: str = Field(
        "kitchen_only",
        pattern="^(kitchen_only|can_buy_herbs|full_access)$",
        description="What level of ingredients they can access"
    )
    preference_taste_smell: Optional[list[str]] = Field(
        default=[],
        description="e.g., no_bitter, no_strong_smell"
    )

    @field_validator("symptom_severity")
    @classmethod
    def validate_severity(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return v
        valid_levels = {"mild", "moderate", "severe"}
        for symptom, level in v.items():
            if level not in valid_levels:
                raise ValueError(f"Severity for '{symptom}' must be one of {valid_levels}")
        return v

    @field_validator("symptom_duration")
    @classmethod
    def validate_duration(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return v
        valid_durations = {"recent", "weeks", "months", "chronic"}
        for symptom, duration in v.items():
            if duration not in valid_durations:
                raise ValueError(f"Duration for '{symptom}' must be one of {valid_durations}")
        return v


# ─── Routine (Dinacharya) Preferences ────────────────────────────────────────

class RoutinePreferences(BaseModel):
    """Collected on first /api/plans/routine request."""

    # Circadian preference — shifts wake-time window
    wake_preference: str = Field(
        "natural",
        pattern="^(early|natural|late)$",
        description="early = ~4:30–5:30 AM | natural = ~5:30–6:30 AM | late = ~6:30–7:30 AM",
    )

    # Occupation type — affects exercise slot intensity + sedentary movement breaks
    occupation_type: str = Field(
        "moderately_active",
        pattern="^(sedentary|moderately_active|very_active)$",
        description="sedentary (desk work) | moderately_active | very_active (manual labour / athlete)",
    )

    # Self-reported Agni — used instead of derived Agni for meal timing
    agni_type_self_report: str = Field(
        "sama",
        pattern="^(sama|manda|tikshna|vishama)$",
        description="sama (balanced) | manda (slow/sluggish) | tikshna (sharp/intense) | vishama (irregular)",
    )

    # Integration flags — if True, engine fetches latest gym/yoga plan to annotate exercise slots
    integrate_gym_plan: bool = Field(False, description="Annotate exercise slots with user's gym plan")
    integrate_yoga_plan: bool = Field(False, description="Annotate exercise slots with user's yoga plan")

    # Carry fasting signals from diet preferences (optional — used if no DietPreferences)
    fasting_days: list[str] = Field(default=[], description="Days the user fasts (e.g., Monday, Ekadashi)")
    intermittent_fasting: str = Field(
        "no",
        pattern="^(no|12:12|14:10|16:8)$",
        description="IF window for meal slot adjustment",
    )


# ─── Stored document (in MongoDB user_preferences collection) ─────────────────

class UserPreferencesDocument(BaseModel):
    """
    Stored in MongoDB collection: user_preferences
    One document per user, with preferences nested by feature.
    """
    user_id: str
    gym: Optional[GymPreferences] = None
    yoga: Optional[YogaPreferences] = None
    diet: Optional[DietPreferences] = None
    panchakarma: Optional[PanchakarmaPreferences] = None
    remedies: Optional[RemedyPreferences] = None
    routine: Optional[RoutinePreferences] = None
    updated_at: Optional[datetime] = None


# ─── Response wrapper ─────────────────────────────────────────────────────────

class PreferencesResponse(BaseModel):
    """Returned by GET /api/preferences/{feature}"""
    feature: str
    preferences: dict
    is_set: bool
