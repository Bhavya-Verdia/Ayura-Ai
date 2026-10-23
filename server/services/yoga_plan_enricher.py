import json
from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Yoga instructor and Ayurvedic wellness advisor. You enrich deterministically generated yoga plans with personalized coaching insights.

You will receive a yoga plan summary, user profile, and relevant Ayurvedic knowledge retrieved from a classical knowledge base.
Use the knowledge base context to ground your response in classical Ayurvedic principles.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile, generated yoga plan, and Ayurvedic knowledge context, provide enrichment data in this exact JSON schema:

{
  "plan_title": "Personalized [dosha] [goal] Yoga Plan for [name]",
  "plan_description": "2-3 sentence motivating overview specific to this user's profile and dosha",
  "daily_intention": {
    "Monday": "1 short mindful intention for this day's sequence",
    "Tuesday": "...",
    "Wednesday": "...",
    "Thursday": "...",
    "Friday": "...",
    "Saturday": "...",
    "Sunday": "..."
  },
  "breathing_guidance": "Specific advice on how to pair breath with their selected pranayama and asana style for their dosha",
  "lifestyle_sync": "2-3 sentences on how this practice aligns with their dosha's natural rhythms, including diet or sleep tips",
  "progression_plan": {
    "week_1": "What to focus on structurally",
    "week_2": "How to deepen the practice",
    "week_3": "Next progression or mental focus",
    "week_4": "Integration or restorative focus"
  },
  "condition_coaching": "If the user has medical conditions, write 2-3 sentences of condition-specific coaching — what to watch for, how to adapt, and the therapeutic mechanism of the key poses. Omit this field entirely if no conditions are present.",
  "age_coaching": "If the user is senior (60+) or youth (≤17), write 1 sentence of age-specific guidance. Omit if age_group is adult.",
  "motivational_note": "1 personalized sentence addressing their specific goal and dosha"
}

RULES FOR daily_intention:
Each day in the schedule below carries an "intensity" — strong, moderate, gentle
or restorative — plus an "intensity_intent" describing what that day is for and,
on the easier days, an "effort_cue" saying how the poses should be worked. The
intention you write for a day MUST match them. Do not write about effort, edges
or challenge on a gentle or restorative day, and do not write a purely passive
intention onto a strong one.

Every day is the SAME LENGTH and deliberately the SAME SEQUENCE, give or take a
pose or two — that repetition is the design, so the practitioner stops needing to
read the plan. Never suggest an easier day is a shorter one, never present a day
as a new or different practice, and never frame the repetition as a limitation.
What changes between days is depth and effort, not the poses.

The user practises at "practice_time" in the profile below. Never recommend
practising at another time of day: the plan is built for that time (no Surya
Namaskar in the evening, for one), and a note saying "ideally in the evening"
beside a morning plan contradicts the plan it sits in.

AYURVEDIC KNOWLEDGE BASE (use these classical references to ground your response):
{rag_context}

