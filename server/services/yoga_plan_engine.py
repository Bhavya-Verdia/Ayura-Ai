import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSES_PATH = BASE_DIR / "data" / "knowledge_base" / "yoga_poses.json"
PRANAYAMA_PATH = BASE_DIR / "data" / "knowledge_base" / "pranayama.json"

yoga_poses = []
if POSES_PATH.exists():
    with open(POSES_PATH, "r", encoding="utf-8") as f:
        yoga_poses = json.load(f)

pranayama_list = []
if PRANAYAMA_PATH.exists():
    with open(PRANAYAMA_PATH, "r", encoding="utf-8") as f:
        pranayama_list = json.load(f)

def filter_poses(user_profile, yoga_prefs, yoga_poses):
    scored_poses = []
    
    # a) Level filter (hard)
    level_map = {
        "beginner": ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced": ["beginner", "intermediate", "advanced"]
    }
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none": user_exp = "beginner"
    allowed_levels = level_map.get(user_exp, ["beginner"])
    
    # b) Pregnancy filter (hard)
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    
    # c) Injury / contraindication filter
    user_injuries = set(user_profile.get("injuries_or_limitations", []))
    mapped_injuries = set()
    for inj in user_injuries:
        i = inj.lower()
        if "bad_knee" in i or "knee" in i: mapped_injuries.update(["knee_injury", "knee_replacement"])
        if "lower_back" in i or "back" in i: mapped_injuries.update(["lower_back_pain", "herniated_disc"])
        if "shoulder" in i: mapped_injuries.update(["shoulder_injury", "rotator_cuff"])
        if "neck" in i: mapped_injuries.update(["neck_injury", "cervical_spondylosis"])
        if "hypertension" in i or "blood pressure" in i: mapped_injuries.update(["high_blood_pressure", "hypertension"])
        if "heart" in i: mapped_injuries.update(["heart_disease"])
        if "glaucoma" in i: mapped_injuries.update(["glaucoma"])
        
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    yoga_goal = yoga_prefs.get("yoga_goal", "flexibility")
    
    for pose in yoga_poses:
        # a
        if pose.get("level", "intermediate") not in allowed_levels:
            continue
            
        # b
        if is_pregnant and not pose.get("pregnancy_safe", True):
            continue
            
        # c
        pose_contra = set(pose.get("contraindications", []))
        if mapped_injuries.intersection(pose_contra):
            continue
            
        score = 0
        
        # d) Dosha scoring
        db = pose.get("dosha_balance", {})
        d_val = db.get(dominant_dosha, "neutral")
        if d_val == "balances": score += 2
        elif d_val == "neutral": score += 1
        elif d_val == "aggravates": score -= 1
        
        # e) Goal filter
        if yoga_goal in pose.get("goals", []):
            score += 2
            
        # Ensure Savasana is always in the pool
        if pose.get("english_name") == "Corpse Pose":
            score += 100
        if "supta" in pose.get("sanskrit_name", "").lower():
            score += 50
            
        scored_poses.append((score, pose))
        
    scored_poses.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored_poses[:80]]

def select_pranayama(user_profile, yoga_prefs, pranayama_list, count=3):
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none": user_exp = "beginner"
    
    level_map = {
        "beginner": ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced": ["beginner", "intermediate", "advanced"]
    }
    allowed_levels = level_map.get(user_exp, ["beginner"])
    
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    yoga_goal = yoga_prefs.get("yoga_goal", "stress_relief")
    
    scored_pranayama = []
    
    for pr in pranayama_list:
        if is_pregnant and not pr.get("pregnancy_safe", True):
            continue
        if pr.get("level", "beginner") not in allowed_levels:
            continue
            
        score = 0
        de = pr.get("dosha_effect", {}).get(dominant_dosha, "neutral")
        if de == "balances": score += 2
        elif de == "neutral": score += 1
        elif de == "aggravates": score -= 2
        
        ptype = pr.get("type", "balancing")
        if yoga_goal == "stress_relief" and ptype in ["balancing", "grounding"]: score += 2
        if yoga_goal in ["energy", "strength"] and ptype == "energizing": score += 2
        if yoga_goal == "healing" and ptype == "balancing": score += 2
        if yoga_goal == "flexibility" and ptype == "grounding": score += 1
        if yoga_goal == "spiritual" and ptype == "balancing": score += 2
        
        scored_pranayama.append((score, pr))
        
    scored_pranayama.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored_pranayama[:count]]

