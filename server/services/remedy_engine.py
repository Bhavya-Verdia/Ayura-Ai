from datetime import datetime, timezone
from core.kb_cache import kb_cache

def filter_remedies(user_profile: dict, symptom_input: dict) -> list:
    filtered_results = []
    
    symptoms = symptom_input.get("symptoms", [])
    severity = symptom_input.get("severity", {})
    duration = symptom_input.get("duration", {})
    
    pregnancy_or_nursing = user_profile.get("pregnancy_or_nursing", False)
    current_meds = user_profile.get("current_medications", [])
    medical_history = user_profile.get("medical_history", [])
    allergies = user_profile.get("allergies", [])
    dominant_dosha = user_profile.get("dominant_dosha", "vata").lower()
    secondary_dosha = user_profile.get("secondary_dosha", "pitta").lower()
    
    all_remedies = kb_cache.ayurvedic_remedies
    
    for sym_id in symptoms:
        sym_sev = severity.get(sym_id, "mild")
        sym_dur = duration.get(sym_id, "recent")
        
        # a) Severity gate
        if sym_sev == "severe":
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "see_doctor",
                "message": "This symptom requires immediate medical attention. Please consult a doctor."
            })
            continue
            
        # Find remedy in KB
        remedy_kb = next((r for r in all_remedies if r.get("symptom_id") == sym_id), None)
        if not remedy_kb:
            continue
            
        # b) Duration gate
        requires_practitioner = (sym_dur in ["chronic", "months"])
        
        # c) Pregnancy filter
        if pregnancy_or_nursing and not remedy_kb.get("pregnancy_safe", False):
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "consult_doctor",
                "message": "Safe remedy not available during pregnancy. Please consult your Ayurvedic practitioner."
            })
            continue
            
        # dosha selection helper
        def is_safe(cand_remedy):
            if not cand_remedy: 
                return False, None
            
            # Extract text to search for ingredients
            ingredients_list = cand_remedy.get("ingredients", [])
            ingredients_text = " ".join([i.get("item", "").lower() for i in ingredients_list])
            
            # e) Medical contraindication
            blocks = {
                "diabetes": ["guggulu", "honey"],
                "hypertension": ["salt", "ajwain", "stimulant"],
                "thyroid": ["ashwagandha"],
                "ibs": ["pippali", "trikatu"]
            }
            
            for cond in medical_history:
                cond_l = cond.lower()
                for key, blocked_items in blocks.items():
                    if key in cond_l:
                        for item in blocked_items:
                            if item in ingredients_text:
                                if key == "thyroid" and item == "ashwagandha":
                                    cand_remedy["caution_note"] = "Use Ashwagandha with caution due to thyroid history."
                                else:
                                    return False, f"Contraindicated for {cond}"
            
            # d) Drug interaction
            drug_interaction_map = {
                "ashwagandha": ["thyroid_medication", "immunosuppressants"],
                "guggulu": ["blood_thinners", "thyroid_medication"],
                "triphala": ["blood_thinners", "diabetes_medication"],
                "ginger": ["blood_thinners", "diabetes_medication"],
                "neem": ["diabetes_medication", "immunosuppressants"],
                "fenugreek": ["diabetes_medication", "blood_thinners"],
                "aloe_vera": ["diabetes_medication", "blood_thinners"],
                "tulsi": ["blood_thinners"]
            }
            
            for med in current_meds:
                med_l = med.lower().replace(" ", "_")
                for herb, interactions in drug_interaction_map.items():
                    if herb in ingredients_text:
                        for interaction in interactions:
                            if interaction in med_l:
                                return False, {"interaction_found": True, "medication": med, "herb": herb}
            
            # f) Allergy filter
            for allergy in allergies:
                if allergy.lower() in ingredients_text:
                    return False, f"Allergen {allergy} found"
                    
            return True, None

        selected_remedy = None
        dosha_used = dominant_dosha
        candidate = remedy_kb.get("remedies", {}).get(dominant_dosha)
        
        interaction_warning = None
        
        safe, reason = is_safe(candidate)
        if not safe:
            if isinstance(reason, dict) and reason.get("interaction_found"):
                interaction_warning = reason
            dosha_used = secondary_dosha
            candidate = remedy_kb.get("remedies", {}).get(secondary_dosha)
            safe, reason = is_safe(candidate)
            if not safe:
                if isinstance(reason, dict) and reason.get("interaction_found"):
                    interaction_warning = reason
                candidate = remedy_kb.get("universal_remedy")
                dosha_used = "universal"
                safe, reason = is_safe(candidate)
                if not safe:
                    msg = {"symptom_id": sym_id, "action": "consult_doctor", "message": "No safe remedy available due to interactions/allergies."}
                    if isinstance(reason, dict):
                        msg.update(reason)
                    elif interaction_warning:
                        msg.update(interaction_warning)
                    filtered_results.append(msg)
                    continue
                    
        selected_remedy = candidate
        if not selected_remedy:
            continue
            
        # Build result for this symptom
        filtered_results.append({
            "symptom_id": sym_id,
            "symptom_display": remedy_kb.get("symptom_display", sym_id),
            "severity": sym_sev,
            "duration": sym_dur,
            "dosha_cause": remedy_kb.get("dosha_cause", {}).get(dosha_used, ""),
            "remedy": selected_remedy,
            "requires_practitioner": requires_practitioner,
            "drug_interaction_warning": interaction_warning,
            "source": remedy_kb.get("source", "Traditional"),
            "dosha_used": dosha_used
        })
        
    return filtered_results

