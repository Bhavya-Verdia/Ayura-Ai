import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Load exercises into memory
BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_PATH = BASE_DIR / "data" / "knowledge_base" / "gym_exercises.json"

gym_exercises = []
if EXERCISES_PATH.exists():
    with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
        gym_exercises = json.load(f)

def filter_exercises(user_profile, gym_prefs, gym_exercises):
    available_eq = set([eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])])
    if "bodyweight" not in available_eq:
        available_eq.add("bodyweight")
        
    scored_exercises = []
    
    level_map = {
        "beginner": ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced": ["beginner", "intermediate", "advanced"]
    }
    user_level = user_profile.get("fitness_level", "beginner") or "beginner"
    allowed_levels = level_map.get(user_level, ["beginner"])
    
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    gym_goal = gym_prefs.get("gym_goal", "general_fitness")
    injuries = set(user_profile.get("injuries_or_limitations") or [])
    
    for ex in gym_exercises:
        # a) Equipment filter
        ex_eq = ex.get("equipment", "bodyweight").lower()
        if ex_eq not in available_eq and ex_eq != "bodyweight":
            continue
            
        # b) Level filter
        if ex.get("level", "intermediate") not in allowed_levels:
            continue
            
        # d) Goal filter
        if not ex.get("goal_suitability", {}).get(gym_goal, False):
            continue
            
        # e) Contraindication filter (HARD filter)
        ex_contra = set(ex.get("contraindications", []))
        if injuries.intersection(ex_contra):
            continue
            
        # e2) Pregnancy filter (HARD filter)
        is_pregnant = user_profile.get("pregnancy_or_nursing", False)
        if is_pregnant:
            cat = ex.get("category", "").lower()
            ex_name = ex.get("name", "").lower()
            if cat in ["plyometrics", "strongman"] or "jump" in ex_name or "plyo" in ex_name or "box" in ex_name:
                continue
            
        # c) Dosha score (Soft filter)
        score = 0
        dosha_suit = ex.get("dosha_suitability", {}).get(dominant_dosha, "moderate")
        if dosha_suit == "good":
            score += 2
        elif dosha_suit == "moderate":
            score += 1
        elif dosha_suit == "avoid":
            score -= 2
            
        scored_exercises.append((score, ex))
        
    # f) Sort by dosha score descending, return top 200
    scored_exercises.sort(key=lambda x: x[0], reverse=True)
    return [ex for score, ex in scored_exercises[:200]]


def split_by_muscle_group(exercises):
    split = {
        "chest": [],
        "triceps": [],
        "biceps": [],
        "back": [],
        "shoulders": [],
        "legs": [],
        "core": [],
        "full_body": [],
        "cardio": []
    }
    
    for ex in exercises:
        if ex.get("category") == "cardio":
            split["cardio"].append(ex)
            continue
            
        primary = [m.lower() for m in ex.get("primary_muscles", [])]
        
        assigned = False
        for m in primary:
            if "chest" in m or "pectoral" in m:
                split["chest"].append(ex)
                assigned = True
            elif "triceps" in m:
                split["triceps"].append(ex)
                assigned = True
            elif "biceps" in m:
                split["biceps"].append(ex)
                assigned = True
            elif m in ["lats", "middle back", "lower back", "traps", "back"]:
                split["back"].append(ex)
                assigned = True
            elif "shoulder" in m or "deltoid" in m:
                split["shoulders"].append(ex)
                assigned = True
            elif m in ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors", "legs", "quad", "calf"]:
                split["legs"].append(ex)
                assigned = True
            elif "abdominal" in m or "core" in m or "abs" in m:
                split["core"].append(ex)
                assigned = True
                
        if not assigned:
            split["full_body"].append(ex)
            
    return split


def build_weekly_schedule(workout_days):
    if workout_days == 2:
        return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
    elif workout_days == 3:
        return ["push", "rest", "pull", "rest", "legs_core", "rest", "rest"]
    elif workout_days == 4:
        return ["chest_triceps", "rest", "back_biceps", "legs", "rest", "shoulders_core", "rest"]
    elif workout_days == 5:
        return ["chest", "back", "rest", "legs", "shoulders_arms", "core_cardio", "rest"]
    elif workout_days == 6:
        return ["chest_triceps", "back_biceps", "legs", "shoulders", "arms", "core_cardio", "rest"]
    else:
        return ["full_body", "full_body", "full_body", "rest", "rest", "rest", "rest"]


