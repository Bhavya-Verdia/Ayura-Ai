import json
from ai.llm_client import llm_client
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Yoga instructor and Ayurvedic wellness advisor. You enrich deterministically generated yoga plans with personalized coaching insights.

You will receive a yoga plan summary and user profile.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and generated yoga plan, provide enrichment data in this exact JSON schema:

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

User profile and plan:
{plan_summary_json}
"""

async def enrich_yoga_plan(raw_plan: dict, user_profile: dict, yoga_prefs: dict) -> dict:
    raw_plan["enriched"] = False
    
    try:
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
            },
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
                    "theme": session.get("dosha_theme")
                })
                
        prompt = USER_PROMPT_TEMPLATE.replace("{plan_summary_json}", json.dumps(plan_summary, indent=2))
        
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

        # Merge enrichment
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
