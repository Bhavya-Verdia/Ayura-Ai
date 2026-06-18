import json
from ai.llm_client import llm_client
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Ayurvedic Nutritionist. You enrich deterministically generated diet plans with personalized recipe ideas and Ayurvedic coaching insights.

You will receive a diet plan summary containing the raw foods chosen for each day, along with the user profile.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and generated daily diet plan (raw foods), provide enrichment data in this exact JSON schema:

{
  "plan_title": "Personalized [dosha] [goal] Diet Plan for [name]",
  "plan_description": "2-3 sentence motivating overview specific to this user's profile and dosha",
  "daily_meals_ideas": {
    "Monday": {
      "breakfast": "A short, appetizing meal idea using the raw foods provided for breakfast",
      "lunch": "A short, appetizing meal idea using the raw foods provided for lunch",
      "snack": "A short, appetizing snack idea",
      "dinner": "A short, appetizing meal idea using the raw foods provided for dinner"
    },
    "Tuesday": {
      "breakfast": "...",
      "lunch": "...",
      "snack": "...",
      "dinner": "..."
    }
    // Continue for all 7 days exactly as provided in the summary
  },
  "hydration_guidance": "Specific hydration advice based on their dosha and stated water intake",
  "fasting_guidance": "Specific advice on managing their intermittent fasting or specific fasting days according to Ayurveda",
  "gut_health_sync": "2-3 sentences on how these specific foods will help their stated gut health issue",
  "motivational_note": "1 personalized sentence addressing their specific diet goal and dosha"
}

User profile and plan:
{plan_summary_json}
"""

async def enrich_diet_plan(raw_plan: dict, user_profile: dict, diet_prefs: dict) -> dict:
    raw_plan["enriched"] = False
    
    try:
        # Build compressed summary for LLM context
        plan_summary = {
            "user": {
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "diet_goal": diet_prefs.get("diet_goal"),
                "dietary_type": diet_prefs.get("dietary_type"),
                "allergies": diet_prefs.get("food_allergies"),
                "intolerances": diet_prefs.get("food_intolerances"),
                "gut_issue": diet_prefs.get("gut_health_issue"),
                "fasting_window": diet_prefs.get("intermittent_fasting"),
                "fasting_days": diet_prefs.get("fasting_days"),
                "water_intake": diet_prefs.get("water_intake"),
                "pregnancy": user_profile.get("pregnancy_or_nursing", False)
            },
            "generated_schedule": []
        }
        
        for d in raw_plan.get("weekly_schedule", []):
            day_data = {
                "day": d.get("day_name"),
                "is_fasting_day": d.get("is_fasting_day"),
                "meals": {}
            }
            
            for meal_name, items in d.get("meals", {}).items():
                if meal_name == "daily_macros_approx":
                    day_data["approx_macros"] = items
                    continue
                # Just send the names of the foods to the LLM to inspire the recipes
                day_data["meals"][meal_name] = [item.get("name") for item in items]
                
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
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Ayurvedic Diet Plan")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        raw_plan["daily_meals_ideas"] = enrichment.get("daily_meals_ideas", {})
        raw_plan["hydration_guidance"] = enrichment.get("hydration_guidance", "")
        raw_plan["fasting_guidance"] = enrichment.get("fasting_guidance", "")
        raw_plan["gut_health_sync"] = enrichment.get("gut_health_sync", "")
        raw_plan["motivational_note"] = enrichment.get("motivational_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        
        logger.info(f"Successfully enriched diet plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich diet plan: {str(e)}")
        
    return raw_plan
