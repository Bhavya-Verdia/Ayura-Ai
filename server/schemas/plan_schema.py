"""
Ayura AI - Pydantic Schemas for Plans and Chat
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlanGenerationRequest(BaseModel):
    """Request to generate personalized plans."""
    plan_types: list[str] = Field(
        default=["gym", "yoga", "diet", "panchakarma", "remedies"],
        description="Which plans to generate"
    )
    mode: str = Field(default="agentic", pattern="^(rule_based|rag|agentic)$")
    feedback: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional user feedback used to adapt a previously generated plan",
    )
    previous_plan_id: Optional[str] = Field(
        default=None,
        description="Optional historical plan id to adapt from; defaults to the latest plan",
    )


class PlanResponse(BaseModel):
    id: Optional[str] = None
    user_summary: dict
    gym_plan: Optional[dict] = None
    yoga_plan: Optional[dict] = None
    diet_plan: Optional[dict] = None
    panchakarma_plan: Optional[dict] = None
    home_remedies: Optional[list[dict]] = None
    medicines: Optional[list[dict]] = None
    health_risks: Optional[list[dict]] = None
    seasonal_guidance: Optional[dict] = None
    daily_tip: Optional[str] = None
    generated_at: datetime
    generation_method: str
    model_used: Optional[str] = None
    adaptation_summary: Optional[str] = None
    source_plan_id: Optional[str] = None
    version_diff: Optional[dict] = None
    ratings: Optional[dict] = None
    safety_checks: Optional[dict] = None


class PlanRatingRequest(BaseModel):
    section: str = Field(
        ...,
        pattern="^(overall|gym_plan|yoga_plan|diet_plan|panchakarma_plan|home_remedies|seasonal_guidance|daily_tip)$",
    )
    score: int = Field(..., ge=1, le=5)
    note: Optional[str] = Field(default=None, max_length=500)


class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: list[dict] = []
    session_id: str


class ProgressLogRequest(BaseModel):
    weight_kg: Optional[float] = Field(None, ge=20, le=500)
    symptom_updates: Optional[dict] = None
    adherence_percent: Optional[int] = Field(None, ge=0, le=100)
    plan_feedback: Optional[str] = Field(None, max_length=1000)
    mood: Optional[str] = Field(None, pattern="^(great|good|okay|low|bad)$")


class ProgressResponse(BaseModel):
    current: dict
    prediction: Optional[dict] = None
    weekly_insight: Optional[str] = None
    trend: Optional[str] = None
    streak_data: Optional[dict] = None

# Package init