def build_remedy_plan(filtered_remedies: list, user_profile: dict, symptom_input: dict) -> dict:
    plan_id = f"remedy_{user_profile.get('id', 'usr')}_{int(datetime.now(timezone.utc).timestamp())}"
    dominant_dosha = user_profile.get("dominant_dosha", "vata").lower()
    
    symptoms_addressed = []
    doctor_referrals = []
    
    for res in filtered_remedies:
        if res.get("action") in ["see_doctor", "consult_doctor"]:
            doctor_referrals.append(res)
        else:
            symptoms_addressed.append(res)
            
    guidelines = {}
    if dominant_dosha == "vata":
        guidelines = {
            "diet_during_recovery": "Warm, cooked, oily foods. Avoid cold, raw, dry foods during recovery.",
            "lifestyle_notes": "Rest adequately. Maintain regular meal and sleep times.",
            "what_to_avoid": ["cold drinks", "raw salads", "skipping meals", "late nights"]
        }
    elif dominant_dosha == "pitta":
        guidelines = {
            "diet_during_recovery": "Cooling foods — coconut water, cucumber, sweet fruits. Avoid spicy and fermented foods.",
            "lifestyle_notes": "Avoid overheating. Rest in cool environment.",
            "what_to_avoid": ["spicy food", "alcohol", "excess sun", "competitive stress"]
        }
    else:
        guidelines = {
            "diet_during_recovery": "Light, warm, spiced foods. Avoid heavy, sweet, oily foods.",
            "lifestyle_notes": "Stay active. Avoid daytime sleep.",
            "what_to_avoid": ["cold dairy", "fried food", "excess sugar", "sedentary behavior"]
        }

    return {
        "plan_id": plan_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_dosha": dominant_dosha,
        "symptoms_addressed": symptoms_addressed,
        "doctor_referrals": doctor_referrals,
        "general_guidelines": guidelines,
        "ayurvedic_context": "",
        "follow_up": "If symptoms persist beyond 7 days, consult an Ayurvedic practitioner",
        "disclaimer": "These are traditional home remedies for general wellness only. They are not a substitute for medical treatment. Consult a qualified healthcare provider for persistent, severe, or worsening symptoms.",
        "enriched": False
    }
