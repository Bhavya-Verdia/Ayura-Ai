"""
LLM-primary diet plan generator.

The rule engine (diet_plan_engine.py) builds a structured Ayurvedic brief from the
user's profile. This module sends that brief to the LLM and receives a complete 4-week
plan with real Indian meal names, Pathya-Apathya, and classical text references.

Knowledge constants, brief builder, and allergen scanner live in diet_brief_builder.py.
The rule engine is retained as a fallback if the LLM call fails (see routes/plans.py).
"""
from datetime import datetime, timezone

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger
from services.diet_brief_builder import (
    build_brief,
    diet_allergies,
    diet_conditions,
    fasting_withheld_reason,
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
5a. Every meal is vegetarian or vegan. No egg, fish, poultry or meat in any meal, \
   drink, Pathya list or line of guidance, whatever the patient's stated type. The \
   food library this plan is screened against holds no animal food, so such a meal \
   would be served without being checked against the patient's diseases at all.
6. Use the patient's Agni type to determine meal heaviness and frequency.
7. High Ama = all meals must be Deepaniya + Pachana; no heavy, sour, or fermented foods.
8. Each day should have a therapeutic theme (e.g., "Ama Pachana", "Agni Deepana", "Ojas Building").
9. Include a special Ayurvedic drink (Kashaya, Kwatha, herbal milk, or medicinal water) \
   for each day with timing and rationale.
10. Meals should reflect genuine Indian culinary tradition — realistic, preparable at home.
11. Follow the THERAPEUTIC PROGRESSION given in the patient brief exactly, and \
    return its phase names verbatim. It is chosen from this patient's Ama, Bala, Ojas \
    and build, and it is not the same for every patient: Langhana and Brimhana are \
    opposite lines of treatment and giving the wrong one is a clinical error, not a \
    stylistic one. Where the brief says a phase is deliberately absent, do not \
    reintroduce it under another name. \
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
      "phase": "<<PHASE_1>>",
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
      "phase": "<<PHASE_2>>",
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
      "phase": "<<PHASE_3>>",
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
      "phase": "<<PHASE_4>>",
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


def _frame_fields(frame: dict) -> dict:
    """Meal times, the two daily drinks, spices and tips — built from the patient's
    screened food list (`diet_day_frame`), on every path that writes a plan."""
    return {"meal_timing": frame["meal_timing"], "daily_rituals": frame["rituals"],
            "spice_guide": frame["spice_guide"], "ayurvedic_tips": frame["ayurvedic_tips"],
            "withheld_guidance": frame["withheld_guidance"]}


def _clinical(user_profile: dict, conditions: list[str]) -> dict:
    """Medicine-food interactions and condition notes, with sources — the same on
    both generation paths."""
    from services.diet_clinical_notes import clinical_notes, medication_matches
    interactions, unmatched = medication_matches(user_profile)
    return {"medication_interactions": interactions,
            "medications_not_checked": unmatched,
            "clinical_notes": clinical_notes(user_profile, conditions)}


async def _with_classical_context(brief: str, user_profile: dict, diet_prefs: dict) -> str:
    """The brief with classical passages from the knowledge base appended."""
    # RAG: pull classical text passages relevant to this patient's profile.
    #
    # Supplementary grounding, in its own try. These five calls used to sit
    # directly under the outer `except`, which returns None and sends the caller
    # to the rule engine — so a ChromaDB restart did not cost the plan its
    # classical citations, it cost the plan. Every diet generation during the
    # outage silently lost the LLM path entirely: the therapeutic arc, the
    # per-meal energy budget, the condition coaching, all of it, with nothing on
    # screen to say why.
    #
    # An outage degrades, it does not withhold — the same rule the remedies
    # triage follows for the same retrieval layer.
    dominant_dosha_q = (user_profile.get("dominant_dosha") or "vata").lower()
    agni_type_q = (user_profile.get("agni_type") or "sama").lower()
    conditions_q = diet_conditions(user_profile, diet_prefs)
    season = (user_profile.get("current_season") or "").lower()
    rag_context_parts: list[str] = []
    try:
        # Query 1: dosha + agni general diet guidance
        general_query = f"{dominant_dosha_q} dosha diet Ahara Pathya Apathya {agni_type_q} Agni Ayurvedic food"
        general_docs = await rag_pipeline.query(general_query, "nutrition", n_results=5, dosha_filter=dominant_dosha_q)
        if general_docs:
            rag_context_parts.append(rag_pipeline.format_context(general_docs, max_chars=1200))

        # Query 2: condition-specific diet — retrieve for EACH condition (capped),
        # not just the first, so multi-condition patients get classical grounding
        # for every diagnosis rather than only conditions_q[0].
        for _cond in conditions_q[:3]:
            cond_query = f"{_cond} Pathya Apathya diet Ayurvedic classical"
            cond_docs = await rag_pipeline.query(cond_query, "nutrition", n_results=3)
            if cond_docs:
                rag_context_parts.append(rag_pipeline.format_context(cond_docs, max_chars=600))

        # Query 3: seasonal diet
        if season:
            season_docs = await rag_pipeline.query(f"{season} Ritucharya diet seasonal Ayurveda", "nutrition", n_results=3)
            if season_docs:
                rag_context_parts.append(rag_pipeline.format_context(season_docs, max_chars=600))
    except Exception as _rag_err:
        # Partial context is kept: a condition query that succeeded before the
        # failure is still grounding for that condition.
        logger.warning(
            f"diet RAG retrieval degraded ({_rag_err}); generating with "
            f"{len(rag_context_parts)} of the usual context blocks"
        )

    rag_context = "\n\n".join(rag_context_parts) if rag_context_parts else ""

    # Inject RAG context into brief if retrieved
    if rag_context:
        brief = brief + f"\n\nCLASSICAL KNOWLEDGE BASE (cite these references where relevant):\n{rag_context}"

    return brief


async def generate_diet_plan_llm(
    user_profile: dict,
    diet_prefs: dict,
) -> dict | None:
    """
    Returns a complete diet plan dict or None on failure (caller falls back to rule engine).
    """
    try:
        brief = build_brief(user_profile, diet_prefs)

        brief = await _with_classical_context(brief, user_profile, diet_prefs)

        # The four-week progression. It used to be four literals in the prompt, the
        # same for every patient the app has ever had — so a Kapha-dominant obese
        # diabetic got a Brimhana week (Charaka Sutrasthana 23 names exactly that
        # group as the diseases of over-nourishment) and a depleted underweight
        # patient got a clearing week they had no Bala for.
        from services.diet_plan_arc import arc_prompt_block, choose_arc
        arc = choose_arc(user_profile, diet_prefs)
        brief = brief + "\n\n" + arc_prompt_block(arc)

        # Rare and uncurated conditions are classified BEFORE generation now, so their
        # Apathya screens the food list the plan is composed from rather than only
        # flagging the finished meals.
        from services.ahara_safety import (
            apply_advisory_safety, apply_ahara_safety, apply_condition_food_safety,
            apply_dietary_type_safety, apply_script_guard, classify_condition_apathya_llm,
        )
        from services.diet_brief_builder import uncurated_conditions
        from services.diet_energy import energy_target
        from services.diet_week_generator import generate_week_by_week
        _conds = diet_conditions(user_profile, diet_prefs)
        _extra_apathya = await classify_condition_apathya_llm(uncurated_conditions(_conds))
        energy = energy_target(user_profile, diet_prefs)

        body = await generate_week_by_week(user_profile, diet_prefs, brief, arc, energy,
                                           _extra_apathya)
        weeks = body["diet_weeks"]
        data = body["overview"] or {}

        dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
        agni_type = (user_profile.get("agni_type") or "sama").lower()
        user_id = str(user_profile.get("id") or user_profile.get("_id") or "anon")
        allergies = diet_allergies(user_profile, diet_prefs)
        intolerances = diet_prefs.get("food_intolerances") or []

        result = {
            "plan_id": f"diet_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_method": "llm_primary",
            "nutrition_method": "computed_from_components",
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
                "active_condition_protocols": list(set(_conds)),
                "current_season": (user_profile.get("current_season") or "").lower() or None,
            },
            "plan_title": data.get("plan_title", "Personalised Ayurvedic Diet Plan"),
            "plan_description": data.get("plan_description", ""),
            "pathya_apathya": data.get("pathya_apathya", {}),
            "therapeutic_arc": arc,
            "weekly_plan": weeks[0]["daily_plan"],
            "diet_weeks": weeks,
            "condition_coaching": data.get("condition_coaching", ""),
            "hydration_guidance": data.get("hydration_guidance", ""),
            "fasting_guidance": data.get("fasting_guidance", ""),
            "seasonal_note": data.get("seasonal_note", ""),
            "ahar_vidhi": data.get("ahar_vidhi", ""),
            "motivational_note": data.get("motivational_note", ""),
            **_frame_fields(body["frame"]),
            "energy_prescription": energy,
            "nutrient_targets": energy["nutrient_targets"],
            "energy_reconciliation": body["energy_reconciliation"],
            "composition_report": body["composition_report"],
            "fasting_notice": fasting_withheld_reason(user_profile, diet_prefs),
            **_clinical(user_profile, _conds),
            "disclaimer": (
                "This plan is generated by an AI Vaidya and is for wellness and educational purposes. "
                "Nutrition is calculated from the foods and grams in each meal using published "
                "composition data; prepared dishes marked as estimates are approximate. "
                "Consult a qualified practitioner or dietitian before beginning any therapeutic diet, "
                "especially with existing medical conditions."
            ),
        }

        # The same deterministic layers as before. Composition from the screened list
        # and the repair pass mean they should find nothing; they still run, so the
        # plan reports what was checked rather than assuming it.
        result = apply_script_guard(result)
        result = apply_ahara_safety(result, allergies, intolerances)
        result = apply_dietary_type_safety(result, diet_prefs.get("dietary_type"))
        result = apply_condition_food_safety(
            result, _conds, extra_terms=_extra_apathya,
            pregnant=bool(user_profile.get("pregnancy_or_nursing")),
        )
        result = apply_advisory_safety(
            result, _conds, allergies, intolerances, extra_terms=_extra_apathya,
            pregnant=bool(user_profile.get("pregnancy_or_nursing")),
        )

        return result

    except Exception as e:
        logger.error(f"LLM diet generation failed: {e}")
        return None


