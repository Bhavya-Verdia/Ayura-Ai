import json
from ai.llm_client import llm_client
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert fitness coach and Ayurvedic wellness advisor. You enrich deterministically generated gym plans with personalized coaching insights.

You will receive a gym plan summary and user profile.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and generated gym plan, provide enrichment data in this exact JSON schema:

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
  "ayurvedic_lifestyle_sync": "2-3 sentences on how this training plan aligns with their dosha's natural rhythms and seasonal considerations",
  "motivational_note": "1 personalized sentence addressing their specific goal and dosha"
}

User profile and plan:
{plan_summary_json}
"""

async def enrich_gym_plan(raw_plan: dict, user_profile: dict, gym_prefs: dict) -> dict:
    raw_plan["enriched"] = False
    
    try:
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
        
        prompt = USER_PROMPT_TEMPLATE.replace("{plan_summary_json}", json.dumps(plan_summary, indent=2))
        
        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True
        )
        
        # Parse JSON
        enrichment = json.loads(response_text)
        
        # Merge enrichment
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Gym Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["weekly_focus_notes"] = enrichment.get("weekly_focus_notes", {})
        raw_plan["nutrition_sync"] = enrichment.get("nutrition_sync", {})
        raw_plan["recovery_protocol"] = enrichment.get("recovery_protocol", {})
        raw_plan["progression_plan"] = enrichment.get("progression_plan", {})
        raw_plan["ayurvedic_lifestyle_sync"] = enrichment.get("ayurvedic_lifestyle_sync", "")
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        
        logger.info(f"Successfully enriched gym plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich gym plan: {str(e)}")
        
    return raw_plan
