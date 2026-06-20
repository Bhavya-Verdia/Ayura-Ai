import json
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_PATH = BASE_DIR / "data" / "knowledge_base" / "gym_exercises.json"

gym_exercises = []
if EXERCISES_PATH.exists():
    with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
        gym_exercises = json.load(f)


# ── Warmup / Cooldown libraries ───────────────────────────────────────────────

_WARMUP = {
    "upper": [
        "Arm circles — 10 forward, 10 backward",
        "Cross-body shoulder stretch — 30 sec each side",
        "Shoulder roll — 10 slow rotations",
        "Band pull-apart or doorway chest stretch — 15 reps",
        "Cat-cow — 8 reps",
        "Wrist circles — 10 each direction",
    ],
    "lower": [
        "Hip circles — 10 each direction",
        "Leg swings — 10 forward/back each leg",
        "Bodyweight squat — 10 slow reps",
        "Ankle circles — 10 each direction",
        "Glute bridge — 12 reps",
        "Walking lunge — 8 each leg",
    ],
    "core": [
        "Cat-cow — 10 reps",
        "Dead bug — 8 each side",
        "Hip flexor stretch — 30 sec each side",
        "Bird dog — 8 each side",
        "High knees — 30 sec",
    ],
    "full": [
        "Jumping jacks — 30 sec",
        "Arm circles — 10 each direction",
        "Hip circles — 10 each direction",
        "Bodyweight squat — 10 reps",
        "High knees — 30 sec",
        "Inchworm — 5 reps",
    ],
    "cardio": [
        "Brisk walk or light jog — 3 min",
        "Leg swings — 10 each leg",
        "Ankle circles — 10 each direction",
        "Hip circles — 10 each direction",
        "Dynamic quad stretch — 8 each leg",
    ],
}

_COOLDOWN = {
    "upper": [
        "Doorway chest stretch — 30 sec",
        "Cross-body shoulder stretch — 30 sec each side",
        "Overhead tricep stretch — 30 sec each arm",
        "Lat stretch in doorway — 30 sec each side",
        "Child's pose — 60 sec",
        "Deep belly breathing — 5 breaths",
    ],
    "lower": [
        "Standing quad stretch — 30 sec each leg",
        "Seated hamstring stretch — 30 sec each leg",
        "Pigeon pose or figure-four stretch — 45 sec each side",
        "Calf stretch against wall — 30 sec each leg",
        "Supine spinal twist — 30 sec each side",
        "Child's pose — 60 sec",
    ],
    "core": [
        "Supine spinal twist — 30 sec each side",
        "Child's pose — 60 sec",
        "Hip flexor stretch (lunge) — 30 sec each side",
        "Cobra stretch — 30 sec",
        "Deep belly breathing — 5 breaths",
    ],
    "full": [
        "Child's pose — 60 sec",
        "Supine spinal twist — 30 sec each side",
        "Quad stretch — 30 sec each leg",
        "Shoulder cross-body stretch — 30 sec each arm",
        "Deep belly breathing — 5 breaths",
    ],
    "cardio": [
        "Walk at easy pace — 3 min",
        "Standing quad stretch — 30 sec each leg",
        "Standing calf stretch — 30 sec each leg",
        "Seated hamstring stretch — 30 sec each leg",
        "Deep belly breathing — 5 breaths",
    ],
}

_FOCUS_WARMUP_TYPE = {
    "full_body": "full", "push": "upper", "pull": "upper",
    "chest_triceps": "upper", "back_biceps": "upper",
    "chest": "upper", "back": "upper", "shoulders": "upper",
    "shoulders_core": "upper", "arms": "upper",
    "legs": "lower", "legs_core": "lower",
    "shoulders_arms": "upper", "core_cardio": "cardio",
}


def _warmup_for(focus: str) -> list:
    return _WARMUP.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _WARMUP["full"])


def _cooldown_for(focus: str) -> list:
    return _COOLDOWN.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _COOLDOWN["full"])


# ── Goal-based prescription (Fix 2) ──────────────────────────────────────────
# Each goal prescribes its own sets/reps/rest per week.
# This is what makes a strength plan feel different from a fat-loss plan.