def build_day_plan(day_num, day_name, focus, muscle_split, gym_prefs, user_profile):
    if focus == "rest":
        return {
            "day": day_num,
            "day_name": day_name,
            "focus": "Rest & Recovery",
            "type": "recovery",
            "warmup": [],
            "main_workout": [],
            "cooldown": [],
            "estimated_duration_minutes": 0,
            "calories_burned_estimate": 0
        }
        
    duration = gym_prefs.get("workout_duration_minutes", 45)
    
    if duration <= 20: target_ex_count = 3
    elif duration <= 30: target_ex_count = 4
    elif duration <= 45: target_ex_count = 6
    elif duration <= 60: target_ex_count = 8
    else: target_ex_count = 10
    
    # Map focus to keys
    focus_keys = []
    if "full_body" in focus: focus_keys = ["full_body", "chest", "back", "legs", "core"]
    elif "push" in focus: focus_keys = ["chest", "shoulders", "triceps"]
    elif "pull" in focus: focus_keys = ["back", "biceps"]
    elif "legs" in focus: focus_keys = ["legs"]
    elif "chest_triceps" in focus: focus_keys = ["chest", "triceps"]
    elif "back_biceps" in focus: focus_keys = ["back", "biceps"]
    elif "chest" == focus: focus_keys = ["chest"]
    elif "back" == focus: focus_keys = ["back"]
    elif "shoulders" in focus: focus_keys = ["shoulders"]
    elif "arms" in focus: focus_keys = ["biceps", "triceps"]
    elif "core" in focus: focus_keys = ["core", "cardio"]
    
    pool = []
    for k in focus_keys:
        if k in muscle_split:
            pool.extend(muscle_split[k])
            
    # Deduplicate and shuffle
    unique_pool = {ex["id"]: ex for ex in pool}.values()
    pool = list(unique_pool)
    random.shuffle(pool)
    
    selected = pool[:target_ex_count]
    
    # Form workout array
    main_workout = []
    total_cals = 0
    level = user_profile.get("fitness_level", "beginner") or "beginner"
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"
        
    for ex in selected:
        sr = ex.get("sets_reps", {}).get(level, {"sets": 3, "reps": "10-12", "rest_seconds": 90})
        
        # Estimate cals
        reps_str = str(sr.get("reps", "10"))
        try:
            parts = reps_str.split("-")
            reps = sum(map(int, parts)) / len(parts)
        except:
            reps = 10
            
        cat = ex.get("category", "strength").lower()
        if cat == "strength":
            time_per_rep = 4
        elif cat == "cardio":
            time_per_rep = 2
        elif cat == "stretching":
            time_per_rep = 10
        else:
            time_per_rep = 4
            
        cpm = ex.get("calories_per_minute", 5.0)
        exercise_mins = (sr.get("sets", 3) * reps * time_per_rep) / 60.0
        total_cals += exercise_mins * cpm
        
        main_workout.append({
            "exercise_id": ex.get("id"),
            "exercise_name": ex.get("name"),
            "sets": sr.get("sets", 3),
            "reps": sr.get("reps", "10-12"),
            "rest_seconds": sr.get("rest_seconds", 90),
            "notes": ex.get("modification", "")
        })
        
    return {
        "day": day_num,
        "day_name": day_name,
        "focus": focus.replace("_", " ").title(),
        "type": "strength" if "cardio" not in focus else "cardio",
        "warmup": ["Arm circles", "High knees", "Dynamic stretches"],
        "main_workout": main_workout,
        "cooldown": ["Child's pose", "Hamstring stretch", "Deep breathing"],
        "estimated_duration_minutes": duration,
        "calories_burned_estimate": int(total_cals + 15 + 5) # +15 warmup, +5 cooldown
    }

def get_ayurvedic_tips(dosha):
    if dosha == "pitta":
        return {
            "best_time_to_workout": "Early morning or evening (avoid midday heat)",
            "pre_workout": "Coconut water or cool water, avoid working out in anger/stress",
            "post_workout": "Cool shower, coconut water, avoid overheating",
            "recovery": "Moon salutation on rest days, avoid competitive mindset"
        }
    elif dosha == "kapha":
        return {
            "best_time_to_workout": "6am-10am (kapha time — exercise fights morning heaviness)",
            "pre_workout": "Dry ginger tea, no heavy breakfast before workout",
            "post_workout": "Stimulating pranayama (Kapalabhati), light protein meal",
            "recovery": "Stay active on rest days — walk minimum 30 mins"
        }
    else: # Vata
        return {
            "best_time_to_workout": "10am-2pm (avoid early morning cold)",
            "pre_workout": "Warm sesame oil self-massage, eat a small warm meal 1hr before",
            "post_workout": "Rest 10 mins, warm water, avoid cold shower immediately",
            "recovery": "Prioritize 8hrs sleep, warm oil massage on rest days"
        }

def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None):
    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    filtered_exercises = filter_exercises(user_profile, gym_prefs, ge)
    muscle_split = split_by_muscle_group(filtered_exercises)
    
    workout_days = gym_prefs.get("workout_days_per_week", 4)
    schedule_focus = build_weekly_schedule(workout_days)
    
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_schedule = []
    
    for i, focus in enumerate(schedule_focus):
        day_plan = build_day_plan(i+1, days_of_week[i], focus, muscle_split, gym_prefs, user_profile)
        weekly_schedule.append(day_plan)
        
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    disclaimer = "PREGNANCY DISCLAIMER: Please consult your doctor before starting any exercise program during pregnancy. Avoid high impact, twisting, and heavy lifting." if is_pregnant else "This plan is for general wellness guidance only. Please consult a physician before beginning any new exercise program."

    return {
        "plan_id": f"gym_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "bmi_category": user_profile.get("bmi_category", "unknown"),
            "fitness_level": user_profile.get("fitness_level", "beginner"),
            "gym_goal": gym_prefs.get("gym_goal", "general_fitness"),
            "workout_days": workout_days,
            "duration_per_session": gym_prefs.get("workout_duration_minutes", 45)
        },
        "weekly_schedule": weekly_schedule,
        "ayurvedic_tips": get_ayurvedic_tips(dominant_dosha),
        "progressive_overload_note": "Week 2: increase reps by 2. Week 3: add 1 set. Week 4: deload.",
        "disclaimer": disclaimer
    }
