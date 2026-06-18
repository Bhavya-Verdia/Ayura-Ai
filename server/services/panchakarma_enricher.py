import json
from ai.llm_client import llm_client
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Ayurvedic Doctor (Vaidya). You enrich deterministically generated Panchakarma plans with personalized coaching, precise instructions, and emotional support.

You will receive a plan summary containing the therapies chosen for each day, along with the user profile.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and generated daily detox plan, provide enrichment data in this exact JSON schema:

{
  "plan_title": "Personalized [setting] Panchakarma Protocol for [name]",
  "plan_description": "2-3 sentence motivating overview explaining the phases of this specific plan",
  "daily_guidance": {
    "Day 1": "A short, precise instruction on how to approach today's therapies and what to expect physically/emotionally",
    "Day 2": "...",
    "Day 3": "..."
    // Continue for all days exactly as provided in the summary
  },
  "dietary_rules": "Strict Ayurvedic dietary instructions for this specific setting and goal (e.g. Kitchari mono-diet instructions)",
  "emotional_detox_sync": "2-3 sentences on what emotional release to expect during the Pradhana Karma phase for their specific dosha",
  "motivational_note": "1 personalized sentence addressing their specific goal and dosha"
}

User profile and plan:
{plan_summary_json}
"""

async def enrich_panchakarma_plan(raw_plan: dict, user_profile: dict, pk_prefs: dict) -> dict:
    raw_plan["enriched"] = False
    
    try:
        # Build compressed summary for LLM context
        plan_summary = {
            "user": {
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "goal": pk_prefs.get("panchakarma_goal"),
                "setting": pk_prefs.get("setting"),
                "experience": pk_prefs.get("detox_experience"),
                "duration_days": pk_prefs.get("available_time_days"),
                "pregnancy": user_profile.get("pregnancy_or_nursing", False),
                "season": pk_prefs.get("current_season")
            },
            "generated_schedule": []
        }
        
        for d in raw_plan.get("daily_schedule", []):
            day_data = {
                "day": f"Day {d.get('day')}",
                "phase": d.get("phase"),
                "therapies": [t.get("name") for t in d.get("therapies", [])]
            }
            plan_summary["generated_schedule"].append(day_data)
                
        prompt = USER_PROMPT_TEMPLATE.replace("{plan_summary_json}", json.dumps(plan_summary, indent=2))
        
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
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Panchakarma Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["daily_guidance"] = enrichment.get("daily_guidance", {})
        raw_plan["dietary_rules"] = enrichment.get("dietary_rules", "")
        raw_plan["emotional_detox_sync"] = enrichment.get("emotional_detox_sync", "")
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        
        logger.info(f"Successfully enriched panchakarma plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich panchakarma plan: {str(e)}")
        
    return raw_plan
