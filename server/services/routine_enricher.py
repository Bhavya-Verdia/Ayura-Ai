"""
Routine Plan Enricher
Adds LLM-generated coaching, seasonal rationale, and dosha-specific guidance
on top of the deterministic Dinacharya schedule from routine_engine.py.

Two things were wrong with it. The snapshot it sent the model read `wake_time`,
`sleep_time`, `morning_rituals` and `meal_schedule` from the top of the plan,
where none of them live — they are in `dinacharya_protocol` and the timeline — so
the model was asked to explain "the prescribed sleep window" with no window, no
rituals and no meal times. And the narrative passed no gate: a pregnant user's
plan withholds Nasya and Triphala, and the coaching beside it was free to
recommend both.
"""
import json
import re

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

_SYSTEM_PROMPT = """
You are a senior Ayurvedic lifestyle coach (Dinacharya specialist) with deep knowledge of
Charaka Samhita Sutrasthana and Ashtanga Hridayam Sutrasthana chapters on daily routine.

You receive a structured Dinacharya schedule and user profile.
Your role is to add personalized coaching rationale that explains WHY each part of this
routine is prescribed for THIS specific person's dosha, vikriti, agni, and season.

Explain only the practices listed in the schedule. Never recommend a practice, herb or
food listed under "withheld" or "allergies", never suggest exercise harder than the
schedule's exercise limit, and never suggest fasting when fasting is withheld.

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
    "why_oil_pulling": "1 sentence: Kavala Gandusha — what it protects at this hour (empty string if Kavala Gandusha is withheld)",
    "why_abhyanga": "1 sentence: why self-massage before bathing is essential for this dosha"
  }},
  "sleep_coaching": "1-2 sentences: the Ayurvedic reasoning for the prescribed sleep window ({wake_time} to {sleep_time}), referencing Ratricharya and Brahma Muhurta if applicable.",
  {integration_field}
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

_FIELDS = (
    "plan_title", "plan_description", "dosha_coaching", "agni_coaching",
    "seasonal_rationale", "morning_ritual_rationale", "sleep_coaching",
    "integration_note", "weekly_theme", "motivational_note",
)

_SEASON_LABELS = {
    "vasanta": "Vasanta (Spring)", "grishma": "Grishma (Summer)",
    "varsha": "Varsha (Monsoon)", "sharad": "Sharad (Autumn)",
    "hemanta": "Hemanta (Early Winter)", "shishira": "Shishira (Late Winter)",
}

_HERB_WORDS = {
    "Ashwagandha Churna": ("ashwagandha",), "Brahmi Churna": ("brahmi",),
    "Triphala Churna": ("triphala",), "Trikatu Churna": ("trikatu",),
    "Chyawanprash": ("chyawanprash", "chyavanprash"),
}
_SHODHANA = ("vamana", "virechana", "basti", "nasya", "purgation", "emesis")
_HARD_EXERCISE = ("vigorous", "hiit", "high-intensity", "high intensity", "running", "sprint", "intense")


def _snapshot(raw_plan: dict) -> dict:
    """What the plan actually prescribes, read from where it lives."""
    din = raw_plan.get("dinacharya_protocol") or {}
    week = raw_plan.get("weekly_routine") or []
    day0 = (week[0] if week else {}).get("timeline") or []
    return {
        "wake_time": din.get("wake_time"),
        "sleep_time": din.get("sleep_time"),
        "sleep_hours": din.get("sleep_hours"),
        "morning_rituals": [r["name"] for r in din.get("morning_rituals") or [] if not r.get("withheld")],
        "evening_rituals": [r["name"] for r in din.get("evening_rituals") or []],
        "meal_times": {s["meal_type"]: s["time"] for s in day0 if s.get("meal_type")},
        "week": [d.get("exercise_label") for d in week],
        "season": (raw_plan.get("seasonal_ritucharya") or {}).get("season"),
    }


def _withheld_terms(raw_plan: dict, user_profile: dict) -> dict[str, str]:
    """term → why the narrative must not recommend it."""
    din = raw_plan.get("dinacharya_protocol") or {}
    terms: dict[str, str] = {}
    for r in din.get("morning_rituals") or []:
        if r.get("withheld"):
            terms[r["name"].split()[0].lower()] = f"{r['name']} is withheld from this plan"
    for w in din.get("withheld_practices") or []:
        name = str(w.get("practice") or "")
        for herb, words in _HERB_WORDS.items():
            if any(x in name.lower() for x in words):
                for x in words:
                    terms[x] = f"{herb} is withheld: {w.get('reason')}"
    for w in (raw_plan.get("seasonal_ritucharya") or {}).get("withheld") or []:
        item = str(w.get("item") or "").lower()
        for herb, words in _HERB_WORDS.items():
            if any(x in item for x in words):
                for x in words:
                    terms[x] = f"{herb} is withheld: {w.get('reason')}"
    age = int(user_profile.get("age") or 30)
    if din.get("pregnancy_notices") or age < 16 or age >= 70:
        for t in _SHODHANA:
            terms.setdefault(t, "cleansing therapies are not part of this plan for this person")
    limits = raw_plan.get("exercise_limits") or {}
    if limits.get("cap") in ("moderate", "gentle"):
        for t in _HARD_EXERCISE:
            terms[t] = "this plan keeps exercise at a pace you can talk through"
    if raw_plan.get("fasting_notice") and raw_plan.get("requested_fasting") is not None:
        for t in ("fasting", "fast day", "skip breakfast", "intermittent fasting"):
            terms[t] = "fasting is withheld for this person"
    return terms


def gate_routine_enrichment(enrichment: dict, raw_plan: dict, user_profile: dict) -> tuple[dict, list[dict]]:
    """Withhold narrative sentences that recommend what the plan withheld, a declared
    allergen, or anything in a script the checks cannot read."""
    from services.panchakarma_enricher import _DISTANCING, _sentences
    from services.remedy_engine import _allergen_entries, _contains_allergen
    from services.ahara_safety import unreadable_script

    terms = _withheld_terms(raw_plan, user_profile)
    term_re = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")",
                         re.I) if terms else None
    allergens = _allergen_entries(user_profile.get("allergies") or [])
    withheld: list[dict] = []

    def screen(text: str, field: str) -> str:
        if (script := unreadable_script(text)):
            withheld.append({"field": field, "text": text[:200],
                             "reason": f"written in {script} script, which the safety checks cannot read"})
            return ""
        kept = []
        for sent in _sentences(text):
            distanced = bool(_DISTANCING.search(sent))
            reason = None
            if term_re and not distanced and (m := term_re.search(sent)):
                reason = f"names {m.group(1)} — {terms[m.group(1).lower()]}"
            if not reason and not distanced:
                hit = next((e for e in allergens if _contains_allergen(sent, e)), None)
                if hit:
                    reason = f"names a {hit['label'].lower()} food — declared allergy"
            if reason:
                withheld.append({"field": field, "text": sent, "reason": reason})
            else:
                kept.append(sent)
        return " ".join(kept)

    def walk(value, field):
        if isinstance(value, str):
            return screen(value, field)
        if isinstance(value, dict):
            return {k: walk(v, f"{field}.{k}") for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, f"{field}[{i}]") for i, v in enumerate(value)]
        return value

    return {k: walk(v, k) for k, v in enrichment.items()}, withheld


async def enrich_routine_plan(raw_plan: dict, user_profile: dict, routine_prefs: dict) -> dict:
    """Enrich the deterministic Dinacharya plan with LLM coaching and seasonal rationale."""
    raw_plan["enriched"] = False

    try:
        summary = raw_plan.get("user_summary") or {}
        dosha = summary.get("vikriti") or user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha") or "vata"
        # The plan's own Agni — the routine form's answer when given, else the
        # assessment — not the profile's, which the plan may have overridden.
        agni_type = summary.get("agni_type") or user_profile.get("agni_type") or "sama"
        season = summary.get("current_season") or user_profile.get("current_season") or "sharad"
        season_label = _SEASON_LABELS.get(season, season.title())
        rp = routine_prefs.get("routine", {}) or {}
        has_gym = bool(rp.get("integrate_gym_plan"))
        has_yoga = bool(rp.get("integrate_yoga_plan"))

        # Retrieval has its own handler: a ChromaDB outage costs the grounding, not
        # the coaching.
        rag_context = ""
        try:
            rag_query = f"Dinacharya daily routine {dosha} dosha Ayurvedic lifestyle morning ritual"
            docs = await rag_pipeline.query(rag_query, "ayurveda", n_results=4, dosha_filter=dosha)
            rag_context = rag_pipeline.format_context(docs, max_chars=1500)
        except Exception as e:
            logger.warning("Routine enrichment retrieval failed: %s", e)
        rag_context = rag_context or "Use classical Ashtanga Hridayam Sutrasthana (Ch. 3) and Charaka Sutrasthana (Ch. 5) Dinacharya principles."

        integration_parts = [p for p, on in (("gym workout", has_gym), ("yoga practice", has_yoga)) if on]
        # The prompt used to put "Omit this field — no gym or yoga integration
        # requested." inside the schema as the field's description, and the model
        # returned that sentence as the field's value.
        integration_field = (
            '"integration_note": "1-2 sentences: how this routine fits around the '
            f'{" and ".join(integration_parts)} schedule.",' if integration_parts else "")

        snap = _snapshot(raw_plan)
        din = raw_plan.get("dinacharya_protocol") or {}
        plan_summary = {
            "user": {
                "name": user_profile.get("name"),
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": summary.get("dominant_dosha") or user_profile.get("dominant_dosha"),
                "vikriti": dosha,
                "agni_type": agni_type,
                "current_season": season,
                "stress_level": user_profile.get("stress_level"),
                "sleep_quality": user_profile.get("sleep_quality"),
                "medical_history": list(user_profile.get("medical_history") or []),
                "current_medications": list(user_profile.get("current_medications") or []),
                "allergies": list(user_profile.get("allergies") or []),
                "pregnant": bool(din.get("pregnancy_notices")),
                "goal": rp.get("routine_goal") or user_profile.get("goal"),
            },
            "schedule": {**snap, "has_gym_block": has_gym, "has_yoga_block": has_yoga},
            "withheld": [w.get("practice") for w in din.get("withheld_practices") or []]
                        + [r["name"] for r in din.get("morning_rituals") or [] if r.get("withheld")]
                        + [w.get("item") for w in (raw_plan.get("seasonal_ritucharya") or {}).get("withheld") or []],
            "exercise_limit": (raw_plan.get("exercise_limits") or {}).get("cap", "none"),
            "fasting_withheld": bool(raw_plan.get("fasting_notice") and raw_plan.get("requested_fasting") is not None),
        }

        prompt = _USER_PROMPT.format(
            agni_type=agni_type,
            season_label=season_label,
            wake_time=snap["wake_time"],
            sleep_time=snap["sleep_time"],
            integration_field=integration_field,
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

        enrichment = {k: enrichment[k] for k in _FIELDS if enrichment.get(k)}
        enrichment, coaching_withheld = gate_routine_enrichment(enrichment, raw_plan, user_profile)
        raw_plan.update(enrichment)
        raw_plan["coaching_withheld"] = coaching_withheld

        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        logger.info("Routine plan enriched via %s", llm_client.provider)

    except Exception as e:
        logger.error("Routine enrichment failed: %s", e)

    return raw_plan
