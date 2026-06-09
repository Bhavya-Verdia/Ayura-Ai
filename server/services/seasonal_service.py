"""
Ayura AI - Seasonal guidance service
Builds synchronized Ritucharya guidance for both the dashboard and holistic plans.
"""

from __future__ import annotations

import json
from datetime import date

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
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
    current_date: date | None = None,
) -> dict:
    """Generate normalized seasonal guidance for a user dosha."""
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
    docs = await rag_pipeline.query(query, "ayurveda", n_results=3, dosha_filter=user_dosha)
    context = rag_pipeline.format_context(docs, max_chars=1800)

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

    prompt = f"""
You are an Ayurvedic expert generating concise Ritucharya guidance.

USER DOSHA: {user_dosha}
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
