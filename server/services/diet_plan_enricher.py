import json
from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Ayurvedic Nutritionist (M.D. Ayurveda, BAMS). You enrich deterministically generated Ayurvedic diet plans with personalised recipe ideas and clinical coaching insights.

You will receive a structured diet plan summary. Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and generated 7-day diet plan, provide enrichment data in this exact JSON schema:

{
  "plan_title": "string — short personalised title (e.g. 'Pitta-Cooling Detox Plan for Ravi')",
  "plan_description": "string — 2-3 sentences motivating overview specific to this user's dosha + goal + condition protocols",
  "daily_meal_ideas": {
    "Monday": {
      "breakfast": "string — appetising meal idea using the provided breakfast foods",
      "lunch": "string — appetising meal idea using the provided lunch foods",
      "snack": "string — appetising snack idea using provided snack foods",
      "dinner": "string — appetising meal idea using provided dinner foods"
    },
    "Tuesday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." },
    "Wednesday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." },
    "Thursday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." },
    "Friday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." },
    "Saturday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." },
    "Sunday": { "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "..." }
  },
  "condition_coaching": "string — 2-3 sentences on how this specific diet addresses the user's active conditions (leave empty string if no conditions)",
  "hydration_guidance": "string — dosha-specific hydration advice tailored to their water intake and current gut issue",
  "fasting_guidance": "string — Ayurvedic guidance on their intermittent fasting window or fasting days (leave empty string if no fasting)",
  "seasonal_note": "string — 1-2 sentences on how this plan aligns with the current season's Ritucharya (leave empty string if season not provided)",
  "motivational_note": "string — 1 personalised sentence addressing their specific diet goal and dosha"
}

User profile and plan:
{plan_summary_json}
"""


async def enrich_diet_plan(raw_plan: dict, user_profile: dict, diet_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        # Use Week 1 for enrichment — food pool is identical across weeks
        week1 = next(
            (w for w in raw_plan.get("four_week_plan", []) if w.get("week") == 1),
            None,
        )
        schedule_for_llm: list[dict] = []
        if week1:
            for d in week1.get("days", []):
                day_data: dict = {
                    "day": d.get("day_name"),
                    "is_fasting_day": d.get("is_fasting_day"),
                    "meals": {},
                    "approx_macros": d.get("daily_macros"),
                }
                for meal_name, items in d.get("meals", {}).items():
                    day_data["meals"][meal_name] = [item.get("name") for item in items]
                schedule_for_llm.append(day_data)

        us = raw_plan.get("user_summary", {})
        plan_summary = {
            "user": {
                "name": user_profile.get("name") or user_profile.get("full_name"),
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": us.get("dominant_dosha"),
                "agni_type": us.get("agni_type"),
                "diet_goal": us.get("diet_goal"),
                "dietary_type": us.get("dietary_type"),
                "gut_issue": us.get("gut_issue"),
                "intermittent_fasting": us.get("intermittent_fasting"),
                "fasting_days": diet_prefs.get("fasting_days"),
                "water_intake": us.get("water_intake"),
                "current_season": us.get("current_season"),
                "active_conditions": us.get("active_condition_protocols"),
                "ama_indicator": user_profile.get("ama_indicator"),
                "ojas_level": user_profile.get("ojas_level"),
                "stress_level": user_profile.get("stress_level"),
                "pregnancy": user_profile.get("pregnancy_or_nursing", False),
            },
            "week_1_schedule": schedule_for_llm,
        }

        # RAG: pull classical diet passages for this user's dosha + conditions
        dosha_r = (us.get("dominant_dosha") or user_profile.get("dominant_dosha") or "vata").lower()
        conds_r = us.get("active_condition_protocols") or []
        rag_query = f"{dosha_r} dosha Ayurvedic diet Pathya Apathya {us.get('agni_type', 'sama')} Agni"
        rag_docs = await rag_pipeline.query(rag_query, "nutrition", n_results=4, dosha_filter=dosha_r)
        if not rag_docs and conds_r:
            rag_docs = await rag_pipeline.query(f"{conds_r[0]} diet Pathya classical Ayurveda", "nutrition", n_results=3)
        rag_context = rag_pipeline.format_context(rag_docs, max_chars=1000) if rag_docs else ""

        plan_summary_str = json.dumps(plan_summary, indent=2)
        if rag_context:
            plan_summary_str += f"\n\nCLASSICAL KNOWLEDGE BASE:\n{rag_context}"

        prompt = USER_PROMPT_TEMPLATE.replace(
            "{plan_summary_json}", plan_summary_str
        )

        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )

        enrichment = json.loads(response_text)
        if "error" in enrichment:
            raise ValueError(f"LLM provider error: {enrichment['error']}")

        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalised Ayurvedic Diet Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["daily_meal_ideas"] = enrichment.get("daily_meal_ideas", {})
        raw_plan["condition_coaching"] = enrichment.get("condition_coaching", "")
        raw_plan["hydration_guidance"] = enrichment.get("hydration_guidance", "")
        raw_plan["fasting_guidance"] = enrichment.get("fasting_guidance", "")
        raw_plan["seasonal_note"] = enrichment.get("seasonal_note", "")
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider

        logger.info(f"Diet plan enriched using {llm_client.provider}")

    except Exception as e:
        logger.error(f"Failed to enrich diet plan: {e}")

    return raw_plan
