"""How a gym plan is PROGRAMMED — the shape a coach would recognise.

Every test here came out of a 400-plan sweep (random age, sex, body, level,
goal, days, length, equipment, conditions, cardio preference) that read the
generated week rather than the code. Each failure mode it found was invisible
to the safety suite, because none of them is unsafe; they are the things that
make a qualified reviewer stop trusting the rest of the page.
"""
import collections
import random
import re

import pytest

from services.gym_plan_engine import (
    _TIER_REPS, _build_weekly_schedule, _get_weight_range, _movement_pattern,
    _parse_reps, generate_gym_plan, gym_exercises,
)

_BY_ID = {e["id"]: e for e in gym_exercises}
_STANDARD_RANGES = {r for pair in _TIER_REPS.values() for r in pair} | set(_TIER_REPS)


def _bmi_category(h, w):
    b = w / (h / 100) ** 2
    return ("underweight" if b < 18.5 else "normal" if b < 25
            else "overweight" if b < 30 else "obese")


def _sweep(n=80, seed=7):
    rng = random.Random(seed)
    for i in range(n):
        h, w = rng.choice([(170, 50), (170, 68), (165, 82), (172, 120)])
        level = rng.choice(["beginner", "intermediate", "advanced"])
        profile = {
            "id": f"sweep{i}", "age": rng.choice([14, 24, 35, 48, 62, 75]),
            "gender": rng.choice(["male", "female", "other"]),
            "height_cm": h, "weight_kg": w, "bmi_category": _bmi_category(h, w),
            "fitness_level": level,
            "activity_level": rng.choice(["sedentary", "light", "moderate", "active"]),
            "medical_history": rng.choice([[], ["hypertension"], ["diabetes"],
                                           ["osteoporosis"], ["knee_pain"], ["asthma"]]),
            "dominant_dosha": rng.choice(["vata", "pitta", "kapha"]),
        }
        prefs = {
            "gym_goal": rng.choice(["fat_loss", "muscle_gain", "strength",
                                    "endurance", "general_fitness"]),
            "workout_days_per_week": rng.choice([2, 3, 4, 5, 6]),
            "workout_duration_minutes": rng.choice([20, 30, 45, 60]),
            "available_equipment": rng.choice([["full_gym"], ["bodyweight"],
                                               ["dumbbell", "bands"], ["dumbbell", "machine"]]),
            "strength_level": rng.choice(["untrained", "beginner", level]),
            "cardio_preference": rng.choice(["none", "light", "moderate", "heavy"]),
            "target_muscle_focus": rng.choice(["full_body", "full_body", "upper", "lower", "back"]),
        }
        yield profile, prefs, generate_gym_plan(profile, prefs)


_PLANS = list(_sweep())


def _training_days(plan, weeks=(1,)):
    for week in plan["four_week_plan"]:
        if week["week"] in weeks:
            for day in week["days"]:
                if day["type"] != "recovery":
                    yield day


def test_a_day_does_not_press_the_same_way_four_times():
    """A strength chest day came out bench, floor press, incline bench and
    dumbbell bench at five sets each; a full-body day, two horizontal presses
    and no overhead one. A day holds one compound per movement pattern on a
    full-body, upper or lower day and two on a day named for a region — the
    sweep found 549 days over it before the cap."""
    over = []
    for _, prefs, plan in _PLANS:
        for day in _training_days(plan):
            spread = day["focus"].lower() in ("full body", "upper", "lower", "legs core")
            cap = 1 if spread else 2
            counts = collections.Counter(
                _movement_pattern(_BY_ID[e["exercise_id"]]) for e in day["main_workout"]
                if e["role"] != "conditioning"
                and _BY_ID[e["exercise_id"]].get("mechanic") == "compound")
            for pattern in ("squat", "hinge", "push_h", "push_v", "pull_h", "pull_v"):
                if counts[pattern] > cap:
                    over.append((day["focus"], pattern, counts[pattern]))
    # The fallback may still reach past the cap when a bodyweight pool holds
    # nothing else, but it is the exception, not the shape of a week.
    assert len(over) <= 3, over[:10]