_GOAL_WEEKS = {
    "strength": [
        {"sets": 3, "reps": "3-5",  "rest_seconds": 180, "note": "Focus on form. Choose a weight you can barely complete 5 clean reps with."},
        {"sets": 4, "reps": "3-5",  "rest_seconds": 180, "note": "Add 2.5–5 kg vs Week 1 on main lifts if all reps were clean."},
        {"sets": 4, "reps": "4-5",  "rest_seconds": 180, "note": "Peak intensity week — push for personal bests on compound lifts."},
        {"sets": 2, "reps": "3-5",  "rest_seconds": 180, "note": "Deload — reduce weight 20%, focus on perfect technique."},
    ],
    "muscle_gain": [
        {"sets": 3, "reps": "8-10",  "rest_seconds": 90,  "note": "Foundation — last 2 reps of each set should feel challenging."},
        {"sets": 3, "reps": "10-12", "rest_seconds": 75,  "note": "Volume build — same weight as W1, push for extra reps."},
        {"sets": 4, "reps": "10-12", "rest_seconds": 60,  "note": "Peak volume — highest workload week, add weight if form is solid."},
        {"sets": 2, "reps": "8-10",  "rest_seconds": 90,  "note": "Deload — reduce weight 15%, prioritise mind-muscle connection."},
    ],
    "fat_loss": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 45,  "note": "Keep rest short to maintain elevated heart rate. Moderate weight."},
        {"sets": 3, "reps": "15-20", "rest_seconds": 35,  "note": "Cut rest by 10 sec vs Week 1 to increase metabolic demand."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 30,  "note": "Peak metabolic week — minimum rest, circuit style if possible."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 45,  "note": "Deload — slightly fewer reps, full rest, let connective tissue recover."},
    ],
    "endurance": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 30,  "note": "Light weight, high reps. Focus on breathing rhythm throughout."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 25,  "note": "Add 1 set vs Week 1. Cut rest to challenge aerobic capacity."},
        {"sets": 4, "reps": "18-22", "rest_seconds": 20,  "note": "Peak endurance week — go to near-failure on each set."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 30,  "note": "Deload — reduce volume, maintain movement quality."},
    ],
    "general_fitness": [
        {"sets": 3, "reps": "10-12", "rest_seconds": 60,  "note": "Balanced foundation. Should feel moderately challenging by last rep."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 50,  "note": "Increase reps or reduce rest slightly vs Week 1."},
        {"sets": 4, "reps": "12-15", "rest_seconds": 45,  "note": "Peak week — add 1 set to all exercises."},
        {"sets": 2, "reps": "10-12", "rest_seconds": 60,  "note": "Deload — back to Week 1 volume, let the body consolidate gains."},
    ],
}


def _get_goal_prescription(goal: str, week: int) -> dict:
    prescriptions = _GOAL_WEEKS.get(goal, _GOAL_WEEKS["general_fitness"])
    return prescriptions[min(week - 1, 3)]


# ── Exercise filtering ────────────────────────────────────────────────────────

def filter_exercises(user_profile, gym_prefs, exercises):
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}

    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    user_level = user_profile.get("fitness_level", "beginner") or "beginner"
    allowed_levels = level_map.get(user_level, ["beginner"])

    # Beginners doing bodyweight-only: also allow intermediate bodyweight exercises
    # so pull/push days don't end up empty (chin-ups, rows are marked intermediate)
    if user_level == "beginner" and is_bodyweight_only:
        allowed_levels = ["beginner", "intermediate"]

    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    gym_goal = gym_prefs.get("gym_goal", "general_fitness")
    injuries = set(user_profile.get("injuries_or_limitations") or [])
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)

    scored = []
    for ex in exercises:
        eq = ex.get("equipment", "bodyweight").lower()
        if eq not in available_eq and eq != "bodyweight":
            continue
        if ex.get("level", "intermediate") not in allowed_levels:
            continue
        if not ex.get("goal_suitability", {}).get(gym_goal, False):
            continue
        if injuries.intersection(set(ex.get("contraindications", []))):
            continue
        if is_pregnant and not ex.get("pregnancy_safe", False):
            continue

        score = 0
        dosha_suit = ex.get("dosha_suitability", {}).get(dominant_dosha, "moderate")
        if dosha_suit == "good":
            score += 2
        elif dosha_suit == "moderate":
            score += 1
        elif dosha_suit == "avoid":
            score -= 2
        # Prefer true-beginner exercises for beginners
        if user_level == "beginner" and ex.get("level") == "beginner":
            score += 1
        scored.append((score, ex))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [ex for _, ex in scored[:200]]


# ── Muscle group split ────────────────────────────────────────────────────────

