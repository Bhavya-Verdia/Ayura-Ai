import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
THERAPIES_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_therapies.json"

pk_therapies = []
if THERAPIES_PATH.exists():
    with open(THERAPIES_PATH, "r", encoding="utf-8") as f:
        pk_therapies = json.load(f)

def filter_and_score_therapies(user_profile, pk_prefs, phase, pk_therapies):
    scored = []
    
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    setting = pk_prefs.get("setting", "home")
    experience = pk_prefs.get("detox_experience", "none")
    herbs = pk_prefs.get("access_to_ayurvedic_herbs", "willing_to_buy")
    diet_ability = pk_prefs.get("diet_adherence_ability", "partial")
    self_care_time = pk_prefs.get("self_care_time_per_day", "30 min")
    
    if "15" in self_care_time: max_dur = 15
    elif "30" in self_care_time: max_dur = 30
    elif "1" in self_care_time: max_dur = 60
    else: max_dur = 120
    
    for t in pk_therapies:
        if t["phase"] != phase:
            continue
            
        # Hard filters
        if setting == "home" and "home" not in t["setting_required"]:
            continue
        if setting == "clinic" and "clinic" not in t["setting_required"]:
            continue
            
        if experience == "none" and t["experience_required"] in ["some", "experienced"]:
            continue
        if experience == "some" and t["experience_required"] == "experienced":
            continue
            
        if herbs == "no" and t["herb_requirement"] == "specific_ayurvedic":
            continue
            
        if diet_ability == "lifestyle_only" and t["diet_strictness"] in ["strict", "partial"]:
            continue
        if diet_ability == "partial" and t["diet_strictness"] == "strict":
            continue
            
        if t["duration_minutes"] > max_dur and setting != "clinic":
            # For clinic we ignore user's self_care_time
            continue
            
        score = 0
        
        # Dosha effect
        de = t.get("dosha_effect", {}).get(dominant_dosha, 0)
        if de == -1: score += 2
        elif de == 0: score += 1
        elif de == 1: score -= 2 # Heavily penalize aggravating therapies in PK
        
        scored.append((score, t))
        
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for s, t in scored]

def assemble_phase(pool, target_days, start_day, phase_name):
    # In a real clinical setting, therapies are repeated. 
    # For a digital plan, we pick the top 1 or 2 therapies and assign them daily for this phase.
    if not pool:
        return [] # Fallback
        
    primary = pool[0]
    secondary = pool[1] if len(pool) > 1 else None
    
    schedule = []
    for i in range(target_days):
        day_therapies = [{"id": primary["id"], "name": primary["name"], "duration_minutes": primary["duration_minutes"], "benefits": primary["benefits"]}]
        if secondary and (i % 2 == 0 or len(pool) == 2):
            day_therapies.append({"id": secondary["id"], "name": secondary["name"], "duration_minutes": secondary["duration_minutes"], "benefits": secondary["benefits"]})
            
        schedule.append({
            "day": start_day + i,
            "phase": phase_name,
            "therapies": day_therapies
        })
    return schedule

def generate_panchakarma_plan(user_profile, pk_prefs, pk_therapies_db=None):
    total_days = pk_prefs.get("available_time_days", 7)
    
    # Phase splitting
    prep_days = max(1, int(total_days * 0.3))
    post_days = max(1, int(total_days * 0.4))
    main_days = total_days - prep_days - post_days
    if main_days <= 0:
        main_days = 1
        post_days = total_days - prep_days - main_days
        
    pkt = pk_therapies_db if pk_therapies_db is not None else pk_therapies
    purva_pool = filter_and_score_therapies(user_profile, pk_prefs, "purvakarma", pkt)
    pradhana_pool = filter_and_score_therapies(user_profile, pk_prefs, "pradhana", pkt)
    paschat_pool = filter_and_score_therapies(user_profile, pk_prefs, "paschat", pkt)
    
    schedule = []
    
    # Assembly
    schedule.extend(assemble_phase(purva_pool, prep_days, 1, "Purvakarma (Preparation)"))
    schedule.extend(assemble_phase(pradhana_pool, main_days, 1 + prep_days, "Pradhana Karma (Main Cleanse)"))
    schedule.extend(assemble_phase(paschat_pool, post_days, 1 + prep_days + main_days, "Paschat Karma (Rejuvenation)"))
    
    setting = pk_prefs.get("setting", "home")
    disclaimer = "This plan is for educational purposes. True Panchakarma must be supervised by an Ayurvedic doctor."
    if setting == "home":
        disclaimer = "HOME DETOX WARNING: This plan is severely restricted to mild home practices. Do not attempt deep purgation or emesis without a clinical setting."
        
    return {
        "plan_id": f"pk_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": user_profile.get("dominant_dosha", "vata"),
            "setting": setting,
            "experience": pk_prefs.get("detox_experience", "none"),
            "duration_days": total_days
        },
        "phase_breakdown": {
            "purvakarma_days": prep_days,
            "pradhana_karma_days": main_days,
            "paschat_karma_days": post_days
        },
        "daily_schedule": schedule,
        "disclaimer": disclaimer,
        "enriched": False
    }