def test_bodyweight_variants_of_one_movement_are_not_stacked():
    """Push-Up, Incline Push-Up and Knee Push-Up in one session is one exercise
    at three difficulty levels, two of them too easy for whoever can do the
    third."""
    stacked = []
    for _, _, plan in _PLANS:
        for day in _training_days(plan):
            families = collections.Counter(
                _BY_ID[e["exercise_id"]]["family"] for e in day["main_workout"]
                if _BY_ID[e["exercise_id"]]["equipment"] == "bodyweight")
            stacked += [(day["focus"], f, n) for f, n in families.items() if n > 2]
    assert not stacked, stacked[:5]


def test_every_rep_range_is_one_a_coach_writes():
    """The tiers were the main lift's range shifted by a fixed number, which
    wrote 11-13, 13-15, 17-22 and 5-7 on 4,587 rows of the sweep."""
    odd = collections.Counter()
    for _, _, plan in _PLANS:
        for day in _training_days(plan, weeks=(1, 2, 3, 4)):
            for e in day["main_workout"]:
                if _parse_reps(e["reps"]) and e["reps"] not in _STANDARD_RANGES:
                    odd[e["reps"]] += 1
    assert not odd, odd.most_common(5)


def test_a_bodyweight_movement_names_its_own_next_step():
    """The library authors `easier`/`harder` for every bodyweight movement, and
    the plan printed a ladder keyed on the MUSCLE instead: a glute bridge, a
    calf raise and a glute kickback were each told to progress to a pistol
    squat."""
    checked = 0
    for _, _, plan in _PLANS:
        for day in _training_days(plan):
            for e in day["main_workout"]:
                lib = _BY_ID[e["exercise_id"]]
                harder = (lib.get("progression") or {}).get("harder")
                if lib["equipment"] == "bodyweight" and harder:
                    assert harder in e["weight_range"], (e["exercise_name"], e["weight_range"])
                    checked += 1
    assert checked > 50


def test_no_barbell_is_lighter_than_the_bar_it_is_lifted_with():
    """An obese 55-year-old was written a 2-3 kg barbell curl. An EZ-bar or a
    fixed barbell starts at about 7.5 kg; an Olympic bar at 20."""
    for _, _, plan in _PLANS:
        for day in _training_days(plan, weeks=(1, 2, 3, 4)):
            for e in day["main_workout"]:
                m = re.match(r"([\d.]+)–([\d.]+) kg", e["weight_range"])
                if m and e["equipment"] == "barbell":
                    assert float(m.group(1)) >= 7.5, (e["exercise_name"], e["weight_range"])


@pytest.mark.parametrize("minutes", [20, 30, 45, 60])
def test_a_session_runs_about_as_long_as_was_asked(minutes):
    """A 20-minute request was built as 44-47 minutes (three main lifts at five
    sets and a fifteen-minute walk), and a 90-minute endurance session as 55.
    Up to an hour the session is fitted to the clock: sets come off or go on,
    and the conditioning block is sized to what is left."""
    plan = generate_gym_plan(
        {"age": 30, "gender": "male", "weight_kg": 75, "fitness_level": "intermediate",
         "bmi_category": "normal", "dominant_dosha": "pitta"},
        {"gym_goal": "general_fitness", "workout_days_per_week": 4,
         "workout_duration_minutes": minutes, "available_equipment": ["full_gym"],
         "strength_level": "intermediate"})
    for day in _training_days(plan):
        assert abs(day["estimated_duration_minutes"] - minutes) <= max(5, minutes * 0.2), (
            day["focus"], day["estimated_duration_minutes"], minutes)


def test_a_long_endurance_session_spends_its_extra_time_on_cardio():
    plan = generate_gym_plan(
        {"age": 30, "gender": "female", "weight_kg": 62, "fitness_level": "intermediate",
         "bmi_category": "normal", "dominant_dosha": "kapha"},
        {"gym_goal": "endurance", "workout_days_per_week": 4,
         "workout_duration_minutes": 75, "available_equipment": ["full_gym"],
         "cardio_preference": "heavy"})
    minutes = [int(e["reps"].split()[0]) for d in _training_days(plan)
               for e in d["main_workout"]
               if e["role"] == "conditioning" and e["reps"].endswith("min")]
    assert minutes and max(minutes) >= 20, minutes