def split_by_muscle_group(exercises):
    split = {k: [] for k in ["chest", "triceps", "biceps", "back", "shoulders", "legs", "core", "full_body", "cardio"]}
    for ex in exercises:
        if ex.get("category") == "cardio":
            split["cardio"].append(ex)
            continue
        primary = [m.lower() for m in ex.get("primary_muscles", [])]
        assigned = False
        for m in primary:
            if "chest" in m or "pectoral" in m:
                split["chest"].append(ex); assigned = True; break
            elif "tricep" in m:
                split["triceps"].append(ex); assigned = True; break
            elif "bicep" in m:
                split["biceps"].append(ex); assigned = True; break
            elif m in ["lats", "middle back", "lower back", "traps", "back"]:
                split["back"].append(ex); assigned = True; break
            elif "shoulder" in m or "deltoid" in m:
                split["shoulders"].append(ex); assigned = True; break
            elif m in ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors", "legs", "quad", "calf"]:
                split["legs"].append(ex); assigned = True; break
            elif "abdominal" in m or "core" in m or "abs" in m or "hip flex" in m:
                split["core"].append(ex); assigned = True; break
        if not assigned:
            split["full_body"].append(ex)
    return split


# ── Weekly schedule builder ───────────────────────────────────────────────────

def _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level):
    """Detect equipment/level constraints and pick the right split (Fix 3)."""
    # Beginners with bodyweight only → always full-body; split days lead to empty pools
    if is_bodyweight_only and fitness_level == "beginner":
        if workout_days <= 2:
            return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
        elif workout_days == 3:
            return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]
        else:
            return ["full_body", "rest", "full_body", "rest", "full_body", "core_cardio", "rest"]

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
    return ["full_body", "full_body", "full_body", "rest", "rest", "rest", "rest"]


def _focus_to_keys(focus):
    if "full_body" in focus:        return ["full_body", "chest", "back", "legs", "core"]
    elif "push" in focus:           return ["chest", "shoulders", "triceps"]
    elif "pull" in focus:           return ["back", "biceps"]
    elif focus == "legs":           return ["legs"]
    elif "legs_core" in focus:      return ["legs", "core"]
    elif "chest_triceps" in focus:  return ["chest", "triceps"]
    elif "back_biceps" in focus:    return ["back", "biceps"]
    elif focus == "chest":          return ["chest"]
    elif focus == "back":           return ["back"]
    elif "shoulders_core" in focus: return ["shoulders", "core"]
    elif "shoulders_arms" in focus: return ["shoulders", "biceps", "triceps"]
    elif focus == "shoulders":      return ["shoulders"]
    elif "arms" in focus:           return ["biceps", "triceps"]
    elif "core_cardio" in focus:    return ["core", "cardio"]
    return ["full_body"]


# ── Exercise selection ────────────────────────────────────────────────────────

