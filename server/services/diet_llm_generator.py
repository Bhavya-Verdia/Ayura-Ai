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
    build_brief,
    diet_allergies,
    diet_conditions,
    fasting_days_for,
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


async def generate_diet_plan_llm(
    user_profile: dict,
    diet_prefs: dict,
) -> dict | None:
    """
    Returns a complete diet plan dict or None on failure (caller falls back to rule engine).
    """
    try:
        brief = build_brief(user_profile, diet_prefs)

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

        # The four-week progression. It used to be four literals in the prompt, the
        # same for every patient the app has ever had — so a Kapha-dominant obese
        # diabetic got a Brimhana week (Charaka Sutrasthana 23 names exactly that
        # group as the diseases of over-nourishment) and a depleted underweight
        # patient got a clearing week they had no Bala for.
        from services.diet_plan_arc import arc_prompt_block, choose_arc
        arc = choose_arc(user_profile, diet_prefs)
        brief = brief + "\n\n" + arc_prompt_block(arc)

        prompt = USER_PROMPT_TEMPLATE.replace("{brief}", brief)
        for _week in arc["weeks"]:
            prompt = prompt.replace(
                f"<<PHASE_{_week['week_number']}>>", _week["phase"])

        # A full 4-week plan (Week 1 detailed + Weeks 2-4 compact) exceeds the
        # 4096-token default — that truncated the JSON mid-string, so json.loads
        # always failed and diet silently fell back to the rule engine. Use the
        # model's max output budget so the "LLM-primary" path actually runs.
        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
            max_tokens=16384,
        )

        data = json.loads(response_text)
        if "error" in data:
            raise ValueError(f"LLM returned error: {data['error']}")
        if "weeks" not in data or not isinstance(data["weeks"], list):
            raise ValueError("LLM response missing 'weeks' array")
        # A "4-week plan" with fewer than four weeks was shipping to the UI, which
        # renders four week tabs. The length was never checked — only that the key
        # existed — and the model drops a week now and then. Each missing week is
        # also a missing therapeutic phase, so this is a failed generation rather
        # than a short one: the caller falls back to the rule engine, which always
        # produces four.
        weeks_in = [w for w in data["weeks"] if isinstance(w, dict)]
        numbers = sorted(w.get("week_number") for w in weeks_in)
        if numbers != [1, 2, 3, 4]:
            raise ValueError(f"LLM returned weeks {numbers}, expected [1, 2, 3, 4]")
        data["weeks"] = sorted(weeks_in, key=lambda w: w["week_number"])

        dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
        agni_type = (user_profile.get("agni_type") or "sama").lower()
        norm_conds = diet_conditions(user_profile, diet_prefs)

        user_id = str(user_profile.get("id") or user_profile.get("_id") or "anon")

        _DAY_ALIASES = {
            "monday": "monday", "tuesday": "tuesday", "wednesday": "wednesday",
            "thursday": "thursday", "friday": "friday", "saturday": "saturday", "sunday": "sunday",
            "mon": "monday", "tue": "tuesday", "wed": "wednesday",
            "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday",
        }

        # Tag fasting days and run allergen check on week 1 (full detail)
        fasting_days_raw = fasting_days_for(user_profile, diet_prefs)
        fasting_set = {d.lower() for d in fasting_days_raw}
        weeks = data["weeks"]
        week1_daily = weeks[0].get("daily_plan", {}) if weeks else {}
        for day_name, day_data in week1_daily.items():
            if isinstance(day_data, dict):
                canonical = _DAY_ALIASES.get(day_name.lower(), day_name.lower())
                day_data["is_fasting"] = canonical in fasting_set
        # Both places the app stores an allergy. It read the diet form alone, so an
        # allergy declared in onboarding's health step was honoured by the remedies
        # engine and by nothing in the feature that is entirely about food.
        allergies = diet_allergies(user_profile, diet_prefs)
        intolerances = diet_prefs.get("food_intolerances") or []
        week1_daily = flag_allergens(week1_daily, allergies, intolerances)
        if weeks:
            weeks[0]["daily_plan"] = week1_daily

        # The phase labels are the app's prescription, so they come from the arc and
        # not from whatever the model echoed back. A disagreement is logged rather
        # than shown: the arc names the sequence, and a week displayed under a phase
        # the patient was not prescribed is the defect this whole module addresses.
        for _week, _prescribed in zip(weeks, arc["weeks"]):
            _returned = _week.get("phase")
            if _returned and _returned != _prescribed["phase"]:
                logger.info(
                    f"diet arc: model returned phase {_returned!r} for week "
                    f"{_prescribed['week_number']}, prescribed {_prescribed['phase']!r}"
                )
            _week["phase"] = _prescribed["phase"]

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
            "therapeutic_arc": arc,
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

        # Energy reconciliation. The brief now carries a per-meal kcal budget, but a
        # stated target and a delivered plan were never compared: measured plans came
        # back at 585-720 kcal against a stated 1200, and 1240-1410 against a stated
        # 2400 for an underweight patient. Portions are scaled toward the budget and
        # the residual is reported rather than left on screen as a day total.
        from services.diet_energy import energy_target
        from services.diet_portion_reconciler import reconcile_plan_energy
        result = reconcile_plan_energy(result, energy_target(user_profile, diet_prefs))

        # Deterministic Ahara safety layer (Viruddha + allergens, all 4 weeks)
        from services.ahara_safety import (
            apply_advisory_safety, apply_ahara_safety, apply_condition_food_safety,
            apply_dietary_type_safety, classify_condition_apathya_llm,
        )
        result = apply_ahara_safety(result, allergies, intolerances)
        # The declared dietary type, checked rather than requested. Until now the
        # only thing standing between a vegetarian and a chicken curry was a line in
        # the prompt.
        result = apply_dietary_type_safety(result, diet_prefs.get("dietary_type"))
        # Condition-contraindicated food floor — enforce each condition's Apathya
        # deterministically instead of trusting the LLM to have honoured it. Rare /
        # uncurated conditions get their Apathya classified by the LLM first, so the
        # floor covers ALL diseases, not just the hardcoded common ones.
        from services.diet_brief_builder import uncurated_conditions
        _conds = diet_conditions(user_profile, diet_prefs)
        # Only classify conditions with no curated hint — curated ones are vetted
        # and must not be overwritten by an LLM guess.
        _extra_apathya = await classify_condition_apathya_llm(uncurated_conditions(_conds))
        result = apply_condition_food_safety(
            result, _conds, extra_terms=_extra_apathya,
            pregnant=bool(user_profile.get("pregnancy_or_nursing")),
        )
        # The same floor, applied to the prose that recommends food by name. The
        # scans above read the five consumed slots; `pathya_apathya.pathya` is
        # rendered under the heading "Pathya — Recommended" and was read by nothing.
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
        apply_dietary_type_safety, classify_condition_apathya_llm,
    )
    from services.diet_brief_builder import uncurated_conditions
    from services.diet_energy import energy_target
    from services.diet_plan_engine import generate_diet_plan
    from services.diet_plan_enricher import enrich_diet_plan
    from services.diet_portion_reconciler import reconcile_plan_energy

    raw = generate_diet_plan(user_profile, diet_prefs, diet_foods)
    plan = await enrich_diet_plan(raw, user_profile, diet_prefs)
    plan = apply_ahara_safety(
        plan, diet_allergies(user_profile, diet_prefs),
        diet_prefs.get("food_intolerances") or [])
    plan = apply_dietary_type_safety(plan, diet_prefs.get("dietary_type"))
    conds = diet_conditions(user_profile, diet_prefs)
    extra_apathya = await classify_condition_apathya_llm(uncurated_conditions(conds))
    plan = apply_condition_food_safety(
        plan, conds, extra_terms=extra_apathya,
        pregnant=bool(user_profile.get("pregnancy_or_nursing")))
    plan = apply_advisory_safety(
        plan, conds, diet_allergies(user_profile, diet_prefs),
        diet_prefs.get("food_intolerances") or [], extra_terms=extra_apathya,
        pregnant=bool(user_profile.get("pregnancy_or_nursing")))
    # The engine fills category quotas with no energy target of its own — measured at
    # 580-1031 kcal against a 1490 kcal target, with 22-40 g of protein against an
    # 84 g floor.
    plan = reconcile_plan_energy(plan, energy_target(user_profile, diet_prefs))
    return plan
