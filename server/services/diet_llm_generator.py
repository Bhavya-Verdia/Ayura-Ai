"""
LLM-primary diet plan generator.

The rule engine (diet_plan_engine.py) builds a structured Ayurvedic brief from the
user's profile. This module sends that brief to the LLM and receives a complete 4-week
plan with real Indian meal names, Pathya-Apathya, and classical text references.

Knowledge constants, brief builder, and allergen scanner live in diet_brief_builder.py.
The rule engine is retained as a fallback if the LLM call fails (see routes/plans.py).
"""
import json
from datetime import datetime, timezone

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger
from services.diet_brief_builder import (
    MEAL_TIMING,
    DOSHA_SPICES,
    AYUR_TIPS,
    COND_ALIASES,
    build_brief,
    flag_allergens,
)

SYSTEM_PROMPT = """\
You are a senior Vaidya (M.D. Ayurveda, BAMS+) and clinical nutritionist with mastery of \
Charaka Samhita, Ashtanga Hridayam, Sushruta Samhita, Madhava Nidana, and Bhavaprakasha. \
You generate clinically precise, highly personalised Ayurvedic diet plans.

RULES — these are non-negotiable:
1. Generate REAL Indian meal names. Write "Moong Dal Khichdi with ajwain-hing tadka" — \
   not food lists like "Moong Dal + Rice + Ajwain".
2. Every meal must have an Ayurvedic rationale citing Rasa (taste), Guna (quality), \
   Virya (potency), Vipaka (post-digestive effect).
3. For every medical condition, provide classical Pathya-Apathya with Samhita references.
4. Flag all Viruddha Ahara (incompatible food combinations) relevant to this patient.
5. STRICTLY honour all hard constraints — dietary type, allergies, intolerances.
6. Use the patient's Agni type to determine meal heaviness and frequency.
7. High Ama = all meals must be Deepaniya + Pachana; no heavy, sour, or fermented foods.
8. Each day should have a therapeutic theme (e.g., "Ama Pachana", "Agni Deepana", "Ojas Building").
9. Include a special Ayurvedic drink (Kashaya, Kwatha, herbal milk, or medicinal water) \
   for each day with timing and rationale.
10. Meals should reflect genuine Indian culinary tradition — realistic, preparable at home.
11. Structure the plan as a 4-week Ayurvedic progression: \
    Week 1 (Ama Pachana): Light, Deepaniya-Pachana foods — clear Ama. Avoid heavy, sour, fermented. \
    Week 2 (Agni Deepana): Kindle Agni with warming spices. Gradually richer meals. \
    Week 3 (Brimhana): Nourishing foods — Ojas-building. Ghee, nuts, root vegetables where appropriate. \
    Week 4 (Rasayana): Rejuvenating, seasonal, maintenance. Introduce Rasayana ingredients (amla, ashwagandha milk, dates). \
    Week 1 must be FULL DETAIL (all meal fields). Weeks 2-4 are COMPACT (meal names only as strings).

Respond ONLY with valid JSON. No preamble. No markdown fences. No explanation outside JSON.
"""

