"""
Ayura AI - Chat Service
Single source of truth for all chat AI logic, shared by both the HTTP
endpoint (POST /chat/message) and the WebSocket handler (/chat/ws/{session_id}).
"""

from __future__ import annotations

import json
import re
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field

from core.logger import logger


@dataclass
class ChatResult:
    """Result of processing a single chat message."""
    response_text: str
    sources: list[dict] = field(default_factory=list)
    symptoms_logged: list[str] = field(default_factory=list)
    plans_adapting: list[str] = field(default_factory=list)


async def save_message(db, user_id: str, session_id: str, role: str, content: str, sources: list | None = None) -> None:
    """Persist a chat message and upsert the session document."""
    if db is None:
        return
    now = datetime.now(timezone.utc)
    await db.chat_messages.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "timestamp": now,
    })
    await db.chat_sessions.update_one(
        {"session_id": session_id, "user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$setOnInsert": {"session_id": session_id, "user_id": user_id, "created_at": now},
            "$inc": {"message_count": 1},
        },
        upsert=True,
    )


async def fetch_active_plans(db, user_id: str) -> dict:
    """Return the most recent plan of each type for the user."""
    active_plans = {}
    for plan_type in ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]:
        cursor = db.plan_history.find({"user_id": user_id, "plan_type": plan_type}).sort("generated_at", -1).limit(1)
        plans = await cursor.to_list(length=1)
        if plans:
            active_plans[plan_type] = plans[0].get("plan_data", {})
    return active_plans


async def build_chat_context(
    db,
    user,
    session_id: str,
    safe_content: str,
    history_limit: int = 20,
    max_history_chars: int = 4000,
) -> tuple[str, list[dict]]:
    """Retrieve chat history + RAG context for the LLM prompt.

    Returns:
        (history_str, rag_docs)
    """
    from engine.condition_filter import condition_filter
    from ai.rag_pipeline import rag_pipeline

    # --- Chat History (sliding window by character budget) ---
    cursor = db.chat_messages.find(
        {"session_id": session_id, "user_id": user.id}
    ).sort("timestamp", 1).limit(history_limit)
    messages = await cursor.to_list(length=history_limit)

    # Build history respecting a token/character budget
    history_parts = []
    budget = max_history_chars
    for m in reversed(messages):
        line = f"{m['role'].upper()}: {m['content']}"
        if len(line) > budget:
            break
        history_parts.insert(0, line)
        budget -= len(line)
    history_str = "\n".join(history_parts)

    # --- Symptom → Condition mapping ---
    words = safe_content.lower().replace(",", " ").replace(".", " ").replace("?", " ").split()
    ml_conditions = condition_filter.map_symptoms_to_conditions(words)
    top_conditions = [k for k, v in ml_conditions.items() if v > 0.3]

    # --- RAG Retrieval ---
    dosha = user.dominant_dosha or "pitta"
    query = f"{safe_content} {dosha} dosha " + " ".join(top_conditions)

    docs = await rag_pipeline.query(query, "ayurveda", n_results=3, dosha_filter=dosha)
    if not docs:
        docs = await rag_pipeline.query(query, "remedy", n_results=2)
    context_text = rag_pipeline.format_context(docs, max_chars=2000)

    return history_str, docs, context_text, top_conditions, dosha


def build_chat_prompt(
    user,
    safe_content: str,
    history_str: str,
    context_text: str,
    top_conditions: list[str],
    dosha: str,
    active_plans: dict,
    stream_mode: bool = False,
) -> str:
    """Build the LLM prompt for the chat message."""
    plans_json = json.dumps(active_plans, default=str)[:1500]

    if stream_mode:
        # Streaming: plain text output with embedded XML tags
        return f"""You are the Ayura AI Health Assistant.
USER PROFILE: Dosha: {dosha}, Medical History: {user.medical_history}
CURRENT CONDITIONS: {top_conditions}

ACTIVE PLANS:
{plans_json}

CHAT HISTORY:
{history_str}

RAG KNOWLEDGE:
{context_text}

USER MESSAGE: {safe_content}

Respond helpfully and conversationally. DO NOT use markdown code blocks or JSON.
If the user explicitly reports a new symptom (e.g. "I have a headache"), append at the end:
<symptoms>symptom1, symptom2</symptoms>
If the user complains about a specific plan (e.g. "my diet is too hard"), append at the end:
<plans>diet</plans>
"""
    else:
        # HTTP: structured JSON output
        return f"""You are the Ayura AI Health Assistant.
USER PROFILE: Dosha: {dosha}, Medical History: {user.medical_history}
CURRENT CONDITIONS: {top_conditions}

ACTIVE PLANS:
{plans_json}

CHAT HISTORY:
{history_str}

RAG KNOWLEDGE:
{context_text}

USER MESSAGE: {safe_content}

Respond to the user as a helpful Ayurvedic health assistant.
If the user explicitly reports a new symptom, include it in symptoms_to_log.
If the user complains about a specific plan, include the plan type in plans_to_adapt
(valid values: gym, yoga, diet, panchakarma, remedies, medicines).

OUTPUT FORMAT: Return ONLY valid JSON.
{{
    "response_text": "Your conversational reply here",
    "symptoms_to_log": ["symptom1", "symptom2"],
    "plans_to_adapt": ["diet"]
}}
"""


