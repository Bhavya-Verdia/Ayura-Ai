"""Generate the gym reviewer pack: twelve people, their plans exactly as the app builds them.

The pack is what a physiotherapist and a Vaidya read. A pack read off old output
is worse than none, because a reviewer signs off on behaviour the app no longer
has. Run this after any change to the gym engine or its enricher, and update
the reviewer doc from the markdown it writes.

    python scripts/gym_reviewer_pack.py generate   # engine + live enrichment -> JSON
    python scripts/gym_reviewer_pack.py generate 2 8   # only those plans
    python scripts/gym_reviewer_pack.py render     # JSON -> markdown, one file per plan

`generate` makes real LLM calls (the coaching is part of what is reviewed) and
touches no database. Plan 12's history is simulated, as the pack says.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).resolve().parent / "gym_reviewer_pack"

FULL_GYM = ["barbell", "dumbbells", "machines", "cables", "kettlebell", "resistance_bands",
            "cardio_machines"]

# (title, profile, prefs). Profiles carry what onboarding records; prefs what the
# gym form records. Heights are not shown in the pack and are typical for the build.
PERSONAS = [
    ("15-year-old with asthma, building muscle",
     dict(age=15, gender="male", height_cm=168, weight_kg=55, fitness_level="beginner",
          activity_level="active", dominant_dosha="pitta", medical_history=["asthma"]),
     dict(gym_goal="muscle_gain", workout_days_per_week=5, workout_duration_minutes=60,
          available_equipment=FULL_GYM, strength_level="beginner")),
    ("28-year-old, pregnant",
     dict(age=28, gender="female", height_cm=163, weight_kg=63, fitness_level="intermediate",
          activity_level="moderate", dominant_dosha="vata", medical_history=[],
          pregnancy_or_nursing=True),
     dict(gym_goal="general_fitness", workout_days_per_week=3, workout_duration_minutes=40,
          available_equipment=["dumbbells", "machines"], strength_level="intermediate")),
    ("75-year-old with heart disease and type 2 diabetes",
     dict(age=75, gender="male", height_cm=172, weight_kg=78, fitness_level="beginner",
          activity_level="sedentary", dominant_dosha="kapha",
          medical_history=["heart_disease", "diabetes_type2"]),
     dict(gym_goal="general_fitness", workout_days_per_week=3, workout_duration_minutes=30,
          available_equipment=FULL_GYM, strength_level="untrained")),
    ("26-year-old with PCOS and hypothyroidism, losing fat at home",
     dict(age=26, gender="female", height_cm=160, weight_kg=96, fitness_level="beginner",
          activity_level="sedentary", dominant_dosha="kapha",
          medical_history=["pcos", "hypothyroidism"]),
     dict(gym_goal="fat_loss", workout_days_per_week=4, workout_duration_minutes=45,
          available_equipment=["resistance_bands"], strength_level="untrained")),
    ("29-year-old advanced lifter, strength",
     dict(age=29, gender="male", height_cm=180, weight_kg=90, fitness_level="advanced",
          activity_level="very_active", dominant_dosha="pitta", medical_history=[]),
     dict(gym_goal="strength", workout_days_per_week=4, workout_duration_minutes=75,
          available_equipment=FULL_GYM, strength_level="advanced",
          known_lifts={"squat": {"kg": 170, "reps": 5}, "bench": {"kg": 125, "reps": 5},
                       "deadlift": {"kg": 200, "reps": 4}})),
    ("44-year-old with epilepsy and glaucoma, building muscle",
     dict(age=44, gender="female", height_cm=162, weight_kg=60, fitness_level="intermediate",
          activity_level="moderate", dominant_dosha="pitta",
          medical_history=["epilepsy", "glaucoma"]),
     dict(gym_goal="muscle_gain", workout_days_per_week=4, workout_duration_minutes=45,
          available_equipment=FULL_GYM, strength_level="intermediate")),
    ("36-year-old with sciatica and a lower-back injury, endurance",
     dict(age=36, gender="male", height_cm=175, weight_kg=72, fitness_level="intermediate",
          activity_level="active", dominant_dosha="vata", medical_history=["sciatica"]),
     dict(gym_goal="endurance", workout_days_per_week=5, workout_duration_minutes=60,
          available_equipment=FULL_GYM, strength_level="intermediate",
          injuries=["lower_back"])),
    ("22-year-old with depression and anaemia, sex not given",
     dict(age=22, gender="other", height_cm=165, weight_kg=50, fitness_level="beginner",
          activity_level="light", dominant_dosha="vata",
          medical_history=["depression", "anemia"], allergies=["nuts_tree"]),
     dict(gym_goal="muscle_gain", workout_days_per_week=3, workout_duration_minutes=45,
          available_equipment=["dumbbells"], strength_level="beginner")),
    ("60-year-old with rheumatoid arthritis and osteoporosis",
     dict(age=60, gender="female", height_cm=158, weight_kg=66, fitness_level="beginner",
          activity_level="light", dominant_dosha="vata",
          medical_history=["rheumatoid_arthritis", "osteoporosis"]),
     dict(gym_goal="general_fitness", workout_days_per_week=2, workout_duration_minutes=30,
          available_equipment=["machines", "dumbbells"], strength_level="untrained")),
    ("47-year-old with hypertension and acid reflux, 20-minute sessions",
     dict(age=47, gender="male", height_cm=176, weight_kg=88, fitness_level="intermediate",
          activity_level="sedentary", dominant_dosha="pitta",
          medical_history=["hypertension", "acid_reflux"]),
     dict(gym_goal="fat_loss", workout_days_per_week=3, workout_duration_minutes=20,
          available_equipment=FULL_GYM, strength_level="intermediate")),
    ("31-year-old with one kettlebell",
     dict(age=31, gender="female", height_cm=165, weight_kg=62, fitness_level="beginner",
          activity_level="moderate", dominant_dosha="pitta", medical_history=[]),
     dict(gym_goal="general_fitness", workout_days_per_week=3, workout_duration_minutes=40,
          available_equipment=["kettlebell"], strength_level="beginner")),
    ("30-year-old starting block 2 from logged sets",
     dict(age=30, gender="male", height_cm=178, weight_kg=78, fitness_level="intermediate",
          activity_level="moderate", dominant_dosha="vata", medical_history=[]),
     dict(gym_goal="muscle_gain", workout_days_per_week=4, workout_duration_minutes=60,
          available_equipment=FULL_GYM, strength_level="intermediate")),
]


def _profile(n: int, base: dict) -> dict:
    bmi = round(base["weight_kg"] / (base["height_cm"] / 100) ** 2, 1)
    cat = ("underweight" if bmi < 18.5 else "normal" if bmi < 25
           else "overweight" if bmi < 30 else "obese")
    return {"id": f"pack-{n}", "name": f"Reviewer persona {n}", "bmi": bmi,
            "bmi_category": cat, "pregnancy_or_nursing": False, "allergies": [], **base}


def _prefs(base: dict) -> dict:
    out = {"cardio_preference": "light", "target_muscle_focus": "full_body",
           "training_style": None, "injuries": [], "injury_detail": None,
           "exercise_preferences": {"likes": [], "dislikes": []}, **base}
    out["available_equipment"] = ["bodyweight", *out["available_equipment"]]
    return out


def _simulated_history(plan: dict, logged_sessions: int = 12) -> dict:
    """Block 1's main lifts logged at their top prescribed load for 10 reps,
    rising about 4% a week, over the first `logged_sessions` sessions."""
    import re
    from datetime import datetime, timezone

    from services.workout_log import block_summary, logged_lifts

    entries, n = [], 0
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            if not day.get("main_workout"):
                continue
            n += 1
            if n > logged_sessions:
                break
            for ex in day["main_workout"]:
                if ex.get("role") != "primary":
                    continue
                m = re.search(r"(\d+(?:\.\d+)?)\s*kg", ex.get("weight_range") or "")
                top = re.findall(r"(\d+(?:\.\d+)?)\s*kg", ex.get("weight_range") or "")
                if not m:
                    continue
                kg = float(top[-1]) * (1.04 ** (week["week"] - 1))
                entries.append({"plan_id": plan["plan_id"], "week": week["week"],
                                "day": day["day"], "exercise_id": ex["exercise_id"],
                                "exercise_name": ex["exercise_name"],
                                "sets": [{"kg": round(kg * 2) / 2, "reps": 10}] * int(ex["sets"]),
                                "effort": "right", "updated_at": datetime.now(timezone.utc)})
    return {"logged_lifts": logged_lifts(entries),
            "previous_block": block_summary(plan, entries)}


async def _build(n: int, profile: dict, prefs: dict, history: dict | None = None) -> dict:
    from services.gym_condition_fallback import extra_avoid_tags_for
    from services.gym_plan_engine import generate_gym_plan, gym_exercises
    from services.gym_plan_enricher import enrich_gym_plan

    pool = gym_exercises
    if profile.get("pregnancy_or_nursing"):   # as routes/plans.generate_gym_plan does
        pool = [e for e in gym_exercises if e.get("pregnancy_safe") is True] or None
    raw = generate_gym_plan(profile, prefs, pool,
                            extra_avoid_tags=await extra_avoid_tags_for(profile),
                            logged_lifts=(history or {}).get("logged_lifts"),
                            previous_block=(history or {}).get("previous_block"))
    return await enrich_gym_plan(raw, profile, prefs)


async def generate(only: set[int] | None = None):
    OUT.mkdir(exist_ok=True)
    for n, (title, base_profile, base_prefs) in enumerate(PERSONAS, 1):
        if only and n not in only:
            continue
        profile, prefs = _profile(n, base_profile), _prefs(base_prefs)
        history = None
        if n == 12:
            from services.gym_plan_engine import generate_gym_plan, gym_exercises
            block1 = generate_gym_plan(profile, prefs, gym_exercises)
            history = _simulated_history(block1)
        plan = await _build(n, profile, prefs, history)
        (OUT / f"plan_{n:02d}.json").write_text(json.dumps(
            {"n": n, "title": title, "profile": profile, "prefs": prefs, "plan": plan},
            indent=1, default=str))
        print(f"plan {n:2d}: enriched={plan.get('enriched')} {title}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "generate":
        asyncio.run(generate({int(a) for a in sys.argv[2:]} or None))
    elif cmd == "render":
        from gym_reviewer_pack_render import render_all  # noqa: E402
        render_all(OUT)
    else:
        sys.exit(__doc__)
