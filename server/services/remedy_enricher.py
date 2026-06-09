import json
from ai.llm_client import llm_client
from core.logger import logger

SYSTEM_PROMPT = """
You are an expert Ayurvedic Doctor (Vaidya). You enrich deterministically selected Ayurvedic remedies/medicines with personalized coaching and clear preparation instructions.

You will receive a plan summary containing the selected remedies, along with the user profile.
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """
Given this user profile and selected remedies, provide enrichment data in this exact JSON schema:

{
  "plan_title": "Personalized [Type] Protocol for [name]",
  "plan_description": "2-3 sentence motivating overview explaining how these remedies will treat their specific symptoms while balancing their dosha",
  "remedy_instructions": {
    "remedy_id_1": "Detailed, encouraging explanation on exactly how and when to take this remedy, including the preparation method provided in the summary. Mention the taste and how to mask it if needed.",
    "remedy_id_2": "..."
    // Continue for all remedies exactly as provided in the summary
  },
  "lifestyle_support": "2-3 sentences of general lifestyle or dietary advice to speed up recovery from their stated symptoms",
  "safety_note": "A very brief note reminding them to discontinue if symptoms worsen"
}

User profile and plan:
{plan_summary_json}
"""

async def enrich_remedies_plan(raw_plan: dict, user_profile: dict, rem_prefs: dict) -> dict:
    raw_plan["enriched"] = False
    
    if not raw_plan.get("selected_remedies"):
        # No remedies matched, no need to enrich
        return raw_plan
        
    try:
        # Build compressed summary for LLM context
        plan_summary = {
            "user": {
                "age": user_profile.get("age"),
                "dominant_dosha": user_profile.get("dominant_dosha"),
                "symptoms": raw_plan.get("user_summary", {}).get("reported_symptoms", []),
                "pregnancy": raw_plan.get("user_summary", {}).get("pregnant", False)
            },
            "type": raw_plan.get("type"),
            "selected_remedies": []
        }
        
        for r in raw_plan.get("selected_remedies", []):
            plan_summary["selected_remedies"].append({
                "id": r["id"],
                "name": r["name"],
                "preparation_method": r["preparation_method"],
                "taste": r["taste_profile"]
            })
                
        prompt = USER_PROMPT_TEMPLATE.replace("{plan_summary_json}", json.dumps(plan_summary, indent=2))
        
        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True
        )
        
        # Parse JSON
        enrichment = json.loads(response_text)
        
        # Merge enrichment
        raw_plan["plan_title"] = enrichment.get("plan_title", "Personalized Protocol")
        raw_plan["plan_description"] = enrichment.get("plan_description", "")
        
        # Attach detailed instructions back to the individual remedies
        instructions = enrichment.get("remedy_instructions", {})
        for r in raw_plan["selected_remedies"]:
            r["detailed_instructions"] = instructions.get(r["id"], r["preparation_method"])
            
        raw_plan["lifestyle_support"] = enrichment.get("lifestyle_support", "")
        raw_plan["safety_note"] = enrichment.get("safety_note", "")
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        
        logger.info(f"Successfully enriched remedy plan using {llm_client.provider}")
    except Exception as e:
        logger.error(f"Failed to enrich remedy plan: {str(e)}")
        
    return raw_plan