def build_sequence(filtered_poses, yoga_prefs, user_profile, used_pose_counts=None):
    if used_pose_counts is None:
        used_pose_counts = {}
        
    mins = yoga_prefs.get("time_available_minutes", 30)
    if mins <= 15: counts = (2, 2, 1)
    elif mins <= 20: counts = (2, 3, 2)
    elif mins <= 30: counts = (3, 5, 2)
    elif mins <= 45: counts = (3, 8, 3)
    else: counts = (4, 10, 4)
    
    w_count, m_count, c_count = counts
    
    # Filter out poses used >= 3 times
    available_poses = [p for p in filtered_poses if used_pose_counts.get(p["id"], 0) < 3]
    if len(available_poses) < sum(counts):
        available_poses = filtered_poses # fallback if we exhaust pool
        
    warmup_pool = [p for p in available_poses if p.get("sequence_role") == "warmup" or (p.get("category") in ["standing", "seated"] and p.get("level") == "beginner")]
    main_pool = [p for p in available_poses if p.get("sequence_role") == "main"]
    
    styles = yoga_prefs.get("yoga_style_preference", ["hatha"])
    style = styles[0] if styles else "hatha"
    
    style_main_pool = []
    for p in main_pool:
        cat = p.get("category")
        if style == "hatha": style_main_pool.append(p)
        elif style == "vinyasa" and cat in ["standing", "balancing"]: style_main_pool.append(p)
        elif style == "restorative" and cat in ["restorative", "supine"]: style_main_pool.append(p)
        elif style == "yin" and cat in ["forward_fold", "supine", "seated"]: style_main_pool.append(p)
        elif style == "power" and cat in ["standing", "inversion", "backbend"]: style_main_pool.append(p)
        elif style == "ashtanga" and cat in ["standing", "balancing", "inversion"]: style_main_pool.append(p)
        else: style_main_pool.append(p) # fallback
        
    if len(style_main_pool) < m_count:
        style_main_pool = main_pool
        
    cooldown_pool = [p for p in available_poses if p.get("sequence_role") == "cooldown" or p.get("category") in ["supine", "forward_fold", "restorative"]]
    
    random.shuffle(warmup_pool)
    random.shuffle(style_main_pool)
    random.shuffle(cooldown_pool)
    
    # Warmup selection
    grounding = [p for p in warmup_pool if p["english_name"] in ["Mountain Pose", "Easy Pose", "Child's Pose"]]
    warmup = []
    if grounding:
        warmup.append(grounding[0])
        used_pose_counts[grounding[0]["id"]] = used_pose_counts.get(grounding[0]["id"], 0) + 1
        warmup_pool = [p for p in warmup_pool if p["id"] != grounding[0]["id"]]
        
    for p in warmup_pool:
        if len(warmup) >= w_count: break
        warmup.append(p)
        used_pose_counts[p["id"]] = used_pose_counts.get(p["id"], 0) + 1
        
    # Main selection
    main_seq = []
    for p in style_main_pool:
        if len(main_seq) >= m_count: break
        if p["id"] not in [x["id"] for x in warmup]:
            main_seq.append(p)
            used_pose_counts[p["id"]] = used_pose_counts.get(p["id"], 0) + 1
            
    # Cooldown selection
    savasana = [p for p in available_poses if p["english_name"] == "Corpse Pose"]
    supta = [p for p in available_poses if "supta" in p["sanskrit_name"].lower()]
    
    cooldown = []
    # Pick a forward fold or supine twist for first cooldown
    first_cd = [p for p in cooldown_pool if p.get("category") in ["forward_fold", "twist", "supine"]]
    if first_cd:
        cooldown.append(first_cd[0])
        used_pose_counts[first_cd[0]["id"]] = used_pose_counts.get(first_cd[0]["id"], 0) + 1
        cooldown_pool = [p for p in cooldown_pool if p["id"] != first_cd[0]["id"]]
        
    for p in cooldown_pool:
        if len(cooldown) >= c_count - 1: break # save last spot for Savasana
        cooldown.append(p)
        used_pose_counts[p["id"]] = used_pose_counts.get(p["id"], 0) + 1
        
    if savasana:
        cooldown.append(savasana[0])
        used_pose_counts[savasana[0]["id"]] = used_pose_counts.get(savasana[0]["id"], 0) + 1
    elif supta:
        cooldown.append(supta[0])
        used_pose_counts[supta[0]["id"]] = used_pose_counts.get(supta[0]["id"], 0) + 1
        
    return {
        "warmup": warmup,
        "main": main_seq,
        "cooldown": cooldown
    }

def format_pose(pose, exp):
    durs = pose.get("duration_seconds", {})
    return {
        "pose_id": pose.get("id"),
        "pose_name": pose.get("english_name"),
        "sanskrit_name": pose.get("sanskrit_name"),
        "duration_seconds": durs.get(exp, durs.get("beginner", 30)),
        "instructions": " ".join(pose.get("instructions", [])),
        "modification": "Use props if needed.",
        "pranayama_sync": pose.get("pranayama_sync", "Breathe steadily")
    }