@pytest.mark.parametrize("level", ["intermediate", "advanced"])
@pytest.mark.parametrize("days", [3, 4, 5, 6])
def test_a_strength_goal_is_not_a_bodybuilding_split(level, days):
    """An advanced lifter asking to get stronger was written "Chest" and
    "Shoulders & Arms" days — squatting and deadlifting once a week."""
    sched = _build_weekly_schedule(days, False, level, "full_body", goal="strength")
    assert not {"chest", "back", "chest_triceps", "back_biceps",
                "shoulders_arms", "arms", "shoulders"} & set(sched), sched
    assert sum(d in ("lower", "full_body") for d in sched) >= 2, sched


@pytest.mark.parametrize("level", ["intermediate", "advanced"])
def test_three_days_trains_each_muscle_more_than_once(level):
    """Push / pull / legs across three days trains each muscle once a week."""
    sched = _build_weekly_schedule(3, False, level, "full_body", goal="muscle_gain")
    assert "push" not in sched and "pull" not in sched, sched


def test_a_conditioning_day_carries_conditioning():
    """It came out as forty-five minutes of planks and crunches labelled
    "Core" for the goals whose cardio share did not happen to land on it."""
    plan = generate_gym_plan(
        {"age": 33, "gender": "male", "weight_kg": 95, "fitness_level": "advanced",
         "bmi_category": "overweight", "dominant_dosha": "kapha"},
        {"gym_goal": "strength", "workout_days_per_week": 6,
         "workout_duration_minutes": 60, "available_equipment": ["full_gym"],
         "cardio_preference": "light"})
    cond_days = [d for d in _training_days(plan) if "Core" in d["focus"]]
    assert cond_days
    for day in cond_days:
        assert any(e["role"] == "conditioning" for e in day["main_workout"]), day["focus"]
        assert sum(e["role"] != "conditioning" for e in day["main_workout"]) <= 4


@pytest.mark.parametrize("goal", ["muscle_gain", "fat_loss", "endurance", "general_fitness"])
def test_the_conventional_deadlift_is_kept_for_strength_sets(goal):
    """A hypertrophy leg day opened squat 4x8-10 then deadlift 4x8-10; an
    endurance one, deadlift 4x15-20. The Romanian deadlift trains the hinge at
    a load that suits the reps."""
    plan = generate_gym_plan(
        {"age": 28, "gender": "male", "weight_kg": 78, "fitness_level": "intermediate",
         "bmi_category": "normal", "dominant_dosha": "vata"},
        {"gym_goal": goal, "workout_days_per_week": 4, "workout_duration_minutes": 60,
         "available_equipment": ["full_gym"], "strength_level": "intermediate"})
    for day in _training_days(plan, weeks=(1, 2, 3, 4)):
        assert "Barbell Deadlift" not in {e["exercise_name"] for e in day["main_workout"]}


def test_a_strength_block_is_led_by_a_free_weight():
    plan = generate_gym_plan(
        {"age": 33, "gender": "male", "weight_kg": 95, "fitness_level": "advanced",
         "bmi_category": "overweight", "dominant_dosha": "kapha"},
        {"gym_goal": "strength", "workout_days_per_week": 4,
         "workout_duration_minutes": 75, "available_equipment": ["full_gym"],
         "strength_level": "advanced"})
    for day in _training_days(plan):
        for e in day["main_workout"]:
            if e["role"] == "primary":
                assert e["equipment"] in ("barbell", "dumbbell", "kettlebell", "machine"), e
                assert _movement_pattern(_BY_ID[e["exercise_id"]]) != "pull_v", e


# ── Load calibration ──────────────────────────────────────────────────────────
# Anchored on Strength Level's published standards (strengthlevel.com, read
# 2026-10) at a 70 kg man and a 60 kg woman. The estimate is the load for a set
# of 10 two reps short of failure; Epley puts that at ~0.71 of a one-rep max.
# "Intermediate" is set between their Novice and Intermediate rows, untrained
# at about their Beginner row. The bands are wide on purpose: the point is that
# nobody is told to curl 1 kg or to goblet-squat 50.

def _top(name, level, sex, bw):
    ex = next(e for e in gym_exercises if e["name"] == name)
    text = _get_weight_range(ex, level, sex, bw, reps="8-10", age=30)
    return float(re.match(r"[\d.]+–([\d.]+)", text).group(1))