async def build_diet_plan(
    user_profile: dict,
    diet_prefs: dict,
    diet_foods: list[dict] | None = None,
) -> dict:
    """The whole diet path: LLM primary, rule engine fallback, same layers on both.

    There were two copies of this sequence — one in `routes/plans.py` for the
    per-feature endpoint and one in `routes/plan_runner.py` for the holistic worker —
    and they had drifted. The holistic fallback ran only `apply_ahara_safety`, so a
    plan produced there skipped the dietary-type check and the condition-contraindicated
    food floor entirely: which endpoint the user came through decided how much of the
    safety model applied to them. One function so that cannot happen again.
    """
    plan = await generate_diet_plan_llm(user_profile, diet_prefs)
    if plan is not None:
        return plan

    logger.warning("LLM diet generation failed; falling back to the rule engine")
    from services.ahara_safety import (
        apply_advisory_safety, apply_ahara_safety, apply_condition_food_safety,
        apply_dietary_type_safety, apply_script_guard, classify_condition_apathya_llm,
    )
    from services.diet_brief_builder import uncurated_conditions
    from services.diet_energy import energy_target
    from services.diet_plan_engine import generate_diet_plan
    from services.diet_plan_enricher import enrich_diet_plan
    # Rare conditions are classified FIRST, so their Apathya screens the pool this
    # engine composes from. Asked afterwards, the classifier's answer (which varies
    # by call) flagged foods the screen had let through — 15 "white rice" alerts on
    # an osteoporosis plan.
    conds = diet_conditions(user_profile, diet_prefs)
    extra_apathya = await classify_condition_apathya_llm(uncurated_conditions(conds))
    raw = generate_diet_plan(user_profile, diet_prefs, diet_foods, extra_terms=extra_apathya)
    plan = await enrich_diet_plan(raw, user_profile, diet_prefs)
    # Free-text meal ideas for week 1, rendered by no screen and read by no scan;
    # the meals below are named from what they are made of.
    plan.pop("daily_meal_ideas", None)
    # The engine's food lists become the same component meals the primary path
    # writes, and are brought to the same targets by the same solver. Its days
    # missed the protein floor on 26 of 28 before this.
    from services.diet_day_frame import day_frame
    from services.diet_week_generator import engine_plan_to_weeks
    energy = energy_target(user_profile, diet_prefs)
    from services.diet_allowed_foods import allowed_foods
    screen = allowed_foods(user_profile, diet_prefs, extra_terms=extra_apathya)
    allowed_ids = {f["id"] for f in screen["allowed"]}
    frame = day_frame(user_profile, diet_prefs, allowed_ids, energy, screen["excluded"])
    body = engine_plan_to_weeks(plan, energy, allowed_ids, rituals=frame["rituals"])
    plan.pop("four_week_plan", None)
    plan.update({
        "generation_method": "rule_engine",
        "nutrition_method": "computed_from_components",
        "diet_weeks": body["diet_weeks"],
        "weekly_plan": body["diet_weeks"][0]["daily_plan"] if body["diet_weeks"] else {},
        "energy_prescription": energy,
        "nutrient_targets": energy["nutrient_targets"],
        "energy_reconciliation": body["energy_reconciliation"],
        "fasting_notice": fasting_withheld_reason(user_profile, diet_prefs),
        **_frame_fields(frame),
        **_clinical(user_profile, conds),
    })
    plan = apply_script_guard(plan)
    plan = apply_ahara_safety(
        plan, diet_allergies(user_profile, diet_prefs),
        diet_prefs.get("food_intolerances") or [])
    plan = apply_dietary_type_safety(plan, diet_prefs.get("dietary_type"))
    plan = apply_condition_food_safety(
        plan, conds, extra_terms=extra_apathya,
        pregnant=bool(user_profile.get("pregnancy_or_nursing")))
    plan = apply_advisory_safety(
        plan, conds, diet_allergies(user_profile, diet_prefs),
        diet_prefs.get("food_intolerances") or [], extra_terms=extra_apathya,
        pregnant=bool(user_profile.get("pregnancy_or_nursing")))
    return plan


