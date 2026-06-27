import json
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
- Dosha intensity principle: Vata types → low intensity, favour stability; Pitta types → moderate, avoid heat and competition; Kapha types → high intensity required to overcome natural heaviness.
- Seasonal restriction: Grishma (summer) and Varsha (monsoon) — reduce intensity by at least 50%; Hemanta/Shishira (winter) — full intensity permitted.
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
    "week_1": "What to focus on",
    "week_2": "How to progress",
    "week_3": "Next progression",
    "week_4": "Deload guidance"
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

KNOWLEDGE BASE CONTEXT (Ayurvedic + fitness principles to ground your response):
{rag_context}

User profile and plan:
{plan_summary_json}
"""

async def enrich_gym_plan(raw_plan: dict, user_profile: dict, gym_prefs: dict) -> dict:
    raw_plan["enriched"] = False

    try:
        dosha = user_profile.get("dominant_dosha") or "vata"
        goal = gym_prefs.get("gym_goal") or "general_fitness"
        fitness_level = gym_prefs.get("fitness_level") or "beginner"

        # Fetch grounding context from both fitness and Ayurveda collections
        rag_query = f"{dosha} dosha exercise training recovery {goal} {fitness_level}"
        fitness_docs = await rag_pipeline.query(rag_query, "fitness", n_results=3)
        ayur_docs = await rag_pipeline.query(f"{dosha} physical activity lifestyle", "ayurveda", n_results=2, dosha_filter=dosha)
        rag_context = rag_pipeline.format_context(fitness_docs + ayur_docs, max_chars=1500) or "No specific context retrieved — use classical Ayurvedic and modern fitness principles."

        plan_summary = {
            "user": {
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "bmi": user_profile.get("bmi"),
                "bmi_category": user_profile.get("bmi_category"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "dosha_scores": user_profile.get("dosha_scores"),
                "fitness_level": gym_prefs.get("fitness_level"),
                "gym_goal": gym_prefs.get("gym_goal"),
                "workout_days": gym_prefs.get("workout_days_per_week"),
                "duration_minutes": gym_prefs.get("workout_duration_minutes"),
                "available_equipment": gym_prefs.get("available_equipment"),
                "injuries": gym_prefs.get("injuries_or_limitations"),
                "medical_history": user_profile.get("medical_history"),
                "activity_level": user_profile.get("activity_level")
            },
            "generated_schedule": [
                {
                    "day": d.get("day_name"),
                    "focus": d.get("focus"),
                    "exercises": [e.get("exercise_name") for e in d.get("main_workout", [])]
                }
                for d in raw_plan.get("weekly_schedule", [])
            ]
        }

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
        raw_plan["nutrition_sync"] = enrichment.get("nutrition_sync", {})
        raw_plan["recovery_protocol"] = enrichment.get("recovery_protocol", {})
        raw_plan["progression_plan"] = enrichment.get("progression_plan", {})
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