def _deterministic_select(pool, n, seed_key):
    seed = int(hashlib.md5(seed_key.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)
    unique_pool = list({ex["id"]: ex for ex in pool}.values())
    rng.shuffle(unique_pool)
    return unique_pool[:n]


def _target_count(duration, goal):
    """Volume cap: max 5 exercises/day (Fix 3). Strength gets fewer, heavier."""
    if duration <= 20:   base = 3
    elif duration <= 30: base = 4
    else:                base = 5  # Hard cap — prevents 40-set weeks
    if goal == "strength":
        base = min(base, 4)  # Strength: fewer movements, heavier weight
    return base


# ── Day plan builder ──────────────────────────────────────────────────────────

def build_day_plan(day_num, day_name, focus, muscle_split, gym_prefs, user_profile, week=1, user_id="default"):
    if focus == "rest":
        return {
            "day": day_num, "day_name": day_name,
            "focus": "Rest & Recovery", "type": "recovery",
            "warmup": [], "main_workout": [], "cooldown": [],
            "estimated_duration_minutes": 0, "calories_burned_estimate": 0,
        }

    duration = gym_prefs.get("workout_duration_minutes", 45)
    goal = gym_prefs.get("gym_goal", "general_fitness")
    level = user_profile.get("fitness_level", "beginner") or "beginner"
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"

    target = _target_count(duration, goal)
    rx = _get_goal_prescription(goal, week)  # goal-specific sets/reps/rest

    # Build pool from focus keys
    pool = []
    for k in _focus_to_keys(focus):
        pool.extend(muscle_split.get(k, []))

    # Fix 1: Fallback for thin pools (Fix 3) ──────────────────────────────────
    if len(pool) < 3:
        pool = muscle_split.get("full_body", [])
    if len(pool) < 3:
        # Last resort: everything available
        pool = [ex for group in muscle_split.values() for ex in group]

    seed_key = f"{user_id}-{focus}-d{day_num}-w{week}"
    selected = _deterministic_select(pool, target, seed_key)

    main_workout = []
    total_cals = 0
    for ex in selected:
        is_timed = any(c.isalpha() for c in str(rx["reps"]))
        sets = rx["sets"]
        reps = rx["reps"]
        rest = rx["rest_seconds"]

        try:
            parts = str(reps).split("-")
            reps_val = sum(int(p) for p in parts if p.isdigit()) / max(len(parts), 1)
        except Exception:
            reps_val = 10

        cpm = ex.get("calories_per_minute", 5.0)
        time_per_rep = 2 if ex.get("category") == "cardio" else 4
        total_cals += (sets * reps_val * time_per_rep / 60.0) * cpm

        main_workout.append({
            "exercise_id": ex.get("id"),
            "exercise_name": ex.get("name"),
            "category": ex.get("category", "strength"),
            "primary_muscles": ex.get("primary_muscles", []),
            "equipment": ex.get("equipment", "bodyweight"),
            "sets": sets,
            "reps": reps,
            "rest_seconds": rest,
            "week_note": rx.get("note", ""),
            "notes": ex.get("modification", ""),
            "instructions": ex.get("instructions", []),
        })

    return {
        "day": day_num,
        "day_name": day_name,
        "focus": focus.replace("_", " ").title(),
        "type": "cardio" if "cardio" in focus else "strength",
        "warmup": _warmup_for(focus),
        "main_workout": main_workout,
        "cooldown": _cooldown_for(focus),
        "estimated_duration_minutes": duration,
        "calories_burned_estimate": int(total_cals + 20),
    }


# ── Ayurvedic tips ────────────────────────────────────────────────────────────

def get_ayurvedic_tips(dosha):
    if dosha == "pitta":
        return {
            "best_time_to_workout": "Early morning or evening (avoid midday heat)",
            "pre_workout": "Coconut water or cool water; avoid working out in anger or stress",
            "post_workout": "Cool shower, coconut water; avoid overheating",
            "recovery": "Moon salutation on rest days; cultivate non-competitive mindset",
        }
    elif dosha == "kapha":
        return {
            "best_time_to_workout": "6–10am (Kapha time — exercise fights morning heaviness)",
            "pre_workout": "Dry ginger tea; no heavy breakfast before workout",
            "post_workout": "Stimulating pranayama (Kapalabhati), light protein meal",
            "recovery": "Stay active on rest days — minimum 30-min walk; avoid napping after workout",
        }
    else:
        return {
            "best_time_to_workout": "10am–2pm (avoid early-morning cold and late-night stimulation)",
            "pre_workout": "Warm sesame oil self-massage (Abhyanga); eat a small warm meal 1 hr before",
            "post_workout": "Rest 10 min; warm water; avoid cold shower immediately after",
            "recovery": "Prioritize 8 hrs sleep; warm oil massage on rest days; avoid over-exertion",
        }


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None):
    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    filtered = filter_exercises(user_profile, gym_prefs, ge)
    muscle_split = split_by_muscle_group(filtered)

    workout_days = gym_prefs.get("workout_days_per_week", 4)
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}
    fitness_level = user_profile.get("fitness_level", "beginner") or "beginner"

    schedule_focus = _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    goal = gym_prefs.get("gym_goal", "general_fitness")

    four_week_plan = []
    for week in range(1, 5):
        week_days = [
            build_day_plan(i + 1, days_of_week[i], focus, muscle_split, gym_prefs, user_profile, week, user_id)
            for i, focus in enumerate(schedule_focus)
        ]
        four_week_plan.append({
            "week": week,
            "theme": {1: "Foundation", 2: "Volume Build", 3: "Intensity Peak", 4: "Deload & Reset"}[week],
            "prescription": _get_goal_prescription(goal, week),
            "days": week_days,
        })

    disclaimer = (
        "PREGNANCY DISCLAIMER: Consult your doctor before starting any exercise program during pregnancy. "
        "Avoid high impact, twisting, and heavy lifting."
        if is_pregnant else
        "This plan is for general wellness guidance only. Consult a physician before beginning any new exercise program."
    )

    return {
        "plan_id": f"gym_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "bmi_category": user_profile.get("bmi_category", "unknown"),
            "fitness_level": fitness_level,
            "gym_goal": goal,
            "workout_days": workout_days,
            "duration_per_session": gym_prefs.get("workout_duration_minutes", 45),
        },
        "weekly_schedule": four_week_plan[0]["days"],
        "four_week_plan": four_week_plan,
        "ayurvedic_tips": get_ayurvedic_tips(dominant_dosha),
        "progressive_overload_guide": {
            "week_1": _GOAL_WEEKS[goal][0]["note"] if goal in _GOAL_WEEKS else "",
            "week_2": _GOAL_WEEKS[goal][1]["note"] if goal in _GOAL_WEEKS else "",
            "week_3": _GOAL_WEEKS[goal][2]["note"] if goal in _GOAL_WEEKS else "",
            "week_4": _GOAL_WEEKS[goal][3]["note"] if goal in _GOAL_WEEKS else "",
        },
        "disclaimer": disclaimer,
    }