def build_yoga_day(sequence, pranayama, yoga_prefs, user_profile):
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none": exp = "beginner"
    
    warmup_fmt = [format_pose(p, exp) for p in sequence["warmup"]]
    main_fmt = [format_pose(p, exp) for p in sequence["main"]]
    cooldown_fmt = [format_pose(p, exp) for p in sequence["cooldown"]]
    
    pranayama_section = []
    for pr in pranayama:
        durs = pr.get("duration_minutes", {})
        pranayama_section.append({
            "technique_id": pr.get("id"),
            "technique_name": pr.get("english_name"),
            "sanskrit_name": pr.get("sanskrit_name"),
            "duration_minutes": durs.get(exp, durs.get("beginner", 3)),
            "instructions": pr.get("instructions", []),
            "dosha_note": f"Balances your {user_profile.get('dominant_dosha', 'vata')} energy."
        })
        
    dosha = user_profile.get("dominant_dosha", "vata")
    goal = yoga_prefs.get("yoga_goal", "flexibility").replace("_", " ")
    if dosha == "vata": theme = f"Grounding & Warming {goal.title()} Practice"
    elif dosha == "pitta": theme = f"Cooling & Calming {goal.title()} Flow"
    else: theme = f"Energizing & Invigorating {goal.title()} Sequence"
    
    return {
        "warmup": warmup_fmt,
        "main_sequence": main_fmt,
        "cooldown": cooldown_fmt,
        "pranayama_section": pranayama_section,
        "total_duration_minutes": yoga_prefs.get("time_available_minutes", 30),
        "sequence_type": yoga_prefs.get("time_of_day_preference", "morning"),
        "dosha_theme": theme
    }

def get_ayurvedic_tips(dosha):
    if dosha == "pitta":
        return {
            "best_time": "Early morning 6-8am or evening after 6pm. Avoid midday.",
            "environment": "Cool, well-ventilated space. Natural light preferred.",
            "what_to_wear": "Light, breathable fabric. Avoid synthetic materials.",
            "after_practice": "Cool water or coconut water. Avoid hot shower immediately."
        }
    elif dosha == "kapha":
        return {
            "best_time": "6-8am. Practice during Kapha time to counteract morning heaviness.",
            "environment": "Bright, well-lit, open space. Uplifting music if desired.",
            "what_to_wear": "Fitted clothes that allow full movement.",
            "after_practice": "Kapalabhati pranayama for 2 mins. Ginger tea."
        }
    else:
        return {
            "best_time": "10am-2pm or early evening. Avoid pre-dawn practice.",
            "environment": "Warm, quiet, dimly lit room. Use blankets and bolsters freely.",
            "what_to_wear": "Warm, comfortable layers. Keep yourself warm throughout.",
            "after_practice": "Rest in Savasana minimum 10 minutes. Warm herbal tea."
        }

def generate_yoga_plan(user_profile, yoga_prefs, yoga_poses_db=None, pranayama_list_db=None):
    yp = yoga_poses_db if yoga_poses_db is not None else yoga_poses
    pl = pranayama_list_db if pranayama_list_db is not None else pranayama_list
    filtered_poses = filter_poses(user_profile, yoga_prefs, yp)
    pranayamas = select_pranayama(user_profile, yoga_prefs, pl, count=3)
    
    time_of_day = yoga_prefs.get("time_of_day_preference", "morning")
    if time_of_day == "morning": rest_days = [3, 7] # Wed, Sun
    elif time_of_day == "evening": rest_days = [4, 7] # Thu, Sun
    else: rest_days = [7] # Sun only
    
    used_pose_counts = {}
    weekly_schedule = []
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for i in range(1, 8):
        if i in rest_days:
            weekly_schedule.append({
                "day": i,
                "day_name": days_of_week[i-1],
                "session": None,
                "rest": True
            })
        else:
            seq = build_sequence(filtered_poses, yoga_prefs, user_profile, used_pose_counts)
            # Pick 1 random pranayama from the 3 for the day
            day_pranayama = [random.choice(pranayamas)] if pranayamas else []
            day_plan = build_yoga_day(seq, day_pranayama, yoga_prefs, user_profile)
            
            weekly_schedule.append({
                "day": i,
                "day_name": days_of_week[i-1],
                "session": day_plan,
                "rest": False
            })
            
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    disclaimer = "This plan is for general wellness guidance only. Please consult a physician before beginning any new exercise program."
    if is_pregnant:
        disclaimer = "PREGNANCY WARNING: Several poses have been removed for pregnancy safety. Please consult your doctor before practice."
        
    return {
        "plan_id": f"yoga_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": user_profile.get("dominant_dosha", "vata"),
            "yoga_goal": yoga_prefs.get("yoga_goal", "flexibility"),
            "experience": yoga_prefs.get("yoga_experience", "beginner"),
            "style_preference": yoga_prefs.get("yoga_style_preference", ["hatha"]),
            "time_available": yoga_prefs.get("time_available_minutes", 30),
            "time_of_day": time_of_day
        },
        "weekly_schedule": weekly_schedule,
        "ayurvedic_tips": get_ayurvedic_tips(user_profile.get("dominant_dosha", "vata")),
        "disclaimer": disclaimer,
        "enriched": False
    }
