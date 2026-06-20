import json
from ai.llm_client import llm_client
from core.logger import logger

_SYSTEM_PROMPT = """
You are a senior Vaidya (Ayurvedic physician, MD Ayurveda). You are enriching a clinically generated Panchakarma plan with precise, personalised coaching grounded in classical texts (Charaka Samhita, Ashtanga Hridayam).

You will receive a structured plan summary. Your job is to add daily guidance, explain the WHY behind each therapy in classical terms, and coach the patient through the emotional and physical arc of the detox.

Respond ONLY with valid JSON. No preamble, no markdown fences.
"""

_USER_PROMPT = """
Given the Panchakarma plan and user context below, produce enrichment in this EXACT JSON schema:

{{
  "plan_title": "Personalised [setting] Panchakarma Protocol — [pradhana_karma_name] for [dosha] Vikriti",
  "plan_description": "3–4 sentences: explain what this plan does clinically, why THIS Pradhana Karma was chosen for THIS Vikriti, and what the patient can expect physically and emotionally.",
  "shodhana_rationale": "1–2 sentences: why Shodhana (or Shamana) was chosen, in classical terms (Bala, Agni, Ama, Ritu, Kriya Kala).",
  "ritu_guidance": "1 sentence on how the current season ({ritu_name}) affects this plan.",
  "purvakarma_coaching": {{
    "why": "Why Snehana + Swedana must precede Pradhana Karma — in 1 sentence",
    "daily_tip": "What the patient will feel during Snehana days and how to interpret it",
    "oil_rationale": "Why THIS specific oil was chosen for Abhyanga (reference the Virya, Rasa, Dhatu it nourishes)"
  }},
  "daily_guidance": {{
    "Day 1": "Precise instruction for today — therapies, timing, what to eat, what to feel",
    "Day 2": "...",
    "Day 3": "..."
  }},
  "pradhana_karma_coaching": {{
    "what_to_expect": "Physical and emotional experiences during Pradhana Karma days",
    "samyak_yoga_signs": "How the patient will know the therapy worked adequately",
    "atiyoga_warning": "Signs of over-treatment and what to do immediately",
    "emotional_release": "What emotional patterns may surface (dosha-specific) and how to process them"
  }},
  "samsarjana_coaching": "2–3 sentences: why Samsarjana Krama is as important as the Shodhana itself, and what happens if skipped",
  "aushadha_guidance": "Explain each Aushadha (oil/medicine) recommended — what it does, when to take it, classical reference if known",
  "dietary_rules": "Detailed Pathya (do's) and Apathya (don'ts) for the entire duration, with classical reasoning",
  "rasayana_plan": "Post-PK Rasayana: specific herb, dose, timing, duration, and why it is ideal post-Shodhana",
  "motivational_note": "1 personalised sentence addressing their specific Vikriti, goal, and pradhana karma",
  "rare_disease_assessment": null
}}

{rare_disease_block}

PLAN CONTEXT:
{plan_json}
"""

_RARE_DISEASE_BLOCK = """
IMPORTANT — RARE/UNMAPPED CONDITIONS DETECTED: {unmapped_list}

These conditions are not in the classical Ayurvedic disease database. As a senior Vaidya, use your knowledge of:
1. Modern pathophysiology mapped to Ayurvedic Srotas and Dhatu
2. Classical texts (CS Nidana Sthana, Ashtanga Hridayam) for the closest analogous Vikara

For each unmapped condition, add to "rare_disease_assessment" (replace null above):
{{
  "<condition_name>": {{
    "nidana_samprapti": "Suspected Dosha/Dhatu/Srotas involvement in 1 sentence",
    "classical_analogue": "Closest classical disease name if exists (e.g. Wilson's → Yakrit Vikara, copper → Tamra Dhatu Dushti)",
    "therapy_suitability": "Is the selected {pradhana_karma} appropriate? Yes/Modified/Contraindicated — explain why",
    "suggested_aushadha": "Specific herbs/formulations if classically indicated",
    "pathya": "Key dietary/lifestyle do's for this condition during PK",
    "vaidya_note": "What a supervising Vaidya must monitor specifically for this condition"
  }}
}}
"""


