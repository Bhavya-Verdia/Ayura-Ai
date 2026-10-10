"""
Ayura AI - Seasonal guidance service
Builds synchronized Ritucharya guidance for both the dashboard and holistic plans.
"""

from __future__ import annotations

import json
from datetime import date

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger
from database.chromadb_client import is_chromadb_available
from engine.seasonal import get_current_season
from services.weather_service import fetch_weather


def _risk_level_for_dosha(user_dosha: str, season_dosha: str, accumulating_dosha: str) -> str:
    if user_dosha == season_dosha:
        return "high"
    if user_dosha == accumulating_dosha:
        return "medium"
    return "low"


def _fallback_recommendations(user_dosha: str, season_name: str, season_description: str) -> dict:
    return {
        "focus": f"Support steady digestion and routines during {season_name}.",
        "diet_adjustments": [
            f"Favor freshly cooked {user_dosha}-balancing meals that suit {season_name.lower()}.",
            "Stay hydrated and prefer simple meals over heavy, highly processed foods.",
            "Adjust meal temperature and spice level based on how the season feels in your body.",
        ],
        "lifestyle_changes": [
            "Keep a consistent sleep and movement routine through the season transition.",
            "Prefer moderate intensity over sudden spikes in exertion.",
            "Use yoga, breathwork, and recovery practices to prevent seasonal aggravation.",
        ],
        "avoid": [
            "Avoid abrupt routine changes during seasonal transition windows.",
            "Avoid ignoring digestive discomfort, sleep disruption, or unusual fatigue.",
            "Avoid pushing detox or workout intensity when your recovery feels poor.",
        ],
        "dosha_impact": season_description,
    }


