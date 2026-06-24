"""
Routine Plan Enricher
Adds LLM-generated coaching, seasonal rationale, and dosha-specific guidance
on top of the deterministic Dinacharya schedule from routine_engine.py.
"""
import json
from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

_SYSTEM_PROMPT = """
You are a senior Ayurvedic lifestyle coach (Dinacharya specialist) with deep knowledge of
Charaka Samhita Sutrasthana and Ashtanga Hridayam Sutrasthana chapters on daily routine.

You receive a structured Dinacharya schedule and user profile.
Your role is to add personalized coaching rationale that explains WHY each part of this
routine is prescribed for THIS specific person's dosha, vikriti, agni, and season.

Respond ONLY with valid JSON. No preamble, no markdown fences.
"""

_USER_PROMPT = """
Given the Dinacharya plan and user context below, provide enrichment in this EXACT JSON schema:

{{
  "plan_title": "Personalised [dosha] Dinacharya for [name] — [season] Season",
  "plan_description": "2-3 sentences: explain the classical basis for this daily routine, why it is prescribed for this dosha+vikriti combination, and the primary therapeutic goal.",
  "dosha_coaching": "2-3 sentences: how the timing and sequence of this routine specifically pacifies or balances this person's dominant vikriti. Reference the natural dosha clock (Kapha morning, Pitta midday, Vata evening).",
  "agni_coaching": "1-2 sentences: how the meal timing and morning ritual sequence in this plan is calibrated to this person's specific Agni type ({agni_type}).",
  "seasonal_rationale": "1-2 sentences: why the wake time, rituals, and dietary notes align with {season_label} Ritucharya. Reference the classical seasonal text if known.",
  "morning_ritual_rationale": {{
    "why_tongue_scraping": "1 sentence: classical basis for Jihva Nirlekhana as the first act",
    "why_oil_pulling": "1 sentence: Kavala Gandusha — what it protects at this hour",
    "why_abhyanga": "1 sentence: why self-massage before bathing is essential for this dosha"
  }},
  "sleep_coaching": "1-2 sentences: the Ayurvedic reasoning for the prescribed sleep window, referencing Ratricharya and Brahma Muhurta if applicable.",
  "integration_note": "{integration_note}",
  "weekly_theme": {{
    "Monday": "1 sentence: what to emphasise today given the overall routine — mental focus, physical energy, or restoration",
    "Tuesday": "1 sentence",
    "Wednesday": "1 sentence",
    "Thursday": "1 sentence",
    "Friday": "1 sentence",
    "Saturday": "1 sentence",
    "Sunday": "1 sentence"
  }},
  "motivational_note": "1 personalised sentence addressing their specific vikriti, goal, and season"
}}

AYURVEDIC KNOWLEDGE BASE (ground your response in these references):
{rag_context}

USER AND PLAN CONTEXT:
{plan_json}
"""


async def enrich_routine_plan(raw_plan: dict, user_profile: dict, routine_prefs: dict) -> dict:
    """Enrich the deterministic Dinacharya plan with LLM coaching and seasonal rationale."""
    raw_plan["enriched"] = False

    try:
        dosha = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha") or "vata"
        agni_type = user_profile.get("agni_type") or "sama"
        season = user_profile.get("current_season") or raw_plan.get("season") or "sharad"
        has_gym = bool(routine_prefs.get("routine", {}).get("integrate_gym_plan"))
        has_yoga = bool(routine_prefs.get("routine", {}).get("integrate_yoga_plan"))

        # Fetch grounding context from Ayurveda knowledge base
        rag_query = f"Dinacharya daily routine {dosha} dosha Ayurvedic lifestyle morning ritual"
        docs = await rag_pipeline.query(rag_query, "ayurveda", n_results=4, dosha_filter=dosha)
        rag_context = rag_pipeline.format_context(docs, max_chars=1500) or "Use classical Ashtanga Hridayam Sutrasthana (Ch. 3) and Charaka Sutrasthana (Ch. 5) Dinacharya principles."

        # Build season label
        _SEASON_LABELS = {
            "vasanta": "Vasanta (Spring)", "grishma": "Grishma (Summer)",
            "varsha": "Varsha (Monsoon)", "sharad": "Sharad (Autumn)",
            "hemanta": "Hemanta (Early Winter)", "shishira": "Shishira (Late Winter)",
        }
        season_label = _SEASON_LABELS.get(season, season.title())

        integration_parts = []
        if has_gym:
            integration_parts.append("gym workout")
        if has_yoga:
            integration_parts.append("yoga practice")
        integration_note = (
            f"This routine integrates your {' and '.join(integration_parts)} schedule. "
            "The timing blocks around these activities preserve the classical Dinacharya sequence "
            "while accommodating your existing fitness commitments."
            if integration_parts
            else "Omit this field — no gym or yoga integration requested."
        )

        plan_summary = {
            "user": {
                "name": user_profile.get("name"),
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "vikriti": dosha,
                "agni_type": agni_type,
                "current_season": season,
                "stress_level": user_profile.get("stress_level"),
                "sleep_quality": user_profile.get("sleep_quality"),
                "medical_history": (user_profile.get("medical_history") or [])[:4],
                "goal": routine_prefs.get("routine", {}).get("routine_goal") or user_profile.get("goal"),
            },
            "schedule_snapshot": {
                "wake_time": raw_plan.get("wake_time"),
                "sleep_time": raw_plan.get("sleep_time"),
                "morning_ritual_count": len(raw_plan.get("morning_rituals", [])),
                "meal_times": {
                    k: raw_plan.get("meal_schedule", {}).get(k, {}).get("time")
                    for k in ("breakfast", "lunch", "snack", "dinner")
                    if raw_plan.get("meal_schedule", {}).get(k)
                },
                "has_gym_block": has_gym,
                "has_yoga_block": has_yoga,
                "season": season_label,
            },
        }

        prompt = _USER_PROMPT.format(
            agni_type=agni_type,
            season_label=season_label,
            integration_note=integration_note,
            rag_context=rag_context,
            plan_json=json.dumps(plan_summary, indent=2),
        )

        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            json_mode=True,
        )

        enrichment = json.loads(response_text)
        if "error" in enrichment:
            raise ValueError(f"LLM error: {enrichment['error']}")

        for key in (
            "plan_title", "plan_description", "dosha_coaching", "agni_coaching",
            "seasonal_rationale", "morning_ritual_rationale", "sleep_coaching",
            "integration_note", "weekly_theme", "motivational_note",
        ):
            if key in enrichment:
                raw_plan[key] = enrichment[key]

        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        logger.info("Routine plan enriched via %s", llm_client.provider)

    except Exception as e:
        logger.error("Routine enrichment failed: %s", e)

    return raw_plan
