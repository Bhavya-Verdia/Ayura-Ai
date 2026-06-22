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


async def enrich_medicines_plan(raw_plan: dict, user_profile: dict, medicines_prefs: dict = None) -> dict:
    """
    Full clinical Vaidya prescription enrichment.
    Passes Rasa-Guna-Virya-Vipaka + Vikriti + Agni + Ama + Season to LLM.
    Outputs structured Chikitsa Sutra, per-medicine rationale with classical basis,
    treatment protocol, Pathya/Apathya lists, Viruddha Ahara alerts, and red flags.
    """
    try:
        primary    = raw_plan.get("primary_formulations", [])
        supporting = raw_plan.get("supporting_formulations", [])
        all_forms  = primary + supporting
        if not all_forms:
            raw_plan["enriched"] = False
            return raw_plan

        # Build compressed pharmacology block for LLM — include all new schema fields
        pharma_data = []
        for m in all_forms:
            pharma_data.append({
                "name":          m["name"],
                "type":          m.get("type"),
                "rasa":          m.get("rasa", []),
                "guna":          m.get("guna", []),
                "virya":         m.get("virya", ""),
                "vipaka":        m.get("vipaka", ""),
                "karma":         m.get("karma", []),
                "dhatu_affected":m.get("dhatu_affected", []),
                "conditions":    m.get("conditions", [])[:4],
                "dosage":        m.get("dosage", ""),
                "selected_anupana": m.get("selected_anupana", m.get("anupana", "")),
                "classical_action": m.get("classical_action", ""),
                "afi_reference": m.get("afi_reference", ""),
                "classical_text_reference": m.get("classical_text_reference", ""),
            })

        # Build comprehensive profile block
        conditions_str    = ", ".join(raw_plan.get("active_conditions", []))
        current_meds_list = (
            (medicines_prefs or {}).get("current_allopathic_medications", []) +
            user_profile.get("current_medications", [])
        )
        current_meds_str = ", ".join(current_meds_list) if current_meds_list else "None"
        season = raw_plan.get("current_season", "") or user_profile.get("current_season", "")
        chikitsa = raw_plan.get("chikitsa_approach", "Shamana")
        agni     = raw_plan.get("agni_type", "sama")
        ama      = raw_plan.get("ama_level", "low")
        vikriti  = raw_plan.get("vikriti_dominant", raw_plan.get("user_dosha", "vata"))
        vikriti2 = raw_plan.get("vikriti_secondary", "")
        _agni_desc = {"sama": "balanced", "manda": "slow/sluggish", "tikshna": "sharp/intense", "vishama": "irregular/variable"}
        agni_label = _agni_desc.get(agni, agni)
        chikitsa_label = "purification" if chikitsa == "Shodhana" else "pacification"

        system_prompt = (
            "You are a senior Vaidya with M.D. (Ayu) and 20 years of clinical practice. "
            "You write precise Ayurvedic clinical prescriptions anchored in Charaka Samhita, "
            "Ashtanga Hridayam, Sharangadhara Samhita, and Bhaishajya Ratnavali. "
            "Output ONLY valid JSON. No markdown. No preamble."
        )

        prompt = f"""
A personalised Ayurvedic medicines plan has been generated. Write a complete clinical enrichment.

PATIENT PROFILE:
- Name context: Age {user_profile.get('age')}, Gender {user_profile.get('gender')}
- Vikriti (Imbalance): {vikriti.upper()} (primary), {vikriti2.upper() if vikriti2 else 'N/A'} (secondary)
- Prakriti (Constitution): {user_profile.get('dominant_dosha', 'vata').upper()}
- Agni (Digestive Fire): {agni} — {agni_label}
- Ama (Toxic load): {ama}
- Active Conditions: {conditions_str or 'General wellness'}
- Current Allopathic Medications: {current_meds_str}
- Allergies: {', '.join(user_profile.get('allergies') or []) or 'None known'}
- Season (Ritucharya): {season or 'Unknown'}
- Chikitsa Approach: {chikitsa} ({chikitsa_label})

FORMULATIONS PRESCRIBED (with full pharmacology):
{json.dumps(pharma_data, indent=2)}

Respond in EXACTLY this JSON format — every field is required:
{{
  "chikitsa_sutra": "2 sentences: overall treatment principle — which Dosha/Dhatu/Mala to address, Shamana or Shodhana approach, and why this combination was chosen for this Vikriti",
  "personalized_intro": "2–3 sentences in warm clinical Vaidya language — address the patient's Vikriti, Agni state, and primary conditions; make it feel individually crafted",
  "formulation_rationale": {{
    "Medicine Name": {{
      "rasa_guna_reasoning": "How the Rasa-Guna-Virya-Vipaka of this formulation corrects the patient's specific Vikriti. Cite the dominant Rasa and Karma that are most relevant.",
      "classical_basis": "Specific Samhita reference and the principle behind using this formulation for this condition — e.g., 'Charaka Chikitsa 6/15: Triphala is prescribed as Rasayana for all three Doshas...'",
      "anupana_reason": "Why the selected Anupana is appropriate for this patient's condition and Agni type"
    }}
  }},
  "synergy_note": "How these formulations work together across the Dosha-Dhatu-Mala framework. If only one formulation: how it addresses the whole Samprapti (disease pathway).",
  "expected_outcomes": {{
    "week_2": "First signs of improvement the patient should notice",
    "week_4": "Expected clinical milestones at one month",
    "week_8": "Full therapeutic response expected"
  }},
  "pathya": [
    "Specific food or habit to DO during this protocol — with brief Ayurvedic reason (5–8 items)"
  ],
  "apathya": [
    "Specific food or habit to AVOID during this protocol — with brief Ayurvedic reason (5–8 items)"
  ],
  "viruddha_ahara_alerts": [
    "Specific incompatible food combination to avoid WHILE ON THESE MEDICINES — classical reference if possible (include 2–4 items or empty array if none)"
  ],
  "dose_note": "Agni-specific dosing guidance — how to start, titrate, and maintain based on this patient's Agni type",
  "monitoring_signs": "What the patient should watch for — positive signs of improvement AND early warning signs that indicate the protocol needs adjustment",
  "when_to_stop": "Precise red flags that require immediately stopping all medicines and consulting a Vaidya or physician. Be clinically specific."
}}
"""

        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
        )

        enrichment = json.loads(response)
        if "error" in enrichment:
            raise ValueError(f"LLM provider error: {enrichment['error']}")

        # Merge enrichment into plan
        raw_plan["chikitsa_sutra"]       = enrichment.get("chikitsa_sutra", "")
        raw_plan["personalized_intro"]   = enrichment.get("personalized_intro", "")
        raw_plan["formulation_rationale"]= enrichment.get("formulation_rationale", {})
        raw_plan["synergy_note"]         = enrichment.get("synergy_note", "")
        raw_plan["expected_outcomes"]    = enrichment.get("expected_outcomes", {})
        raw_plan["pathya"]               = enrichment.get("pathya", [])
        raw_plan["apathya"]              = enrichment.get("apathya", [])
        raw_plan["viruddha_ahara_alerts"]= enrichment.get("viruddha_ahara_alerts", [])
        raw_plan["dose_note"]            = enrichment.get("dose_note", "")
        raw_plan["monitoring_signs"]     = enrichment.get("monitoring_signs", "")
        raw_plan["when_to_stop"]         = enrichment.get("when_to_stop", "")
        raw_plan["enriched"]             = True
        raw_plan["enrichment_model"]     = llm_client.provider
        return raw_plan

    except Exception as e:
        logger.error(f"Failed to enrich medicines plan: {e}")
        raw_plan["enriched"] = False
        raw_plan["enrichment_error"] = str(e)
        return raw_plan