async def build_seasonal_guidance(
    user_dosha: str,
    user_profile: dict | None = None,
    current_date: date | None = None,
) -> dict:
    """Generate normalized seasonal guidance for a user dosha.

    `user_profile` carries the patient's diseases, allergies and dietary type. It used
    to take a dosha and nothing else, while `diet_adjustments` names specific foods —
    a real Sharad card read "Favor sweet, bitter, and astringent foods such as
    **pomegranate, white rice, and leafy greens**" and "Use **cow ghee**", shown
    identically to every Pitta user. White rice is Apathya in Prameha, cow ghee is a
    declared dairy allergen, and this endpoint knew about neither.

    It is the second food-recommending surface in this app that no gate read — the
    Pathya card was the first — so it is prevented in the prompt AND filtered on the
    way out, the same order that worked for the diet brief.
    """
    season_info = get_current_season(current_date)
    risk_level = _risk_level_for_dosha(
        user_dosha,
        season_info.dominant_dosha,
        season_info.accumulating_dosha,
    )
    primary_concern = (
        season_info.dominant_dosha
        if season_info.dominant_dosha != "none"
        else season_info.accumulating_dosha
    )

    # Fetch real-time weather (optional)
    weather = await fetch_weather()

    query = (
        f"Ritucharya {season_info.name} {season_info.english_name} "
        f"diet lifestyle avoid guidance for {user_dosha} dosha"
    )
    context = ""
    try:
        if is_chromadb_available():
            docs = await rag_pipeline.query(query, "ayurveda", n_results=3, dosha_filter=user_dosha)
            context = rag_pipeline.format_context(docs, max_chars=1800)
    except Exception as rag_err:
        logger.warning("RAG query failed for seasonal guidance (using fallback): %s", rag_err)

    fallback = _fallback_recommendations(
        user_dosha=user_dosha,
        season_name=season_info.english_name,
        season_description=season_info.description,
    )

    weather_context = ""
    if weather:
        weather_context = f"""
CURRENT WEATHER (real-time):
- Temperature: {weather['temperature_c']}°C
- Humidity: {weather['humidity']}%
- Conditions: {weather['conditions']} ({weather['description']})
- Location: {weather['location']}
- Ayurvedic Impact: {weather['ayurvedic_impact']['summary']}
"""

    profile = user_profile or {}
    def _as_list(value):
        """A profile field that should be a list and is sometimes a string."""
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [v for v in (value or []) if str(v).strip()]

    conditions = _as_list(profile.get("medical_history"))
    allergies = _as_list(profile.get("allergies"))
    dietary_type = profile.get("dietary_type") or "vegetarian"
    pregnant = bool(profile.get("pregnancy_or_nursing"))

    patient_block = ""
    if conditions or allergies or pregnant:
        lines = []
        if conditions:
            lines.append(f"- Diagnosed conditions: {', '.join(str(c) for c in conditions)}")
        if allergies:
            lines.append(f"- ALLERGIES, never name these or anything containing them: "
                         f"{', '.join(str(a) for a in allergies)}")
        if pregnant:
            lines.append("- Pregnant or nursing: nothing emmenagogue, nothing raw or unpasteurised")
        patient_block = "\nTHIS PATIENT (their guidance, not a generic card):\n" + "\n".join(lines) + "\n"

    prompt = f"""
You are an Ayurvedic expert generating concise Ritucharya guidance.

USER DOSHA: {user_dosha}
DIETARY TYPE: {dietary_type} — this app serves vegetarian and vegan plans only, so
never name egg, fish, poultry or meat, not even to say to avoid it.{patient_block}
CURRENT SEASON: {season_info.name} ({season_info.english_name})
SEASON DETAILS: {season_info.description}
RISK LEVEL: {risk_level}
{weather_context}
AYURVEDIC KNOWLEDGE:
{context if context else 'Provide careful, season-aware Ayurvedic guidance.'}

Return ONLY valid JSON in this format:
{{
  "focus": "One sentence seasonal focus",
  "diet_adjustments": ["item 1", "item 2", "item 3"],
  "lifestyle_changes": ["item 1", "item 2", "item 3"],
  "avoid": ["item 1", "item 2", "item 3"],
  "dosha_impact": "How the season affects this dosha"
}}
"""

    recommendations = fallback
    if llm_client.provider != "none":
        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt="You are a precise Ayurvedic seasonal planning assistant.",
                temperature=0.4,
                json_mode=True,
                max_tokens=700,
            )
            parsed = json.loads(response)
            recommendations = {
                "focus": parsed.get("focus") or fallback["focus"],
                "diet_adjustments": parsed.get("diet_adjustments") or fallback["diet_adjustments"],
                "lifestyle_changes": parsed.get("lifestyle_changes") or fallback["lifestyle_changes"],
                "avoid": parsed.get("avoid") or fallback["avoid"],
                "dosha_impact": parsed.get("dosha_impact") or fallback["dosha_impact"],
            }
        except Exception:
            recommendations = fallback

    # The same gate the diet plan's Pathya card goes through. `diet_adjustments` is a
    # list of recommendations, so a contradicted one is WITHHELD; `avoid` is the list
    # that exists to name these foods and is never scanned. Prevention in the prompt
    # above is what usually works — this is the backstop for when it does not.
    try:
        from services.ahara_safety import apply_advisory_safety

        gated = apply_advisory_safety(
            {
                "pathya_apathya": {
                    "pathya": list(recommendations.get("diet_adjustments") or []),
                    "apathya": list(recommendations.get("avoid") or []),
                },
                "seasonal_note": recommendations.get("focus") or "",
                "condition_coaching": recommendations.get("dosha_impact") or "",
            },
            conditions, allergies, [], extra_terms={}, pregnant=pregnant,
        )
        recommendations = {
            **recommendations,
            "diet_adjustments": gated["pathya_apathya"]["pathya"],
            "withheld_for_you": [
                {"item": w["item"], "reason": w["reason"]}
                for w in gated.get("withheld_recommendations") or []
            ],
        }
    except Exception as gate_err:   # a safety layer must not lose the card
        logger.warning("seasonal guidance safety gate degraded: %s", gate_err)

    return {
        "season": season_info.name,
        "english_name": season_info.english_name,
        "focus": recommendations["focus"],
        "risk_level": risk_level,
        "primary_concern": primary_concern,
        "dominant_dosha": season_info.dominant_dosha,
        "accumulating_dosha": season_info.accumulating_dosha,
        "pacifying_dosha": season_info.pacifying_dosha,
        "description": season_info.description,
        "dosha_impact": recommendations["dosha_impact"],
        "recommendations": {
            "diet_adjustments": recommendations["diet_adjustments"],
            "lifestyle_changes": recommendations["lifestyle_changes"],
            "avoid": recommendations["avoid"],
        },
        "weather": weather,
        "context_source": {
            "weather_context": "live" if weather else "not_available",
            "generated_from": "calendar_ritu_and_rag",
        },
    }