@pytest.mark.parametrize("name,level,sex,bw,lo,hi", [
    # SL bench 70 kg man: novice 64, intermediate 85 -> x0.71 at 10 reps
    ("Barbell Bench Press", "intermediate", "male", 70, 45, 62),
    ("Barbell Squat", "intermediate", "male", 70, 62, 85),
    ("Barbell Romanian Deadlift", "intermediate", "male", 70, 50, 75),
    # SL dumbbell lateral raise, 70 kg man: novice 9, intermediate 15
    ("Side Lateral Raise", "intermediate", "male", 70, 6, 11),
    # SL dumbbell curl, 60 kg woman: beginner 4, novice 7
    ("Dumbbell Bicep Curl", "untrained", "female", 60, 2.5, 6),
    ("Hammer Curls", "beginner", "female", 60, 3, 7),
    # SL goblet squat, 70 kg man: novice 22, intermediate 32
    ("Goblet Squat", "intermediate", "male", 70, 14, 26),
])
def test_starting_loads_sit_inside_published_standards(name, level, sex, bw, lo, hi):
    kg = _top(name, level, sex, bw)
    assert lo <= kg <= hi, f"{name} {level} {sex} {bw} kg: {kg} kg outside {lo}-{hi}"


def test_one_dumbbell_is_not_quoted_per_hand():
    for name in ("Dumbbell Side Bend", "Suitcase Carry",
                 "Dumbbell Overhead Triceps Extension - Two Hands", "Goblet Squat"):
        ex = next(e for e in gym_exercises if e["name"] == name)
        assert "per hand" not in _get_weight_range(ex, "intermediate", "male", 75,
                                                   reps="10-12"), name


# ── Stored inputs ─────────────────────────────────────────────────────────────

def test_a_stored_preference_of_any_plausible_shape_still_builds_a_plan():
    """Both plan paths read preferences back from Mongo, not from the validated
    request. A fuzz of plausible stored shapes found eight crashes — a duration
    saved as null, days as "4", `exercise_preferences` as a string, an age of
    "abc" — each one a user who could not regenerate their plan."""
    rng = random.Random(11)
    profile_values = {
        "age": [None, "", "35", 17.5, "abc", 120], "gender": [None, "", "Male", 123, "nonbinary"],
        "weight_kg": [None, "70", "x", 300], "fitness_level": [None, "", "expert", "Beginner"],
        "medical_history": [None, "diabetes", ["", None], ["Hypertension"]],
        "dominant_dosha": [None, "Vata", "vata-pitta"], "pregnancy_or_nursing": [None, "yes", True],
        "allergies": [None, "dairy", [None]], "injuries_or_limitations": [None, "knee", [""]],
    }
    pref_values = {
        "gym_goal": [None, "", "weight_loss", "strength"], "workout_days_per_week": [None, 0, "4", 8],
        "workout_duration_minutes": [None, "45", 5, 120], "available_equipment": [None, [], "full_gym"],
        "strength_level": [None, "pro"], "cardio_preference": [None, "lots"],
        "target_muscle_focus": [None, "arms"], "training_style": [None, "crossfit"],
        "injuries": [None, "knee"], "injury_detail": [None, 5],
        "exercise_preferences": [None, "x", {"likes": "swimming, cycling", "dislikes": None}],
    }
    for _ in range(250):
        profile = {k: rng.choice(v) for k, v in profile_values.items() if rng.random() < 0.8}
        prefs = {k: rng.choice(v) for k, v in pref_values.items() if rng.random() < 0.8}
        plan = generate_gym_plan(profile, prefs)
        for day in _training_days(plan, weeks=(1, 2, 3, 4)):
            assert day["main_workout"], (profile, prefs)


def test_an_unanswered_sex_is_priced_between_the_two_standards():
    """"Other" and unanswered took the male standard; the diet path made the same
    mistake with its energy equation and fixed it the same way."""
    bench = next(e for e in gym_exercises if e["name"] == "Barbell Bench Press")
    kg = {g: float(re.match(r"([\d.]+)–([\d.]+)", _get_weight_range(
        bench, "advanced", g, 80, reps="8-10")).group(2)) for g in ("male", "female", "other")}
    assert kg["female"] < kg["other"] < kg["male"], kg
