import json
import re

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert fitness coach and Ayurvedic wellness advisor. You enrich deterministically generated gym plans with personalized coaching insights.

You will receive a gym plan summary, user profile, and relevant fitness/Ayurvedic knowledge from a classical knowledge base.
Use the knowledge context to ground your response in both modern exercise science and Ayurvedic principles.

CLASSICAL VYAYAMA VIDHI (Charaka Sutrasthana Ch.7) — incorporate these principles:
- Ardhashakti rule: Exercise must be performed to only half (Ardha) of maximum capacity (Bala). The sign to STOP is sweating on the forehead, nose, and joints together with onset of mouth-breathing.
- Atiyoga (over-exercise) depletes Ojas and aggravates Vata — signs include breathlessness, tremor, dizziness, excessive thirst, joint pain.
- Dosha intensity principle: Vata types → low intensity, favour stability; Pitta types → moderate, avoid heat and competition; Kapha types → vigorous effort to overcome natural heaviness — always within the limits the plan's safety notices set.
- Seasonal (Ritu): classical texts advise the least exertion in Grishma (summer) and Varsha (monsoon) and allow the most in Hemanta/Shishira (winter). The plan's sets, reps and loads are fixed and are not yours to change — express the season as effort: stop earlier, rest longer, train in the cooler hours.
- Pre-exercise: Snehana (oil application) and light meal 1 hr before for Vata; dry and light for Kapha.
- Post-exercise: 10-min rest (Vishrama) before bathing. Cold water on head immediately after exercise is prohibited in classical texts.

Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile, generated gym plan, and knowledge context, provide enrichment data in this exact JSON schema:

{
  "plan_title": "Personalized [dosha] [goal] Plan for [name]",
  "plan_description": "2-3 sentence motivating overview specific to this user's profile",
  "weekly_focus_notes": {
    "Monday": "1 sentence coaching tip for this day's focus",
    "Tuesday": "...",
    ...
  },
  "nutrition_sync": {
    "pre_workout_meal": "Specific meal suggestion aligned with dosha + goal (not generic)",
    "post_workout_meal": "Specific meal suggestion",
    "hydration": "Specific hydration guidance for dosha"
  },
  "recovery_protocol": {
    "sleep": "Specific sleep guidance for dosha + training intensity",
    "active_recovery": "What to do on rest days",
    "signs_of_overtraining": [
      "3-4 specific warning signs for this user's dosha + fitness level"
    ]
  },
  "progression_plan": {
    "week_1": "COACHING for this week — see rules below",
    "week_2": "...",
    "week_3": "...",
    "week_4": "..."
  },
  "vyayama_vidhi": {
    "ardhashakti_guideline": "1 sentence: at what point should THIS user stop their workout, based on their dosha, age, and fitness level — citing Ardhabala principle",
    "atiyoga_warning_signs": [
      "3-4 specific early-warning signs of over-exercise for this user's dosha and fitness level"
    ],
    "pre_workout_ritual": "Dosha-specific pre-workout ritual (timing, food, Abhyanga or not, mindset)",
    "post_workout_ritual": "Post-workout Vishrama (rest), Snana (bathing), and nourishment guidance — classical and practical",
    "seasonal_adjustment": "1 sentence: how the current season (Ritu) should modify this user's training intensity or volume",
    "dosha_intensity_principle": "1 sentence: Vyayama Shakti principle specific to their dominant dosha",
    "vyayama_contraindications": [
      "2-3 conditions or situations when this user should SKIP training entirely, based on classical texts and their profile"
    ]
  },
  "ayurvedic_lifestyle_sync": "2-3 sentences on how this training plan aligns with their dosha's natural rhythms and seasonal considerations",
  "classical_transparency_note": "1-2 sentences being honest with the user: classical Ayurvedic Vyayama (Charaka Sutrasthana Ch.7) specified exercises like Malla Yuddha (wrestling), Danda Vyayama (staff exercises), Ashva Pariksha (horse riding), Naukasana, and swimming in rivers — NOT modern gym equipment. Explain that this plan applies the PRINCIPLES of classical Vyayama (Ardhashakti, dosha-appropriate intensity, seasonal modification) to modern exercises, which aligns with the spirit of the tradition.",
  "motivational_note": "1 personalized sentence addressing their specific goal and dosha"
}

RULES FOR SAFETY — these override every principle above:
- `safety` below lists decisions the plan has already made for this person's
  health, age or pregnancy. Your coaching must agree with them. Never encourage
  heavier loads, maximal efforts, breath-holding, jumping, inversions or more
  intensity than they allow, whatever the dosha principle says.
- If `pregnancy_or_nursing` is true, write for a pregnant or nursing woman: no
  lying flat on the back after the first trimester, no breath-holding, no
  pushing to exhaustion, and stop for pain, bleeding, dizziness or breathlessness.
- Food: suggest VEGETARIAN foods only (no meat, fish, egg), never name anything
  in `allergies`, and respect `medical_history` (e.g. no sugary drinks for a
  diabetic). Any suggestion naming a declared allergen or an animal food is
  removed before the practitioner sees it.