async def enrich_panchakarma_plan(raw_plan: dict, user_profile: dict, pk_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        cd = raw_plan.get("clinical_decisions", {})
        pradhana = cd.get("pradhana_karma_selected", {})
        ritu_ctx = cd.get("ritu_context", {})
        eligibility = cd.get("shodhana_or_shamana", {})
        aushadha = raw_plan.get("aushadha", {})
        snehana = raw_plan.get("snehana_protocol", {})
        samsarjana = raw_plan.get("samsarjana_krama", [])

        # Build compact summary for LLM — include all clinically relevant data
        user_summary_from_engine = raw_plan.get("user_summary", {})
        plan_summary = {
            "user": {
                "name":              user_profile.get("name", "the patient"),
                "age":               user_profile.get("age"),
                "gender":            user_profile.get("gender"),
                "vikriti_dominant":  cd.get("vikriti_dominant"),
                "vikriti_secondary": cd.get("vikriti_secondary"),
                "prakriti":          user_profile.get("dominant_dosha"),
                "ama_level":         user_summary_from_engine.get("ama_indicator") or user_profile.get("ama_indicator", "none"),
                "agni_type":         user_summary_from_engine.get("agni_type") or user_profile.get("agni_type", "sama"),
                "agni_name":         user_summary_from_engine.get("agni_name", "Sama Agni"),
                "bala":              user_summary_from_engine.get("bala", "madhyama"),
                "bala_note":         user_summary_from_engine.get("bala_note", "Madhyama Bala"),
                "ojas_level":        user_summary_from_engine.get("ojas_level") or user_profile.get("ojas_level", "medium"),
                "koshtha":           user_summary_from_engine.get("koshtha") or user_profile.get("koshtha", "sama"),
                "medical_history":   (user_profile.get("medical_history") or [])[:5],
                "goal":              pk_prefs.get("panchakarma_goal"),
                "setting":           pk_prefs.get("setting"),
                "experience":        pk_prefs.get("detox_experience"),
                "duration_days":     pk_prefs.get("available_time_days"),
                "diet_adherence":    pk_prefs.get("diet_adherence_ability"),
            },
            "clinical_decisions": {
                "shodhana_or_shamana": eligibility.get("type"),
                "shodhana_reasons":    eligibility.get("reasons", []),
                "bala":                eligibility.get("bala", "madhyama"),
                "ama_correction_needed": eligibility.get("ama_correction_needed", False),
                "ama_correction_herbs":  eligibility.get("ama_correction_herbs", []),
                "pradhana_karma":      pradhana.get("primary"),
                "pradhana_reason":     pradhana.get("reason"),
                "ritu":                ritu_ctx.get("ritu"),
                "ritu_name":           ritu_ctx.get("ritu_name"),
                "ritu_primary_shodhana": ritu_ctx.get("primary_shodhana"),
                "ritu_warning":        cd.get("ritu_warning"),
                "basti_subtype":       cd.get("basti_subtype"),
            },
            "phase_breakdown":    raw_plan.get("phase_breakdown", {}),
            "snehana_protocol": {
                "internal_ghrita":  snehana.get("internal_ghrita", {}).get("name"),
                "ghrita_rationale": snehana.get("internal_ghrita", {}).get("use"),
                "abhyanga_oil":     snehana.get("abhyanga_oil", {}).get("primary") if isinstance(snehana.get("abhyanga_oil"), dict) else snehana.get("abhyanga_oil"),
                "dose_schedule":    snehana.get("dose_schedule", []),
                "signs_adequate":   snehana.get("signs_adequate", []),
            },
            "aushadha": {
                k: (v.get("name") if isinstance(v, dict) else v)
                for k, v in aushadha.items()
                if v
            },
            "samsarjana_krama_stages": [
                {"stage": s.get("stage"), "food": s.get("food"), "recipe": s.get("recipe")}
                for s in (samsarjana or [])
            ][:7],
            "daily_schedule": [
                {
                    "day": f"Day {d.get('day')}",
                    "phase": d.get("phase"),
                    "therapies": [t.get("name") for t in d.get("therapies", [])],
                }
                for d in raw_plan.get("daily_schedule", [])
            ],
            "rasayana": aushadha.get("rasayana", {}),
        }

        unmapped = cd.get("unmapped_conditions", [])
        rare_block = ""
        if unmapped:
            rare_block = _RARE_DISEASE_BLOCK.format(
                unmapped_list=", ".join(unmapped),
                pradhana_karma=pradhana.get("primary", "selected therapy"),
            )

        prompt = _USER_PROMPT.format(
            ritu_name=ritu_ctx.get("ritu_name", ritu_ctx.get("ritu", "current season")),
            rare_disease_block=rare_block,
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
        if not isinstance(enrichment, dict):
            raise ValueError("LLM returned non-dict response")
        # Minimum schema check — these are the load-bearing fields
        _required = {"plan_title", "plan_description", "shodhana_rationale"}
        missing = _required - enrichment.keys()
        if missing:
            raise ValueError(f"LLM enrichment missing required fields: {missing}")

        # Merge enrichment into plan
        for key in (
            "plan_title", "plan_description", "shodhana_rationale", "ritu_guidance",
            "purvakarma_coaching", "daily_guidance", "pradhana_karma_coaching",
            "samsarjana_coaching", "aushadha_guidance", "dietary_rules",
            "rasayana_plan", "motivational_note", "rare_disease_assessment",
        ):
            if key in enrichment:
                raw_plan[key] = enrichment[key]

        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        logger.info(f"Panchakarma plan enriched via {llm_client.provider}")

    except Exception as e:
        logger.error(f"Panchakarma enrichment failed: {e}")

    return raw_plan