USER_PROMPT_TEMPLATE = """\
Generate a complete 4-week personalised Ayurvedic diet plan for this patient:

{brief}

Return this exact JSON structure — no extra keys, no preamble, no markdown fences:
{{
  "plan_title": "string — personalised title, e.g. 'Vata-Pacifying 4-Week Renewal Plan for Ravi'",
  "plan_description": "string — 2-3 sentences: clinical rationale, dosha logic, conditions addressed",
  "pathya_apathya": {{
    "pathya": ["food/preparation — 1 sentence Ayurvedic reason"],
    "apathya": ["food/preparation — 1 sentence reason to avoid"],
    "viruddha_ahara_warnings": ["combination to avoid — classical reason"],
    "classical_reference": "primary Samhita reference(s) for this case"
  }},
  "weeks": [
    {{
      "week_number": 1,
      "phase": "Ama Pachana",
      "phase_description": "string — 1-2 sentences on this week's therapeutic focus",
      "daily_plan": {{
        "Monday": {{
          "theme": "string — 2-3 word therapeutic theme",
          "breakfast": {{
            "meal_name": "string — real Indian dish name",
            "description": "string — what it is + brief preparation in 1 sentence",
            "key_ingredients": ["ingredient 1", "ingredient 2"],
            "portion": "string — realistic serving e.g. '1 katori (150ml) with 1 tsp ghee'",
            "ayurvedic_note": "string — Rasa-Guna-Virya-Vipaka reasoning in 1-2 sentences",
            "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}
          }},
          "lunch": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "snack": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "dinner": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "special_drink": {{
            "name": "string — e.g. 'CCF Tea (Cumin-Coriander-Fennel)'",
            "when": "string — e.g. 'Morning on empty stomach'",
            "recipe": "string — brief recipe in 1 sentence",
            "rationale": "string — therapeutic reason"
          }}
        }},
        "Tuesday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Wednesday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Thursday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Friday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Saturday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Sunday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}}
      }}
    }},
    {{
      "week_number": 2,
      "phase": "Agni Deepana",
      "phase_description": "string — 1-2 sentences on this week's therapeutic focus",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "Indian meal name", "lunch": "Indian meal name", "snack": "Indian meal name", "dinner": "Indian meal name", "special_drink": "drink name — timing"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }},
    {{
      "week_number": 3,
      "phase": "Brimhana",
      "phase_description": "string",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }},
    {{
      "week_number": 4,
      "phase": "Rasayana",
      "phase_description": "string",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }}
  ],
  "condition_coaching": "string — 2-3 sentences specific to their conditions and how this diet addresses them",
  "hydration_guidance": "string — specific guidance for their dosha, water intake, and gut issue",
  "fasting_guidance": "string — Ayurvedic guidance on their fasting pattern (empty string if none)",
  "seasonal_note": "string — how this plan aligns with Ritucharya (empty string if season unknown)",
  "ahar_vidhi": "string — 2-3 key Ahar Vidhi (eating rules) specific to this patient's Agni and Dosha",
  "motivational_note": "string — 1 personalised, clinically grounded sentence"
}}
"""