RULES FOR progression_plan — the four weeks are ALREADY PROGRAMMED. The
`progression` block below gives you, for each week: its theme, the sets, reps and
rest the main lifts carry that week, the rule that moves the load, and the main
lifts themselves by name with their starting loads. Those numbers are the plan.
Your job is the coaching around them, so:
- Do NOT invent, restate or contradict any set, rep, rest or weight figure. If you
  mention a number, it must be one given to you for that week.
- Name the practitioner's actual main lifts where it helps. They are listed.
- Week 4 is a DELOAD when the block says so. Never tell them to add weight, add
  volume, or chase a personal best in a deload week.
- Write for THIS person: their training age, their injuries, their dosha, their
  constraints. One or two sentences per week, no preamble.

KNOWLEDGE BASE CONTEXT (Ayurvedic + fitness principles to ground your response):
{rag_context}

User profile and plan:
{plan_summary_json}
"""

# What a deload week must never be told to do. The block reduces load by 15-20%
# and the whole point of it is that the practitioner backs off; a coaching line
# saying "add weight" beside a prescription that says "reduce weight 15%" is the
# contradiction that makes a plan untrustworthy, and it is the one an LLM is most
# likely to write because three of the four weeks call for exactly that.
_DELOAD_CONTRADICTION = re.compile(
    r"\b(add (weight|load|volume|a set)|increase (the )?(weight|load|volume|intensity)|"
    r"heavier|personal best|pr\b|new max|push (harder|for more)|go heavier|"
    r"more weight|add \d+(\.\d+)?\s*kg)\b", re.I)

def _as_list(value) -> list:
    """A string where a list belongs iterates into letters, and a one-letter term
    matches every word there is — the diet path's card was emptied that way."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if v]


# Animal foods. The app's food library is vegetarian, and the meal suggestions
# here were the one place in the gym plan that named food with no screen at all.
_NON_VEGETARIAN = ("chicken", "mutton", "meat", "beef", "pork", "lamb", "fish",
                   "salmon", "tuna", "prawn", "shrimp", "seafood", "egg", "omelet",
                   "omelette", "anda")
_NUTRITION_FIELDS = ("pre_workout_meal", "post_workout_meal", "hydration")


def screen_nutrition(nutrition: dict, user_profile: dict) -> tuple:
    """(what is safe to show, what was withheld and why).

    Prevention is the prompt; this is the backstop. A field is withheld whole
    rather than edited, because a sentence with its allergen cut out of it can
    read as a different recommendation."""
    from services.ahara_safety import ALLERGEN_TERMS, _term_in_text

    allergies = [a.lower() for a in _as_list(user_profile.get("allergies"))]
    kept, withheld = {}, []
    for key, text in (nutrition or {}).items():
        if not isinstance(text, str):
            continue
        low = text.lower()
        reason = None
        for allergy in allergies:
            terms = ALLERGEN_TERMS.get(allergy, [allergy])
            hit = next((t for t in terms if len(t) > 2 and _term_in_text(t, low)), None)
            if hit:
                reason = f"names {hit}, and you declared a {allergy.replace('_', ' ')} allergy"
                break
        if not reason:
            hit = next((t for t in _NON_VEGETARIAN if _term_in_text(t, low)), None)
            if hit:
                reason = f"names {hit}; this app's food guidance is vegetarian"
        if reason and key in _NUTRITION_FIELDS:
            withheld.append({"field": key, "reason": reason})
        else:
            kept[key] = text
    return kept, withheld