async def apply_chat_side_effects(
    db,
    user_id: str,
    symptoms_to_log: list[str],
    plans_to_adapt: list[str],
    feedback_text: str,
) -> None:
    """Apply symptom logging and trigger plan adaptations as side effects.

    Runs after the response has been sent to the user.
    """
    now = datetime.now(timezone.utc)

    if symptoms_to_log:
        await db.users.update_one(
            {"_id": user_id},
            {"$addToSet": {"current_symptoms": {"$each": symptoms_to_log}}}
        )
        for symptom in symptoms_to_log:
            await db.timeline.insert_one({
                "user_id": user_id,
                "event_type": "symptom_logged",
                "details": symptom,
                "source": "chat",
                "timestamp": now,
            })
        try:
            from services.audit_service import log_symptom_change
            await log_symptom_change(db, user_id, "added", symptoms_to_log, source="chat")
        except Exception:
            pass

    if plans_to_adapt:
        valid_plans = [p for p in plans_to_adapt if p in ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]]
        if valid_plans:
            # Trigger plan adaptation asynchronously (non-blocking)
            asyncio.create_task(_adapt_plans(db, user_id, valid_plans, feedback_text))


async def _adapt_plans(db, user_id: str, plan_types: list[str], feedback: str) -> None:
    """Background task: regenerate the specified plans with user feedback."""
    from ai.agents.plan_graph import generate_single_plan
    from schemas.user_schema import UserDocument, PlanHistoryDocument
    import uuid

    user_dict = await db.users.find_one({"_id": user_id})
    if not user_dict:
        return

    user = UserDocument(**user_dict)
    user_profile = {
        "name": user.name, "gender": user.gender, "age": user.age,
        "height_cm": user.height_cm, "weight_kg": user.weight_kg,
        "bmi": user.bmi, "bmi_category": user.bmi_category,
        "dosha_scores": user.dosha_scores, "dominant_dosha": user.dominant_dosha,
        "secondary_dosha": user.secondary_dosha,
        "medical_history": user.medical_history or [],
        "current_symptoms": user.current_symptoms or [],
        "current_medications": user.current_medications or [],
        "fitness_level": user.fitness_level or "beginner",
        "activity_level": user.activity_level or "moderate",
        "goal": user.goal, "rating_preferences": {},
    }

    PLAN_DATA_KEYS = {
        "gym": "gym_plan", "yoga": "yoga_plan", "diet": "diet_plan",
        "panchakarma": "panchakarma_plan", "remedies": "home_remedies", "medicines": "medicines",
    }

    for plan_type in plan_types:
        try:
            final_state = await asyncio.wait_for(
                generate_single_plan(plan_type, user_profile, feedback=feedback),
                timeout=90,
            )
            plan_data_key = PLAN_DATA_KEYS.get(plan_type, f"{plan_type}_plan")
            full_plan_data = {
                "user_summary": {"name": user.name, "dominant_dosha": user.dominant_dosha},
                plan_data_key: final_state.get(plan_data_key),
                "health_risks": final_state.get("health_risks", []),
                "safety_checks": final_state.get("safety_checks", {}),
                "adaptation_summary": final_state.get("adaptation_summary"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generation_method": "agentic",
                "model_used": final_state.get("model_used"),
            }
            plan_id = str(uuid.uuid4())
            history = PlanHistoryDocument(
                _id=plan_id, user_id=user_id, plan_type=plan_type,
                generation_method="agentic", model_used=full_plan_data.get("model_used"),
                plan_data=full_plan_data, generated_at=datetime.now(timezone.utc)
            )
            await db.plan_history.insert_one(history.model_dump(by_alias=True))
            logger.info("Adapted %s plan for user %s (via chat)", plan_type, user_id)
        except Exception as exc:
            logger.error("Chat adaptation failed for %s: %s", plan_type, exc)


def extract_xml_tags(text: str) -> tuple[str, list[str], list[str]]:
    """Extract <symptoms> and <plans> XML tags from streaming response text.

    Returns:
        (cleaned_text, symptoms_list, plans_list)
    """
    symptoms: list[str] = []
    plans: list[str] = []

    sym_match = re.search(r"<symptoms>(.*?)</symptoms>", text, re.IGNORECASE)
    if sym_match:
        symptoms = [s.strip() for s in sym_match.group(1).split(",") if s.strip()]
        text = re.sub(r"<symptoms>.*?</symptoms>", "", text, flags=re.IGNORECASE)

    plan_match = re.search(r"<plans>(.*?)</plans>", text, re.IGNORECASE)
    if plan_match:
        plans = [p.strip().lower() for p in plan_match.group(1).split(",") if p.strip()]
        text = re.sub(r"<plans>.*?</plans>", "", text, flags=re.IGNORECASE)

    return text.strip(), symptoms, plans
