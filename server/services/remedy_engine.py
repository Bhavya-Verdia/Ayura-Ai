import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REMEDIES_PATH = BASE_DIR / "data" / "knowledge_base" / "ayurvedic_remedies.json"

all_remedies = []
if REMEDIES_PATH.exists():
    with open(REMEDIES_PATH, "r", encoding="utf-8") as f:
        all_remedies = json.load(f)

def generate_remedies_plan(user_profile, rem_prefs, target_type, ayurvedic_remedies_db=None):
    """
    target_type is either "home_remedy" or "clinical_medicine"
    """
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    
    symptoms = rem_prefs.get("symptom_severity", {})
    if not symptoms:
        symptoms = {}
    
    ingredient_access = rem_prefs.get("ingredient_access", "kitchen_only")
    taste_prefs = rem_prefs.get("preference_taste_smell", [])
    
    scored = []
    
    ar = ayurvedic_remedies_db if ayurvedic_remedies_db is not None else all_remedies
    for r in ar:
        # 1. Type filter
        if r["type"] != target_type:
            continue
            
        # 2. Pregnancy filter
        if is_pregnant and not r["pregnancy_safe"]:
            continue
            
        # 3. Access filter
        if ingredient_access == "kitchen_only" and r["ingredient_access_required"] == "can_buy_herbs":
            continue
            
        # 4. Taste filter
        bad_taste = False
        if "no_bitter" in taste_prefs and "bitter" in r["taste_profile"]:
            bad_taste = True
        if "no_pungent" in taste_prefs and "pungent" in r["taste_profile"]:
            bad_taste = True
        if bad_taste and target_type == "home_remedy":
            continue # Try to honor taste for home remedies. For clinical meds, medicine is medicine.
            
        score = 0
        
        # 5. Symptom Keyword Matching
        matched_symptoms = []
        for sym_name, severity in symptoms.items():
            sym_clean = sym_name.lower().replace(" ", "_")
            # Partial match (e.g. "headache" matches "headache")
            if any(sym_clean in ind for ind in r["indications"]) or any(ind in sym_clean for ind in r["indications"]):
                points = 5
                if severity == "severe": points = 10
                elif severity == "mild": points = 3
                score += points
                matched_symptoms.append(sym_name)
                
        # 6. Dosha Scoring
        de = r.get("dosha_effect", {}).get(dominant_dosha, 0)
        if de == -1: score += 2
        elif de == 0: score += 1
        elif de == 1: score -= 3 # Don't give heating things to Pitta
        
        # We only want to recommend remedies that actually treat the user's symptoms
        if score > 0 and len(matched_symptoms) > 0:
            scored.append({
                "score": score,
                "remedy": r,
                "matched_symptoms": matched_symptoms
            })
            
    # Sort and pick top 3
    scored.sort(key=lambda x: x["score"], reverse=True)
    selected = scored[:3]
    
    plan_therapies = []
    for s in selected:
        rem = s["remedy"]
        plan_therapies.append({
            "id": rem["id"],
            "name": rem["name"],
            "preparation_method": rem["preparation_method"],
            "taste_profile": rem["taste_profile"],
            "targeted_symptoms": s["matched_symptoms"]
        })
        
    disclaimer = "This information is for educational purposes. Consult a physician before starting any herbal medicine."
    if is_pregnant:
        disclaimer = "PREGNANCY WARNING: Only safe, mild remedies have been shown. Still, consult your doctor."
        
    return {
        "plan_id": f"{target_type}_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "pregnant": is_pregnant,
            "reported_symptoms": list(symptoms.keys())
        },
        "type": target_type,
        "selected_remedies": plan_therapies,
        "disclaimer": disclaimer,
        "enriched": False
    }