# ── Check-in rebuild: the weeks still to come ────────────────────────────────

# Safety outputs that list meals by week. A rebuild scans only the weeks it wrote;
# the kept weeks keep the findings they were shipped with.
_WEEK_ALERT_KEYS = ("safety_alerts", "dietary_type_alerts", "condition_safety_alerts",
                    "unscannable_alerts")
_SAFE_FLAGS = {"safety_alerts": "allergen_safe", "dietary_type_alerts": "dietary_type_safe",
               "condition_safety_alerts": "condition_food_safe"}


def _alert_week(alert: dict) -> int | None:
    try:
        return int(str(alert.get("week", "")).split()[-1])
    except (ValueError, IndexError):
        return None


async def rebuild_diet_weeks(old_plan: dict, user_profile: dict, diet_prefs: dict,
                             from_week: int) -> dict:
    """The plan with weeks `from_week`-4 written again after a weekly check-in.

    `user_profile["diet_log"]` carries the check-in (trouble foods, digestion,
    hunger), so the food list, the condition floors and the energy target already
    reflect it. Weeks before `from_week` are kept exactly, the therapeutic arc is
    kept so the phases continue, and the same safety layers run on what was written.
    Raises if the weeks cannot be written; the stored plan is then left as it was."""
    import copy

    from services.ahara_safety import (
        apply_advisory_safety, apply_ahara_safety, apply_condition_food_safety,
        apply_dietary_type_safety, apply_script_guard, classify_condition_apathya_llm,
    )
    from services.diet_brief_builder import uncurated_conditions
    from services.diet_energy import energy_target
    from services.diet_plan_arc import arc_prompt_block, choose_arc
    from services.diet_week_generator import generate_week_by_week

    if not 2 <= from_week <= 4:
        raise ValueError("only weeks 2-4 can be rebuilt")
    conds = diet_conditions(user_profile, diet_prefs)
    extra = await classify_condition_apathya_llm(uncurated_conditions(conds))
    energy = energy_target(user_profile, diet_prefs)
    arc = old_plan.get("therapeutic_arc") or choose_arc(user_profile, diet_prefs)
    brief = build_brief(user_profile, diet_prefs)
    brief = await _with_classical_context(brief, user_profile, diet_prefs)
    brief = brief + "\n\n" + arc_prompt_block(arc)

    kept = [copy.deepcopy(w) for w in old_plan.get("diet_weeks") or []
            if isinstance(w, dict) and (w.get("week_number") or 0) < from_week]
    body = await generate_week_by_week(user_profile, diet_prefs, brief, arc, energy, extra,
                                       kept_weeks=kept)

    plan = copy.deepcopy(old_plan)
    summary = dict(plan.get("user_summary") or {})
    summary["active_condition_protocols"] = list(dict.fromkeys(conds))
    plan.update({
        "diet_weeks": body["diet_weeks"],
        "weekly_plan": body["diet_weeks"][0]["daily_plan"],
        "user_summary": summary,
        "energy_prescription": energy,
        "nutrient_targets": energy["nutrient_targets"],
        "energy_reconciliation": body["energy_reconciliation"],
        "composition_report": body["composition_report"],
        "fasting_notice": fasting_withheld_reason(user_profile, diet_prefs),
        **_frame_fields(body["frame"]),
        **_clinical(user_profile, conds),
    })
    plan.pop("translations", None)

    allergies = diet_allergies(user_profile, diet_prefs)
    intolerances = diet_prefs.get("food_intolerances") or []
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))
    # Scanned: the new weeks and all the prose. Not scanned: the kept weeks, which
    # were checked when they were written and have since been eaten.
    checked = {**plan, "diet_weeks": [w for w in plan["diet_weeks"]
                                      if w["week_number"] >= from_week]}
    checked.pop("weekly_plan", None)
    checked = apply_script_guard(checked)
    checked = apply_ahara_safety(checked, allergies, intolerances)
    checked = apply_dietary_type_safety(checked, diet_prefs.get("dietary_type"))
    checked = apply_condition_food_safety(checked, conds, extra_terms=extra, pregnant=pregnant)
    checked = apply_advisory_safety(checked, conds, allergies, intolerances,
                                    extra_terms=extra, pregnant=pregnant)
    checked["diet_weeks"] = plan["diet_weeks"]
    checked["weekly_plan"] = plan["weekly_plan"]
    for key in _WEEK_ALERT_KEYS:
        earlier = [a for a in old_plan.get(key) or []
                   if isinstance(a, dict) and (_alert_week(a) or 0) < from_week]
        checked[key] = earlier + list(checked.get(key) or [])
        if key in _SAFE_FLAGS:
            checked[_SAFE_FLAGS[key]] = not checked[key]
    seen = {v.get("combination"): v for v in old_plan.get("viruddha_ahara_detected") or []
            if isinstance(v, dict)}
    for v in checked.get("viruddha_ahara_detected") or []:
        seen.setdefault(v.get("combination"), v)
    checked["viruddha_ahara_detected"] = list(seen.values())
    checked["generated_at"] = old_plan.get("generated_at")
    return checked
