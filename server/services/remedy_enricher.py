import json
import logging
from ai.llm_client import llm_client

logger = logging.getLogger(__name__)

async def enrich_remedies_plan(raw_plan: dict, user_profile: dict, remedies_prefs: dict = None) -> dict:
    """
    Enriches the generated remedies plan with Ayurvedic rationale,
    synergy notes, recovery timeline, and personalized introductions.
    """
    try:
        symptoms_addressed = raw_plan.get("symptoms_addressed", [])
        if not symptoms_addressed:
            raw_plan["enriched"] = False
            return raw_plan

        # Compress plan for LLM prompt
        compressed_symptoms = []
        for sym in symptoms_addressed:
            compressed_symptoms.append({
                "id": sym.get("symptom_id"),
                "name": sym.get("symptom_display"),
                "severity": sym.get("severity"),
                "remedy_name": sym.get("remedy", {}).get("name")
            })

        prompt = f"""
You are an expert Ayurvedic practitioner. A home remedies plan has been generated for a user with the following profile:
- Age: {user_profile.get('age')}
- Gender: {user_profile.get('gender')}
- Dominant Dosha: {user_profile.get('dominant_dosha')}
- Secondary Dosha: {user_profile.get('secondary_dosha')}
- Medical History: {', '.join(user_profile.get('medical_history', []))}
- Current Medications: {', '.join(user_profile.get('current_medications', []))}
- Allergies: {', '.join(user_profile.get('allergies', []))}

Symptoms Addressed:
{json.dumps(compressed_symptoms, indent=2)}

Provide an enriched context in EXACTLY this JSON format:
{{
  "personalized_intro": "2-3 sentences addressing user's specific symptom combination and dosha",
  "remedy_rationale": {{
    "symptom_id": "Why this specific remedy works for this dosha - Ayurvedic explanation"
  }},
  "synergy_note": "If multiple symptoms, explain how the remedies work together. If single symptom, explain how the remedy balances the entire body.",
  "recovery_timeline": "What to expect day by day",
  "prevention_tips": ["tip1", "tip2", "tip3"],
  "when_to_escalate": "Specific signs that mean stop home treatment and see a doctor"
}}
"""

        response = await llm_client.generate(
            prompt=prompt,
            system_prompt="You are a clinical Ayurvedic expert. Output strictly valid JSON matching the schema.",
            json_mode=True,
        )
        
        enrichment_data = json.loads(response)
        if "error" in enrichment_data:
            raise ValueError(f"LLM provider error: {enrichment_data['error']}")

        # Merge enrichment data into the plan
        raw_plan["personalized_intro"] = enrichment_data.get("personalized_intro", "")
        raw_plan["synergy_note"] = enrichment_data.get("synergy_note", "")
        raw_plan["recovery_timeline"] = enrichment_data.get("recovery_timeline", "")
        raw_plan["prevention_tips"] = enrichment_data.get("prevention_tips", [])
        raw_plan["when_to_escalate"] = enrichment_data.get("when_to_escalate", "")
        
        # Merge rationales
        rationales = enrichment_data.get("remedy_rationale", {})
        for sym in raw_plan.get("symptoms_addressed", []):
            sym_id = sym.get("symptom_id")
            if sym_id in rationales:
                sym["ayurvedic_rationale"] = rationales[sym_id]
        
        raw_plan["enriched"] = True
        raw_plan["enrichment_model"] = llm_client.provider
        return raw_plan

    except Exception as e:
        logger.error(f"Failed to enrich remedies plan: {e}")
        raw_plan["enriched"] = False
        raw_plan["enrichment_error"] = str(e)
        return raw_plan