async def generate_diet_plan_llm(
    user_profile: dict,
    diet_prefs: dict,
) -> dict | None:
    """
    Returns a complete diet plan dict or None on failure (caller falls back to rule engine).
    """
    try:
        brief = build_brief(user_profile, diet_prefs)

        # RAG: pull classical text passages relevant to this patient's profile
        dominant_dosha_q = (user_profile.get("dominant_dosha") or "vata").lower()
        agni_type_q = (user_profile.get("agni_type") or "sama").lower()
        conditions_q = user_profile.get("medical_history") or []
        rag_context_parts: list[str] = []

        # Query 1: dosha + agni general diet guidance
        general_query = f"{dominant_dosha_q} dosha diet Ahara Pathya Apathya {agni_type_q} Agni Ayurvedic food"
        general_docs = await rag_pipeline.query(general_query, "nutrition", n_results=5, dosha_filter=dominant_dosha_q)
        if general_docs:
            rag_context_parts.append(rag_pipeline.format_context(general_docs, max_chars=1200))

        # Query 2: condition-specific diet if conditions exist
        if conditions_q:
            cond_query = f"{conditions_q[0]} Pathya Apathya diet Ayurvedic classical"
            cond_docs = await rag_pipeline.query(cond_query, "nutrition", n_results=4)
            if cond_docs:
                rag_context_parts.append(rag_pipeline.format_context(cond_docs, max_chars=800))

        # Query 3: seasonal diet
        season = (user_profile.get("current_season") or "").lower()
        if season:
            season_docs = await rag_pipeline.query(f"{season} Ritucharya diet seasonal Ayurveda", "nutrition", n_results=3)
            if season_docs:
                rag_context_parts.append(rag_pipeline.format_context(season_docs, max_chars=600))

        rag_context = "\n\n".join(rag_context_parts) if rag_context_parts else ""

        # Inject RAG context into brief if retrieved
        if rag_context:
            brief = brief + f"\n\nCLASSICAL KNOWLEDGE BASE (cite these references where relevant):\n{rag_context}"

        prompt = USER_PROMPT_TEMPLATE.replace("{brief}", brief)

        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )

        data = json.loads(response_text)
        if "error" in data:
            raise ValueError(f"LLM returned error: {data['error']}")
        if "weeks" not in data or not isinstance(data["weeks"], list):
            raise ValueError("LLM response missing 'weeks' array")

        dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
        agni_type = (user_profile.get("agni_type") or "sama").lower()
        conditions = user_profile.get("medical_history") or []
        norm_conds = [COND_ALIASES.get(c.lower().replace(" ", "_"), c.lower().replace(" ", "_")) for c in conditions]

        user_id = str(user_profile.get("id") or user_profile.get("_id") or "anon")

        _DAY_ALIASES = {
            "monday": "monday", "tuesday": "tuesday", "wednesday": "wednesday",
            "thursday": "thursday", "friday": "friday", "saturday": "saturday", "sunday": "sunday",
            "mon": "monday", "tue": "tuesday", "wed": "wednesday",
            "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday",
        }

        # Tag fasting days and run allergen check on week 1 (full detail)
        fasting_days_raw = diet_prefs.get("fasting_days") or []
        fasting_set = {d.lower() for d in fasting_days_raw}
        weeks = data["weeks"]
        week1_daily = weeks[0].get("daily_plan", {}) if weeks else {}
        for day_name, day_data in week1_daily.items():
            if isinstance(day_data, dict):
                canonical = _DAY_ALIASES.get(day_name.lower(), day_name.lower())
                day_data["is_fasting"] = canonical in fasting_set
        allergies = diet_prefs.get("food_allergies") or []
        intolerances = diet_prefs.get("food_intolerances") or []
        week1_daily = flag_allergens(week1_daily, allergies, intolerances)
        if weeks:
            weeks[0]["daily_plan"] = week1_daily

        weekly_plan = week1_daily  # backward-compat alias

        result = {
            "plan_id": f"diet_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_method": "llm_primary",
            "enriched": True,
            "enrichment_model": llm_client.provider,
            "user_summary": {
                "dominant_dosha": dominant_dosha,
                "agni_type": agni_type,
                "diet_goal": diet_prefs.get("diet_goal", "general_wellness"),
                "dietary_type": diet_prefs.get("dietary_type", "vegetarian"),
                "gut_issue": diet_prefs.get("gut_health_issue", "healthy"),
                "intermittent_fasting": diet_prefs.get("intermittent_fasting", "no"),
                "water_intake": diet_prefs.get("water_intake"),
                "active_condition_protocols": list(set(norm_conds)),
                "current_season": (user_profile.get("current_season") or "").lower() or None,
            },
            "plan_title": data.get("plan_title", "Personalised Ayurvedic Diet Plan"),
            "plan_description": data.get("plan_description", ""),
            "pathya_apathya": data.get("pathya_apathya", {}),
            "weekly_plan": weekly_plan,
            "diet_weeks": weeks,
            "condition_coaching": data.get("condition_coaching", ""),
            "hydration_guidance": data.get("hydration_guidance", ""),
            "fasting_guidance": data.get("fasting_guidance", ""),
            "seasonal_note": data.get("seasonal_note", ""),
            "ahar_vidhi": data.get("ahar_vidhi", ""),
            "motivational_note": data.get("motivational_note", ""),
            # Deterministic Ayurvedic blocks — same as rule engine, no LLM call needed
            "meal_timing": MEAL_TIMING.get(dominant_dosha, MEAL_TIMING.get("vata", {})),
            "spice_guide": DOSHA_SPICES.get(dominant_dosha, DOSHA_SPICES.get("vata", [])),
            "ayurvedic_tips": AYUR_TIPS.get(dominant_dosha, ""),
            "disclaimer": (
                "This plan is generated by an AI Vaidya and is for wellness and educational purposes. "
                "Classical text references are approximate and should be verified. "
                "Consult a qualified Ayurvedic practitioner before beginning any therapeutic diet, "
                "especially with existing medical conditions."
            ),
        }

        # Deterministic Ahara safety layer (Viruddha + allergens, all 4 weeks)
        from services.ahara_safety import apply_ahara_safety
        result = apply_ahara_safety(result, allergies, intolerances)

        return result

    except Exception as e:
        logger.error(f"LLM diet generation failed: {e}")
        return None
