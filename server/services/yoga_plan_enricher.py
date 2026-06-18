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
    "Wednesday": "..."
  },
  "breathing_guidance": "Specific advice on how to pair breath with their selected pranayama and asana style for their dosha",
  "lifestyle_sync": "2-3 sentences on how this practice aligns with their dosha's natural rhythms, including diet or sleep tips",
  "progression_plan": {
    "week_1": "What to focus on structurally",
    "week_2": "How to deepen the practice",
    "week_3": "Next progression or mental focus",
    "week_4": "Integration or restorative focus"
  },
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
                "gender": user_profile.get("gender"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "yoga_goal": yoga_prefs.get("yoga_goal"),
                "experience": yoga_prefs.get("yoga_experience"),
                "style_preference": yoga_prefs.get("yoga_style_preference"),
                "time_available": yoga_prefs.get("time_available_minutes"),
                "injuries": user_profile.get("injuries_or_limitations"),
                "medical_history": user_profile.get("medical_history"),
                "pregnancy": user_profile.get("pregnancy_or_nursing", False)
            },
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
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        
        logger.info(f"Successfully enriched yoga plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich yoga plan: {str(e)}")
        
    return raw_plan
