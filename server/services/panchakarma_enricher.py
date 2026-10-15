import json
from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

_SYSTEM_PROMPT = """
You are a senior Vaidya (Ayurvedic physician, MD Ayurveda). You are enriching a clinically generated Panchakarma plan with precise, personalised coaching grounded in classical texts (Charaka Samhita, Ashtanga Hridayam).

You will receive a structured plan summary. Your job is to add daily guidance, explain the WHY behind each therapy in classical terms, and coach the patient through the emotional and physical arc of the detox.

CRITICAL CLASSICAL ACCURACY — never violate these in any coaching text:
- The 5 Panchakarma (Pradhana Karma) are: Vamana, Virechana, Basti (Anuvasana + Niruha), Nasya, Raktamokshana. These are the only true Panchakarma.
- Abhyanga and Swedana are Purvakarma (preparatory procedures) — NEVER call them Panchakarma.
- Shirodhara is Murdha Taila (a Bahya Chikitsa procedure) — NEVER call it Panchakarma.
- Udvartana is Lekhana Karma (Bahya Chikitsa) — NOT Panchakarma.
- Kati Basti is a regional Snehana technique (Bahya Chikitsa) — NOT Panchakarma.
- Calling Abhyanga or Shirodhara "Panchakarma" is a common commercial error — it is classically incorrect and must never appear in your coaching text.

THE DETERMINISTIC LAYER HAS THE LAST WORD:
- `declared_capabilities` records what the patient told us they can do. `samsarjana_notice` and `procurement_notice` are the engine's position on it. Where either is present, your coaching must agree with it — do not talk a patient enthusiastically through a therapeutic diet or a formulation they have just said they cannot manage, and do not soften a notice that says a phase is not optional.
- Where a notice is absent, do not invent one.
- `deferral`, when present, means the plan must NOT BE STARTED YET — the patient is reading a "Do not start yet" banner above your text. Write the plan as what to do once `resume_when` is satisfied, never as something beginning today. Do not open `daily_guidance` with "begin this morning", do not congratulate them on starting, and do not soften or omit the reason. A narrative that reads as a start instruction directly contradicts the binding notice on the same screen.
- `kriya_kala` is the classical stage of the patient's disease, derived from what they reported at check-in. Cite it in `shodhana_rationale` ONLY from this field — name the stage it gives and nothing else. When it is null the patient has staged no condition, so Kriya Kala is unknown: write the rationale from Bala, Agni, Ama and Ritu and do not mention a stage at all. Never infer a stage from the diagnosis, the duration or the plan. It is `advisory_only`: it did not decide this verdict, so do not write that the patient is eligible or ineligible because of it.
- `secondary_karma_deferred` names a Karma that is classically indicated for this Vikriti and that this plan deliberately does NOT perform. Treat it as withheld. You may say it is something to raise with a Vaidya; you must never describe it as part of the treatment, place it in the schedule, or explain how to undergo it. For Pitta this field is Raktamokshana — bloodletting — and a patient who reads your text as a prescription for it has been actively misled.

- `snehana_protocol.dose_schedule` empty on a Shodhana plan means this Karma takes NO internal oleation (Basti, Nasya and Raktamokshana are prepared with Abhyanga and Swedana alone). Never tell the patient to drink ghee or describe Snehapana in that case; `purvakarma_coaching` is about the massage and the steam.
- `allergen_review.findings` names substances in this plan the patient is allergic to. Never recommend any of them as written — not the ghee, oil, milk or honey named there — and never suggest a substitute base yourself; say the Vaidya supplies a preparation without the allergen.
- `snehana_protocol.matra` is the Snehapana peak set by the patient's Agni. Quote doses only from `dose_schedule`; never a larger figure.
- `medication_review` and `safety_warnings` name what the procedures do to the patient's own medicines. Never tell the patient to stop, skip or change the dose of a prescribed medicine — say the prescriber decides. Do not contradict a caution, and do not describe a Karma the warnings say was withdrawn.

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


# ── Deterministic gate on the narrative ───────────────────────────────────────
# The prompt asks the model to agree with the engine; nothing checked that it did.
# Every field below was merged straight into the plan the patient reads, beside a
# schedule it could contradict. This withholds a sentence — never rewrites it — when
# it prescribes something the engine withheld, and records what it withheld.

import re as _re

_KARMA_WORDS = {
    "vamana": ("vamana", "emesis", "therapeutic vomiting"),
    "virechana": ("virechana", "purgation", "purgative"),
    "basti": ("niruha", "basti", "enema"),
    "basti_matra": ("matra basti",),
    "nasya": ("nasya", "nasal drops"),
    "raktamokshana": ("raktamokshana", "bloodletting", "leech", "jalaukavacharana"),
}
# A sentence naming a withheld thing is fine when it is saying it is withheld.
_DISTANCING = _re.compile(
    r"\b(not|never|no|avoid\w*|withh[oe]ld\w*|withdrawn|instead|rather than|defer\w*|"
    r"postpone\w*|later|future|until|contraindicat\w*|barred|unsafe|replac\w*|"
    r"substitut\w*|without|allerg\w*|discuss|ask (?:the|your) vaidya|skip\w*)\b", _re.I)
_SNEHAPANA_WORDS = _re.compile(r"\b(snehapana|drink(?:ing)? (?:warm |medicated )?ghee|ghee (?:dose|ladder)|"
                               r"internal oleation)\b", _re.I)
_ML = _re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)?\s*(\d+(?:\.\d+)?)?\s*ml\b", _re.I)


def _sentences(text: str) -> list[str]:
    return [x for x in _re.split(r"(?<=[.!?])\s+", text) if x.strip()]


def gate_enrichment(enrichment: dict, raw_plan: dict) -> tuple[dict, list[dict]]:
    """Withhold narrative sentences that contradict the deterministic plan."""
    cd = raw_plan.get("clinical_decisions", {}) or {}
    pradhana = cd.get("pradhana_karma_selected") or {}
    primary = pradhana.get("primary")
    is_shamana = (cd.get("shodhana_or_shamana") or {}).get("type") == "shamana" or not primary

    withheld_karmas: dict[str, str] = {}
    if pradhana.get("original_karma") and pradhana.get("original_karma") != primary:
        withheld_karmas[pradhana["original_karma"]] = "withdrawn for safety"
    deferred = (cd.get("secondary_karma_deferred") or {}).get("karma")
    if deferred and deferred != primary:
        withheld_karmas[deferred] = "not part of this plan"
    if is_shamana:
        for k in ("vamana", "virechana", "basti", "raktamokshana"):
            withheld_karmas.setdefault(k, "no Shodhana in this plan")
    if primary == "basti_matra":
        withheld_karmas.setdefault("basti", "this course is Matra Basti only")
    patterns = {}
    for k, why in withheld_karmas.items():
        words = [w for w in _KARMA_WORDS.get(k, ()) if not (
            # "basti" also names the course being given.
            primary in ("basti", "basti_matra") and w in ("basti", "enema"))]
        if k == "basti" and primary == "basti_matra":
            words = ["niruha", "decoction enema"]
        if words:
            patterns[k] = (_re.compile(r"\b(" + "|".join(map(_re.escape, words)) + r")\b", _re.I), why)

    ladder = (raw_plan.get("snehana_protocol") or {}).get("dose_schedule") or []
    peak = max((d.get("dose_ml") or 0) for d in ladder) if ladder else 0

    allergen_terms: list[tuple[str, str]] = []
    from services.panchakarma_engine import pk_clinical
    table = pk_clinical.get("allergens") or {}
    for f in ((cd.get("allergen_review") or {}).get("findings") or []):
        for key, entry in table.items():
            if isinstance(entry, dict) and entry.get("label") == f.get("allergy"):
                allergen_terms += [(t, f["allergy"]) for t in entry["terms"] if t != "taila"]

    withheld: list[dict] = []

    def screen(text: str, field: str) -> str:
        kept = []
        for sent in _sentences(text):
            reason = None
            distanced = bool(_DISTANCING.search(sent))
            for k, (pat, why) in patterns.items():
                if pat.search(sent) and not distanced:
                    reason = f"{k.replace('_', ' ').title()} — {why}"
                    break
            if not reason and not ladder and not is_shamana and _SNEHAPANA_WORDS.search(sent) and not distanced:
                reason = "this Karma takes no Snehapana"
            if not reason and peak and _re.search(r"\b(ghee|ghrita|sneha)", sent, _re.I):
                for m in _ML.finditer(sent):
                    hi = float(m.group(2) or m.group(1))
                    if hi > peak:
                        reason = f"quotes {hi:g} ml; this plan's Snehapana peak is {peak} ml"
                        break
            if not reason and not distanced:
                for term, label in allergen_terms:
                    if _re.search(rf"\b{_re.escape(term)}\b", sent, _re.I):
                        reason = f"names {term} — declared {label.lower()} allergy"
                        break
            if reason:
                withheld.append({"field": field, "text": sent, "reason": reason})
            else:
                kept.append(sent)
        return " ".join(kept)

    def walk(v, field):
        if isinstance(v, str):
            return screen(v, field)
        if isinstance(v, list):
            return [x for x in (walk(x, field) for x in v) if x not in ("", [], {})]
        if isinstance(v, dict):
            return {k: walk(x, f"{field}.{k}") for k, x in v.items()}
        return v

    gated = {k: walk(v, k) for k, v in enrichment.items()}
    return gated, withheld


async def enrich_panchakarma_plan(raw_plan: dict, user_profile: dict, pk_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        cd = raw_plan.get("clinical_decisions", {})
        pradhana = cd.get("pradhana_karma_selected", {})
        vikriti = cd.get("vikriti_dominant") or user_profile.get("dominant_dosha") or "vata"
        pradhana_name = pradhana.get("primary", "panchakarma")

        # Fetch grounding context from panchakarma + ayurveda collections
        pk_query = f"{pradhana_name} {vikriti} panchakarma shodhana treatment protocol"
        pk_docs = await rag_pipeline.query(pk_query, "panchakarma", n_results=4)
        ayur_docs = await rag_pipeline.query(f"{vikriti} vikriti detox Ayurvedic cleansing", "ayurveda", n_results=2, dosha_filter=vikriti)
        rag_context = rag_pipeline.format_context(pk_docs + ayur_docs, max_chars=1800) or "No specific context retrieved — use classical Charaka Samhita and Ashtanga Hridayam principles."

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
                # The classically-indicated second Karma, which the plan deliberately
                # does NOT schedule. It goes in so the narrative cannot contradict the
                # binding decision — an enricher that does not know a Karma was
                # withheld is free to describe it as part of the treatment, which is
                # how a patient ends up believing bloodletting was prescribed.
                "secondary_karma_deferred": cd.get("secondary_karma_deferred"),
                # The "do not start yet" banner (acute fever, active menstruation).
                # It was rendered to the patient and withheld from the model, so the
                # narrative was free to coach them through Day 1 of a plan the screen
                # above it says not to begin.
                "deferral": cd.get("deferral"),
                # The Shatkriyakala stage of the patient's own reported conditions.
                # `shodhana_rationale` below has always demanded the narrative justify
                # the verdict "in classical terms (Bala, Agni, Ama, Ritu, Kriya Kala)"
                # — and Kriya Kala was the one term of the five never supplied, so it
                # was invented. None when the patient has staged no condition, which
                # is what the prompt rule below is about.
                "kriya_kala": eligibility.get("kriya_kala"),
                # What each procedure does to the medicines the patient takes, and
                # the Karma substitutions those medicines forced.
                "medication_review": cd.get("medication_review"),
                # Substances in this plan the patient is allergic to.
                "allergen_review":   cd.get("allergen_review"),
                "safety_warnings":   cd.get("safety_warnings", []),
            },
            "phase_breakdown":    raw_plan.get("phase_breakdown", {}),
            "snehana_protocol": {
                # None for a Basti, Nasya or Raktamokshana course: those take no
                # internal oleation, so there is no ghrita to name.
                "internal_ghrita":  (snehana.get("internal_ghrita") or {}).get("name"),
                "ghrita_rationale": (snehana.get("internal_ghrita") or {}).get("use"),
                "abhyanga_oil":     snehana.get("abhyanga_oil", {}).get("primary") if isinstance(snehana.get("abhyanga_oil"), dict) else snehana.get("abhyanga_oil"),
                "dose_schedule":    snehana.get("dose_schedule", []),
                "matra":            snehana.get("matra"),
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
            # What the patient said they can do, and what the engine did about it.
            # Without these the narrative coaches somebody enthusiastically through
            # a Peya fast they have just declined, or through sourcing formulations
            # they have just said they cannot obtain — the deterministic layer
            # states the position and the prose contradicts it in the next section.
            "declared_capabilities": {
                "diet_adherence_ability": pk_prefs.get("diet_adherence_ability"),
                "access_to_ayurvedic_herbs": pk_prefs.get("access_to_ayurvedic_herbs"),
            },
            "samsarjana_notice": raw_plan.get("samsarjana_notice"),
            "procurement_notice": raw_plan.get("procurement_notice"),
        }

        unmapped = cd.get("unmapped_conditions", [])
        rare_block = ""
        if unmapped:
            rare_block = _RARE_DISEASE_BLOCK.format(
                unmapped_list=", ".join(unmapped),
                pradhana_karma=pradhana.get("primary", "selected therapy"),
            )
            # The safety triage has already ruled on these conditions, and its ruling
            # is the one the schedule was built from. Asking for a second opinion
            # without showing the first is how you get a narrative that calls a
            # therapy contraindicated while the calendar still schedules it.
            if triage := cd.get("condition_triage"):
                rare_block += (
                    "\n\nA SAFETY TRIAGE HAS ALREADY RULED ON THESE CONDITIONS, and the plan "
                    "above was built from its ruling. Your assessment must agree with it — "
                    "explain and expand on it, never contradict or soften it:\n"
                    + json.dumps(triage, indent=2)
                )

        prompt = _USER_PROMPT.format(
            ritu_name=ritu_ctx.get("ritu_name", ritu_ctx.get("ritu", "current season")),
            rare_disease_block=rare_block,
            plan_json=json.dumps(plan_summary, indent=2),
        ) + f"\n\nCLASSICAL KNOWLEDGE BASE (ground your response in these references):\n{rag_context}"

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

        # Merge enrichment into plan — through the gate, never around it.
        enrichment, coaching_withheld = gate_enrichment(enrichment, raw_plan)
        raw_plan["coaching_withheld"] = coaching_withheld
        if coaching_withheld:
            logger.info(f"Panchakarma enrichment: {len(coaching_withheld)} sentence(s) withheld by the gate")
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