def build_plan_summary(raw_plan: dict, user_profile: dict, gym_prefs: dict) -> dict:
    """What the model is told about the practitioner and the plan it is enriching.

    Three fields were read off the wrong object. `fitness_level` and
    `injuries_or_limitations` live on the user profile — that is where
    `filter_exercises` reads them, and it is why the exercise gating has always
    been correct — but this asked `gym_prefs` for them, and `GymPreferences` has
    no such fields. Both were therefore `None` for every user who has ever
    generated a plan.

    So the coaching narrative wrapped around a correctly-gated plan was written
    for someone with no injuries and no known training age: the engine kept
    overhead pressing away from a torn rotator cuff, and the text beside it talked
    about pushing overhead. The RAG query was worse — `fitness_level` defaulted to
    "beginner" when missing, so every retrieval this feature has ever made asked
    for beginner material, including for advanced lifters.

    Split out from `enrich_gym_plan` so the mapping can be tested without an LLM
    call, which is the only reason it went unnoticed for as long as it did.
    """
    return {
        "user": {
            "age": user_profile.get("age"),
            "gender": user_profile.get("gender"),
            "weight_kg": user_profile.get("weight_kg"),
            "bmi": user_profile.get("bmi"),
            "bmi_category": user_profile.get("bmi_category"),
            "dominant_dosha": user_profile.get("dominant_dosha"),
            "dosha_scores": user_profile.get("dosha_scores"),
            "fitness_level": user_profile.get("fitness_level"),
            # What the practitioner lifts, which is what the load ranges in the
            # plan are built from. It has always been on gym_prefs and was never
            # sent, so the model could not see why the numbers were what they are.
            "strength_level": gym_prefs.get("strength_level"),
            "gym_goal": gym_prefs.get("gym_goal"),
            "training_style": gym_prefs.get("training_style"),
            "target_muscle_focus": gym_prefs.get("target_muscle_focus"),
            "cardio_preference": gym_prefs.get("cardio_preference"),
            "workout_days": gym_prefs.get("workout_days_per_week"),
            "duration_minutes": gym_prefs.get("workout_duration_minutes"),
            "available_equipment": gym_prefs.get("available_equipment"),
            # The plan's own resolved list: the gym form asks about injuries
            # too, and the profile field alone would leave the coaching blind
            # to everything declared there.
            "injuries": ((raw_plan.get("user_summary") or {}).get("injuries")
                         or user_profile.get("injuries_or_limitations")),
            "medical_history": user_profile.get("medical_history"),
            "activity_level": user_profile.get("activity_level"),
            # Not sent until now: the coaching for a pregnant practitioner was
            # written for someone who was not.
            "pregnancy_or_nursing": bool(user_profile.get("pregnancy_or_nursing")),
            "allergies": _as_list(user_profile.get("allergies")),
        },
        # What the engine has already decided about intensity and safety, so the
        # prose around the plan says the same thing as the plan.
        "safety": {k: raw_plan.get(k) for k in (
            "intensity_notice", "age_notice", "injury_notice", "pool_notice")
            if raw_plan.get(k)} | {
            "before_you_train": [g["label"] for g in raw_plan.get("condition_guidance") or []]},
        "generated_schedule": [
            {
                "day": d.get("day_name"),
                "focus": d.get("focus"),
                "exercises": [e.get("exercise_name") for e in d.get("main_workout", [])],
            }
            for d in raw_plan.get("weekly_schedule", [])
        ],
        # The four weeks as the engine programmed them. Without this the model was
        # writing a four-week progression narrative having been shown day names,
        # focus labels and exercise names — no sets, no reps, no rest, no loads,
        # and no idea which week was the deload. It was guessing, next to a
        # deterministic guide that was not.
        "progression": raw_plan.get("progression", []),
    }


def merge_progression(raw_plan: dict, coaching: dict) -> list:
    """Attach each week's coaching line to the week's actual prescription.

    One progression, not two. The engine's numbers and rule stay exactly as they
    were; the model's sentence rides alongside them, and is dropped rather than
    shipped when it contradicts the week it is describing.
    """
    merged = []
    for entry in raw_plan.get("progression", []):
        note = str(coaching.get(f"week_{entry['week']}", "") or "").strip()
        if note and entry.get("is_deload") and _DELOAD_CONTRADICTION.search(note):
            logger.warning(
                "Dropped deload coaching that told the practitioner to add load: %r", note)
            note = ""
        merged.append({**entry, "coach_note": note})
    return merged


async def enrich_gym_plan(raw_plan: dict, user_profile: dict, gym_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        dosha = user_profile.get("dominant_dosha") or "vata"
        goal = gym_prefs.get("gym_goal") or "general_fitness"
        fitness_level = user_profile.get("fitness_level") or "beginner"

        # Fetch grounding context from both fitness and Ayurveda collections
        rag_query = f"{dosha} dosha exercise training recovery {goal} {fitness_level}"
        fitness_docs = await rag_pipeline.query(rag_query, "fitness", n_results=3)
        ayur_docs = await rag_pipeline.query(f"{dosha} physical activity lifestyle", "ayurveda", n_results=2, dosha_filter=dosha)
        rag_context = rag_pipeline.format_context(fitness_docs + ayur_docs, max_chars=1500) or "No specific context retrieved — use classical Ayurvedic and modern fitness principles."

        plan_summary = build_plan_summary(raw_plan, user_profile, gym_prefs)

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

        # Parse JSON — guard against LLM error response
        enrichment = json.loads(response_text)
        if "error" in enrichment:
            raise ValueError(f"LLM provider error: {enrichment['error']}")

        # Merge enrichment
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Gym Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["weekly_focus_notes"] = enrichment.get("weekly_focus_notes", {})
        raw_plan["nutrition_sync"], raw_plan["nutrition_withheld"] = screen_nutrition(
            enrichment.get("nutrition_sync", {}), user_profile)
        raw_plan["recovery_protocol"] = enrichment.get("recovery_protocol", {})
        # `progression_plan` was written by the model, stored on the plan, and read
        # by nothing — not the plan view, not the export, not the chat agent. The
        # progression the user actually sees came from the engine. Rather than ship
        # two competing narratives, the coaching is merged into the engine's own
        # four weeks, which is the one the UI renders.
        raw_plan["progression"] = merge_progression(
            raw_plan, enrichment.get("progression_plan") or {})
        raw_plan["vyayama_vidhi"] = enrichment.get("vyayama_vidhi", {})
        raw_plan["ayurvedic_lifestyle_sync"] = enrichment.get("ayurvedic_lifestyle_sync", "")
        raw_plan["classical_transparency_note"] = enrichment.get("classical_transparency_note", "")
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider

        logger.info(f"Successfully enriched gym plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich gym plan: {str(e)}")

    return raw_plan