User profile and plan:
{plan_summary_json}
"""

# Words in pose names that name no particular pose.
_GENERIC_POSE_WORDS = {"standing", "forward", "supported", "reclining", "shoulder", "seated",
                       "extended", "revolved", "half", "opener", "bridge", "salamba", "ardha",
                       "uttanasana", "facing", "downward"}


def _name_word_counts() -> dict[str, int]:
    import re
    import services.yoga_plan_engine as Y
    counts: dict[str, int] = {}
    for p in Y.yoga_poses:
        for w in {w.lower() for n in (p.get("english_name"), p.get("sanskrit_name")) if n
                  for w in re.split(r"[\s-]+", n)}:
            counts[w] = counts.get(w, 0) + 1
    return counts


_NAME_WORD_COUNTS = _name_word_counts()


def gate_yoga_enrichment(enrichment: dict, raw_plan: dict, user_profile: dict,
                         yoga_prefs: dict) -> tuple[dict, list[dict]]:
    """Withhold narrative sentences that recommend what the plan excluded.

    The narrative was merged ungated. The plan withholds Kapalabhati from a
    hypertensive and a headstand from someone with glaucoma; the breathing
    guidance and condition coaching beside it could name either, and the
    lifestyle line could recommend warm milk to someone allergic to dairy."""
    import re
    import services.yoga_plan_engine as Y
    from services.panchakarma_enricher import _DISTANCING, _sentences
    from services.remedy_engine import _allergen_entries, _contains_allergen
    from services.ahara_safety import unreadable_script

    served = {p.get("pose_id") for d in raw_plan.get("weekly_schedule") or []
              for k in ("warmup", "main_sequence", "cooldown")
              for p in (d.get("session") or {}).get(k) or []}
    age_group = Y._get_age_group(user_profile.get("age") or 30)
    risks = Y._build_risk_set(user_profile, age_group, yoga_prefs)
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))
    names: dict[str, str] = {}
    for pose in Y.yoga_poses:
        if pose.get("id") in served:
            continue
        why = None
        if set(pose.get("risk_tags") or []) & risks:
            why = "a pose this plan leaves out for your conditions"
        elif pregnant and (pose.get("category") == "inversion" or pose.get("pregnancy_safe") is False):
            why = "a pose this plan leaves out in pregnancy"
        if why:
            full = [pose.get("english_name"), pose.get("sanskrit_name")]
            # The words people actually write: "Headstand" for "Supported Headstand
            # Pose", "Shoulderstand" for "Shoulder Stand", "Sirsasana" for "Salamba
            # Sirsasana". A full-name match alone missed "practise Headstand".
            # Only words that name ONE pose: "Rotation" is in five pose names and
            # withheld "smooth rotation" from a pregnant woman's intention.
            short = [w for n in full if n for w in re.split(r"[\s-]+", n)
                     if len(w) > 6 and w.lower() not in _GENERIC_POSE_WORDS
                     and _NAME_WORD_COUNTS.get(w.lower(), 0) == 1]
            joined = [n.replace(" ", "") for n in full if n and " " in n]
            for n in [*full, *short, *joined]:
                if n and len(n) > 4:
                    names[n.lower()] = why
    for x in raw_plan.get("pranayama_safety_exclusions") or []:
        full = str(x.get("name") or "")
        for n in [full.split(" (")[0], *re.findall(r"\(([^)]+)\)", full)]:
            if len(n) > 4:
                names[n.lower()] = "a breath this plan withholds for you"
    name_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\b",
                         re.I) if names else None
    allergens = _allergen_entries(user_profile.get("allergies") or [])
    withheld: list[dict] = []
    # The plan is built for the time the user chose. A sentence recommending the
    # other one ("Practice at the same time daily, ideally in the evening" beside a
    # morning plan) is withheld, the way a sentence naming a withheld pose is.
    chosen = (yoga_prefs.get("time_of_day_preference") or "morning").lower()
    other_time = {"morning": r"\bevening\b|\bafter (?:6|six) ?pm\b",
                  "evening": r"\bmorning\b|\bdawn\b|\bsunrise\b|\bbefore (?:6|six) ?am\b"}.get(chosen)
    other_re = re.compile(other_time, re.I) if other_time else None
    practice_re = re.compile(r"\b(practi[cs]e|practi[cs]ing|session|sequence|asana)\b", re.I)

    def screen(text: str, field: str) -> str:
        if (script := unreadable_script(text)):
            withheld.append({"field": field, "text": text[:200],
                             "reason": f"written in {script} script, which the safety checks cannot read"})
            return ""
        kept = []
        for sent in _sentences(text):
            distanced = bool(_DISTANCING.search(sent))
            reason = None
            if name_re and not distanced and (m := name_re.search(sent)):
                reason = f"names {m.group(1)}, {names[m.group(1).lower()]}"
            if not reason and not distanced:
                hit = next((e for e in allergens if _contains_allergen(sent, e)), None)
                if hit:
                    reason = f"names a {hit['label'].lower()} food — declared allergy"
            if not reason and other_re and other_re.search(sent) and practice_re.search(sent):
                reason = f"recommends practising at another time; this plan is for the {chosen}"
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

    return {k: walk(v, k) for k, v in enrichment.items()}, withheld


async def enrich_yoga_plan(raw_plan: dict, user_profile: dict, yoga_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        dosha = user_profile.get("dominant_dosha") or "vata"
        conditions = user_profile.get("medical_history") or []
        goal = yoga_prefs.get("yoga_goal") or "general_wellness"

        # Fetch grounding context from ChromaDB before calling the LLM
        rag_query = f"{dosha} yoga practice {goal} pranayama Ayurvedic wellness"
        # Retrieval has its own handler: under the outer `except` a ChromaDB restart
        # cost the plan all of its coaching, not just the references.
        docs = []
        try:
            docs = await rag_pipeline.query(rag_query, "ayurveda", n_results=4, dosha_filter=dosha)
            if not docs and conditions:
                cond_query = f"{conditions[0]} yoga therapy Ayurvedic treatment"
                docs = await rag_pipeline.query(cond_query, "ayurveda", n_results=3)
        except Exception as e:
            logger.warning(f"Yoga enrichment: retrieval failed ({e}); continuing without it")
        rag_context = rag_pipeline.format_context(docs, max_chars=1500) or "No specific context retrieved — use classical Ayurvedic principles."

        # Build compressed summary for LLM context
        plan_summary = {
            "user": {
                "age": user_profile.get("age"),
                "age_group": raw_plan.get("user_summary", {}).get("age_group", "adult"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "vikriti": user_profile.get("vikriti_dominant"),
                "vikriti_secondary": user_profile.get("vikriti_secondary"),
                "yoga_goal": yoga_prefs.get("yoga_goal"),
                "experience": yoga_prefs.get("yoga_experience"),
                "style_preference": yoga_prefs.get("yoga_style_preference"),
                "time_available": yoga_prefs.get("time_available_minutes"),
                "practice_time": yoga_prefs.get("time_of_day_preference") or "morning",
                "injuries": user_profile.get("injuries_or_limitations"),
                "medical_history": user_profile.get("medical_history"),
                "current_symptoms": user_profile.get("current_symptoms"),
                "stress_level": user_profile.get("stress_level"),
                "sleep_quality": user_profile.get("sleep_quality"),
                "agni_type": user_profile.get("agni_type"),
                "ama_indicator": user_profile.get("ama_indicator"),
                "ojas_level": user_profile.get("ojas_level"),
                "pregnancy": user_profile.get("pregnancy_or_nursing", False),
                "current_season": user_profile.get("current_season"),
                "seasonal_note": raw_plan.get("seasonal_note"),
                "allergies": user_profile.get("allergies"),
                "current_medications": user_profile.get("current_medications"),
            },
            # What the engine decided, so the narrative agrees with it.
            "withheld_breathing": [x.get("name") for x in (raw_plan.get("pranayama_safety_exclusions") or [])],
            "condition_guidance": [g.get("label") for g in (raw_plan.get("condition_guidance") or [])],
            "condition_protocols": [
                {
                    "condition": p.get("condition"),
                    "protocol_name": p.get("protocol_name"),
                    "sequence_note": p.get("sequence_note"),
                    "lifestyle_note": p.get("lifestyle_note"),
                }
                for p in (raw_plan.get("condition_protocols") or [])
            ] or None,
            "generated_schedule": []
        }

        for d in raw_plan.get("weekly_schedule", []):
            if d.get("rest"):
                plan_summary["generated_schedule"].append({
                    "day": d.get("day_name"),
                    "activity": "Rest"
                })
            else:
                session = d.get("session", {})
                main_poses = [p.get("pose_name") for p in session.get("main_sequence", [])]
                prana = [pr.get("technique_name") for pr in session.get("pranayama_section", [])]
                plan_summary["generated_schedule"].append({
                    "day": d.get("day_name"),
                    "activity": "Yoga Practice",
                    "main_poses": main_poses,
                    "pranayama": prana,
                    "theme": session.get("dosha_theme"),
                    # The week has a load arc and the daily intention is rendered
                    # on the day card, so the enricher has to know which day is
                    # which. Without it the LLM writes the same "find your edge"
                    # line onto the restorative day it writes onto a strong one,
                    # which contradicts the practice underneath it.
                    "intensity": session.get("intensity"),
                    "intensity_intent": session.get("intensity_note"),
                    "effort_cue": session.get("effort_cue"),
                })

        prompt = (
            USER_PROMPT_TEMPLATE
            .replace("{rag_context}", rag_context)
            .replace("{plan_summary_json}", json.dumps(plan_summary, indent=2))
        )

        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True
        )

        # Parse JSON — guard against the LLM returning {"error": "..."} when
        # both providers are unavailable (json.loads succeeds but has no schema keys)
        enrichment = json.loads(response_text)
        if "error" in enrichment:
            raise ValueError(f"LLM provider error: {enrichment['error']}")

        # Merge enrichment — through the gate, never around it.
        enrichment, raw_plan["coaching_withheld"] = gate_yoga_enrichment(enrichment, raw_plan, user_profile, yoga_prefs)
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Yoga Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["daily_intention"] = enrichment.get("daily_intention", {})
        raw_plan["breathing_guidance"] = enrichment.get("breathing_guidance", "")
        raw_plan["lifestyle_sync"] = enrichment.get("lifestyle_sync", "")
        raw_plan["progression_plan"] = enrichment.get("progression_plan", {})
        if enrichment.get("condition_coaching"):
            raw_plan["condition_coaching"] = enrichment["condition_coaching"]
        if enrichment.get("age_coaching"):
            raw_plan["age_coaching"] = enrichment["age_coaching"]
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider

        logger.info(f"Successfully enriched yoga plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich yoga plan: {str(e)}")

    return raw_plan
