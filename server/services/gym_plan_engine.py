import json
import hashlib
import random
import re
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


# ── Goal-based prescription ───────────────────────────────────────────────────

_GOAL_WEEKS = {
    "strength": [
        {"sets": 3, "reps": "3-5",  "rest_seconds": 180, "note": "Focus on form. Choose a weight you can barely complete 5 clean reps with."},
        {"sets": 4, "reps": "3-5",  "rest_seconds": 180, "note": "Add 2.5–5 kg vs Week 1 on main lifts if all reps were clean."},
        {"sets": 4, "reps": "4-5",  "rest_seconds": 180, "note": "Peak intensity week — push for personal bests on compound lifts."},
        {"sets": 2, "reps": "3-5",  "rest_seconds": 180, "note": "Deload — reduce weight 20%, focus on perfect technique."},
    ],
    "muscle_gain": [
        {"sets": 3, "reps": "8-10",  "rest_seconds": 90, "note": "Foundation — last 2 reps of each set should feel challenging."},
        {"sets": 3, "reps": "10-12", "rest_seconds": 75, "note": "Volume build — same weight as W1, push for extra reps."},
        {"sets": 4, "reps": "10-12", "rest_seconds": 60, "note": "Peak volume — highest workload week, add weight if form is solid."},
        {"sets": 2, "reps": "8-10",  "rest_seconds": 90, "note": "Deload — reduce weight 15%, prioritise mind-muscle connection."},
    ],
    "fat_loss": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 45, "note": "Keep rest short to maintain elevated heart rate. Moderate weight."},
        {"sets": 3, "reps": "15-20", "rest_seconds": 35, "note": "Cut rest by 10 sec vs Week 1 to increase metabolic demand."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 30, "note": "Peak metabolic week — minimum rest, circuit style if possible."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 45, "note": "Deload — slightly fewer reps, full rest, let connective tissue recover."},
    ],
    "endurance": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 30, "note": "Light weight, high reps. Focus on breathing rhythm throughout."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 25, "note": "Add 1 set vs Week 1. Cut rest to challenge aerobic capacity."},
        {"sets": 4, "reps": "18-22", "rest_seconds": 20, "note": "Peak endurance week — go to near-failure on each set."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 30, "note": "Deload — reduce volume, maintain movement quality."},
    ],
    "general_fitness": [
        {"sets": 3, "reps": "10-12", "rest_seconds": 60, "note": "Balanced foundation. Should feel moderately challenging by last rep."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 50, "note": "Increase reps or reduce rest slightly vs Week 1."},
        {"sets": 4, "reps": "12-15", "rest_seconds": 45, "note": "Peak week — add 1 set to all exercises."},
        {"sets": 2, "reps": "10-12", "rest_seconds": 60, "note": "Deload — back to Week 1 volume, let the body consolidate gains."},
    ],
}


# Volume is where training age shows. Reps and rest belong to the goal — they are
# what makes a set a strength set or an endurance set — but how many of them a
# body can absorb and recover from is a property of the practitioner.
_LEVEL_SET_DELTA = {"beginner": -1, "intermediate": 0, "advanced": 1}
_MIN_SETS, _MAX_SETS = 2, 6


def _get_goal_prescription(goal: str, week: int, level: str = "intermediate") -> dict:
    """The week's sets, reps and rest, adjusted for training age.

    Level used to gate WHICH exercises were eligible and nothing else, so a
    beginner and an advanced lifter on muscle gain both got 3x8-10 in week 1 —
    identical volume for someone in their first month and someone in their tenth
    year. The knowledge base carries per-level prescriptions and nothing read
    them; they are the same boilerplate on 873 of 904 rows, so this adjusts the
    goal table rather than trusting them.
    """
    table = _GOAL_WEEKS.get(goal, _GOAL_WEEKS["general_fitness"])
    rx = dict(table[min(week - 1, 3)])
    delta = _LEVEL_SET_DELTA.get(level, 0)
    rx["sets"] = max(_MIN_SETS, min(_MAX_SETS, int(rx["sets"]) + delta))
    # Week 1's rest, carried through the block. The goal tables shorten rest week
    # over week to raise metabolic demand, which is right for the tiers that can
    # be squeezed and wrong for the lift the block is built around: muscle gain
    # peaked at five sets of ten-to-twelve with SIXTY seconds between them, while
    # simultaneously instructing the practitioner to add weight. A main lift's
    # rest is set by the load it is carrying, and the load only goes up.
    rx["base_rest_seconds"] = int(table[0]["rest_seconds"])
    return rx


# ── Exercise roles within a session ───────────────────────────────────────────
# The goal prescription was applied to every exercise in the day, identically —
# 95% of generated sessions gave the same sets, reps AND rest to all of their
# work. A barbell squat and a cable crossover both came out 3x8-10 with 90
# seconds between sets. No coach writes a session that way, and it is the single
# clearest tell that a plan was generated rather than programmed.
#
# A session has a shape. The first movement is the heaviest thing the day does,
# it gets the most sets and the longest rest, and it is the lift the four-week
# progression is actually about. What follows supports it, at lower load and
# higher reps. What finishes is isolation, which needs neither three minutes nor
# three-rep sets.
#
# The goal table stays the source of truth — it is what makes a set a strength
# set or an endurance set, and it is what periodises across the four weeks. The
# roles shift it.
_ROLE_ORDER = ("primary", "secondary", "accessory", "conditioning")

_ROLE_SETS = {"primary": +1, "secondary": 0, "accessory": -1}
_ROLE_REST = {"primary": 1.0, "secondary": 0.75, "accessory": 0.5}
_ACCESSORY_MAX_SETS = 4

# How long a set needs before the next one is a floor under the movement, not a
# property of the goal. Fat loss and endurance rest 30 and 20 seconds in their
# peak weeks, and scaling that down for accessories put every role at the same
# number — a heavy compound and a cable curl separated by nothing. A main lift
# gets a minute whatever the block is trying to do; the goal's own rest interval
# then periodises the tiers that can afford to be squeezed, which is how a
# metabolic block is written anyway.
_ROLE_MIN_REST = {"primary": 60, "secondary": 40, "accessory": 20}

_ROLE_LABEL = {
    "primary": "Main lift",
    "secondary": "Secondary",
    "accessory": "Accessory",
    "conditioning": "Conditioning",
}

# Movements that can carry a day. A compound in one of these patterns is doing
# the session's real work; a compound outside them (a shrug, a face pull) is not
# a lift you build a month around.
_PRIMARY_PATTERNS = {"squat", "hinge", "lunge", "push_h", "push_v", "pull_v", "pull_h", "carry"}


def _parse_reps(reps):
    """(lo, hi) for a rep range, or None if the prescription is not in reps."""
    digits = [p.strip() for p in str(reps).replace("\u2013", "-").split("-")]
    if not digits or not all(d.isdigit() for d in digits):
        return None
    nums = [int(d) for d in digits]
    return nums[0], nums[-1]


def _rep_delta(hi: int, role: str) -> int:
    """How far up the rep range a supporting movement sits.

    Scaled against the goal, not fixed: adding five reps to a 3-5 strength set
    makes it an accessory set, and adding five to a 15-20 endurance set makes it
    a set of 25 that nobody asked for.
    """
    if role == "primary":
        return 0
    if role == "secondary":
        return 2
    return 5 if hi <= 8 else (3 if hi <= 12 else 2)


def _role_prescription(rx: dict, role: str) -> dict:
    """The goal's week prescription, shifted for what this exercise is doing."""
    sets = int(rx.get("sets", 3)) + _ROLE_SETS.get(role, 0)
    if role == "accessory":
        sets = min(sets, _ACCESSORY_MAX_SETS)
    sets = max(_MIN_SETS, min(_MAX_SETS, sets))

    reps = rx.get("reps", "10-12")
    parsed = _parse_reps(reps)
    if parsed:
        delta = _rep_delta(parsed[1], role)
        reps = f"{parsed[0] + delta}-{parsed[1] + delta}" if delta else reps

    rest = int(rx.get("rest_seconds", 60)) * _ROLE_REST.get(role, 1.0)
    floor = _ROLE_MIN_REST.get(role, 40)
    if role == "primary":
        floor = max(floor, int(rx.get("base_rest_seconds", 0)))
    rest = max(floor, int(rest / 5 + 0.5) * 5)
    return {"sets": sets, "reps": reps, "rest_seconds": rest}


def _assign_roles(selected: list, primary_slots: int) -> list:
    """Label each selected exercise with the job it does in the session."""
    roles = []
    taken = 0
    for ex in selected:
        if ex.get("category") == "cardio":
            roles.append("conditioning")
        elif (taken < primary_slots
              and _is_compound(ex) and _movement_pattern(ex) in _PRIMARY_PATTERNS):
            roles.append("primary")
            taken += 1
        elif _is_compound(ex):
            roles.append("secondary")
        else:
            roles.append("accessory")
    # An arms day and a core day hold no big compound, and that is the truth
    # about them — they are accessory work. But something has to lead, so the
    # first movement is promoted to the middle tier rather than being given a
    # main lift's three-minute rest.
    if roles and "primary" not in roles:
        for i, r in enumerate(roles):
            if r == "accessory":
                roles[i] = "secondary"
                break
    return roles


def _primary_slots(target: int) -> int:
    """One main lift in a short session, two once there is room to support them."""
    return 2 if target >= 5 else 1


def _role_at(index: int, primary_slots: int) -> str:
    """The role of the nth exercise in a session, for costing it before it exists."""
    if index < primary_slots:
        return "primary"
    return "secondary" if index < primary_slots + 1 else "accessory"


# ── Weight / Load Guidance ────────────────────────────────────────────────────
# (lo, hi) in kg. Dumbbell = per-hand weight. Cable/machine = stack weight.
# Female ranges are ~60-65% of male — reflects average population, not a ceiling.

_WEIGHT_GUIDE = {
    "barbell": {
        "chest":     {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (35,55),  "female": (20,35)},
                      "intermediate": {"male": (55,90), "female": (35,55)},
                      "advanced":  {"male": (90,140), "female": (55,85)}},
        "back":      {"untrained": {"male": (30,50),  "female": (20,35)},
                      "beginner":  {"male": (50,80),  "female": (30,50)},
                      "intermediate": {"male": (80,130), "female": (50,80)},
                      "advanced":  {"male": (130,200),"female": (80,120)}},
        "legs":      {"untrained": {"male": (30,50),  "female": (20,35)},
                      "beginner":  {"male": (50,80),  "female": (30,55)},
                      "intermediate": {"male": (80,130), "female": (50,85)},
                      "advanced":  {"male": (130,200),"female": (80,130)}},
        "shoulders": {"untrained": {"male": (15,30),  "female": (8,18)},
                      "beginner":  {"male": (28,48),  "female": (15,30)},
                      "intermediate": {"male": (46,72), "female": (28,46)},
                      "advanced":  {"male": (70,100), "female": (44,68)}},
        "core":      {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (30,50),  "female": (15,30)},
                      "intermediate": {"male": (50,80), "female": (28,48)},
                      "advanced":  {"male": (80,120), "female": (46,72)}},
    },
    "dumbbell": {
        "chest":     {"untrained": {"male": (6,10),  "female": (3,6)},
                      "beginner":  {"male": (10,16), "female": (5,10)},
                      "intermediate": {"male": (16,26), "female": (8,16)},
                      "advanced":  {"male": (26,40), "female": (14,24)}},
        "back":      {"untrained": {"male": (8,12),  "female": (4,8)},
                      "beginner":  {"male": (12,20), "female": (6,12)},
                      "intermediate": {"male": (18,30), "female": (10,18)},
                      "advanced":  {"male": (28,44), "female": (16,28)}},
        "legs":      {"untrained": {"male": (8,14),  "female": (6,10)},
                      "beginner":  {"male": (12,20), "female": (8,14)},
                      "intermediate": {"male": (20,32), "female": (12,22)},
                      "advanced":  {"male": (30,50), "female": (18,34)}},
        "shoulders": {"untrained": {"male": (4,8),   "female": (2,5)},
                      "beginner":  {"male": (6,12),  "female": (3,8)},
                      "intermediate": {"male": (10,18), "female": (6,12)},
                      "advanced":  {"male": (18,28), "female": (10,18)}},
        "biceps":    {"untrained": {"male": (5,8),   "female": (2,5)},
                      "beginner":  {"male": (8,14),  "female": (4,8)},
                      "intermediate": {"male": (12,20), "female": (6,12)},
                      "advanced":  {"male": (18,30), "female": (10,18)}},
        "triceps":   {"untrained": {"male": (5,8),   "female": (2,5)},
                      "beginner":  {"male": (7,12),  "female": (3,7)},
                      "intermediate": {"male": (10,18), "female": (5,11)},
                      "advanced":  {"male": (16,26), "female": (9,17)}},
        "core":      {"untrained": {"male": (4,8),   "female": (2,5)},
                      "beginner":  {"male": (6,12),  "female": (3,7)},
                      "intermediate": {"male": (10,18), "female": (5,11)},
                      "advanced":  {"male": (16,26), "female": (9,17)}},
        "full_body": {"untrained": {"male": (6,10),  "female": (3,6)},
                      "beginner":  {"male": (8,14),  "female": (4,8)},
                      "intermediate": {"male": (12,22), "female": (6,14)},
                      "advanced":  {"male": (20,34), "female": (12,22)}},
    },
    "machine": {
        "chest":     {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (30,50),  "female": (15,28)},
                      "intermediate": {"male": (48,78), "female": (26,48)},
                      "advanced":  {"male": (76,120), "female": (44,72)}},
        "back":      {"untrained": {"male": (25,40),  "female": (14,24)},
                      "beginner":  {"male": (36,56),  "female": (20,36)},
                      "intermediate": {"male": (54,84), "female": (30,54)},
                      "advanced":  {"male": (82,130), "female": (50,82)}},
        "legs":      {"untrained": {"male": (30,55),  "female": (20,38)},
                      "beginner":  {"male": (50,85),  "female": (30,56)},
                      "intermediate": {"male": (82,130), "female": (52,86)},
                      "advanced":  {"male": (128,200),"female": (76,128)}},
        "shoulders": {"untrained": {"male": (14,28),  "female": (8,16)},
                      "beginner":  {"male": (24,44),  "female": (12,26)},
                      "intermediate": {"male": (40,68), "female": (22,42)},
                      "advanced":  {"male": (64,100), "female": (36,66)}},
    },
    "cable": {
        "chest":     {"untrained": {"male": (10,20),  "female": (5,12)},
                      "beginner":  {"male": (16,30),  "female": (8,18)},
                      "intermediate": {"male": (26,44), "female": (14,28)},
                      "advanced":  {"male": (40,64),  "female": (24,42)}},
        "back":      {"untrained": {"male": (15,26),  "female": (8,16)},
                      "beginner":  {"male": (22,38),  "female": (12,24)},
                      "intermediate": {"male": (34,56), "female": (18,36)},
                      "advanced":  {"male": (54,86),  "female": (32,56)}},
        "shoulders": {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (30,50),  "female": (18,32)}},
        "biceps":    {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (28,46),  "female": (16,30)}},
        "triceps":   {"untrained": {"male": (8,14),   "female": (4,8)},
                      "beginner":  {"male": (12,20),  "female": (6,12)},
                      "intermediate": {"male": (16,28), "female": (9,18)},
                      "advanced":  {"male": (24,40),  "female": (14,26)}},
        "core":      {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (28,46),  "female": (16,30)}},
        "legs":      {"untrained": {"male": (15,30),  "female": (10,20)},
                      "beginner":  {"male": (26,46),  "female": (16,30)},
                      "intermediate": {"male": (40,68), "female": (24,44)},
                      "advanced":  {"male": (64,100), "female": (38,66)}},
    },
    "kettlebell": {
        "full_body": {"untrained": {"male": (8,12),  "female": (4,8)},
                      "beginner":  {"male": (12,20), "female": (6,12)},
                      "intermediate": {"male": (20,32), "female": (10,20)},
                      "advanced":  {"male": (28,48), "female": (16,32)}},
        "legs":      {"untrained": {"male": (8,16),  "female": (6,10)},
                      "beginner":  {"male": (14,24), "female": (8,16)},
                      "intermediate": {"male": (22,36), "female": (14,24)},
                      "advanced":  {"male": (32,56), "female": (20,36)}},
    },
}

_BODYWEIGHT_PROGRESSIONS = {
    "chest":     "Bodyweight · Progress: easier (incline) → standard → decline → archer push-up → single-arm",
    "back":      "Bodyweight · Progress: band-assisted → negative → full pull-up/chin-up → weighted",
    "legs":      "Bodyweight · Progress: squat → split squat → Bulgarian split squat → pistol squat",
    "core":      "Bodyweight · Increase difficulty by slowing tempo or adding pauses",
    "shoulders": "Bodyweight · Add resistance band or light dumbbell when movement feels easy",
    "biceps":    "Bodyweight (band or towel row) · Add resistance band to increase difficulty",
    "triceps":   "Bodyweight · Progress: incline → flat → decline dips / push-up variations",
    "full_body": "Bodyweight · Increase reps first, then add load (weighted vest / resistance band)",
    "cardio":    "Effort-based · Increase duration or intensity (speed, incline) each week",
}


def _primary_muscle_group(ex: dict) -> str:
    """Map an exercise's primary muscle to a weight-guide key."""
    primary = [m.lower() for m in ex.get("primary_muscles", [])]
    for m in primary:
        if "chest" in m or "pectoral" in m:    return "chest"
        if "lat" in m or "back" in m or "trap" in m: return "back"
        if "quad" in m or "hamstring" in m or "glute" in m or "calf" in m or "leg" in m: return "legs"
        if "shoulder" in m or "deltoid" in m:  return "shoulders"
        if "bicep" in m:                        return "biceps"
        if "tricep" in m:                       return "triceps"
        if "abdominal" in m or "core" in m or "abs" in m: return "core"
    return "full_body"


def _get_weight_range(ex: dict, strength_level: str, gender: str) -> str:
    """Return a starter weight range string or bodyweight progression note."""
    eq = ex.get("equipment", "bodyweight").lower()
    cat = ex.get("category", "strength").lower()

    # Cardio and timed exercises don't need weight
    if cat == "cardio":
        return "Effort-based — see intensity note"

    # Bodyweight exercises: return progression ladder
    if eq in ("bodyweight", "other"):
        muscle = _primary_muscle_group(ex)
        return _BODYWEIGHT_PROGRESSIONS.get(muscle, "Bodyweight · Add band/vest to progress")

    # Map equipment aliases
    eq_key = eq
    if eq in ("dumbbells", "dumbbell"):      eq_key = "dumbbell"
    elif eq in ("barbell",):                  eq_key = "barbell"
    elif eq in ("machine",):                  eq_key = "machine"
    elif eq in ("cable", "cables"):           eq_key = "cable"
    elif eq in ("kettlebell", "kettlebells"): eq_key = "kettlebell"
    elif eq in ("bands", "resistance_bands"): return "Light–heavy band · choose resistance that makes last 2 reps challenging"
    else:                                     return "Moderate resistance · adjust to feel challenging by last rep"

    muscle = _primary_muscle_group(ex)
    gender_key = "female" if str(gender).lower() in ("female", "f", "woman") else "male"
    lvl = strength_level if strength_level in ("untrained", "beginner", "intermediate", "advanced") else "beginner"

    equip_data = _WEIGHT_GUIDE.get(eq_key, {})
    # Try exact muscle, then fall back to full_body or chest
    muscle_data = equip_data.get(muscle) or equip_data.get("full_body") or equip_data.get("chest")
    if not muscle_data:
        return "Moderate weight · adjust so last 2 reps are challenging"

    level_data = muscle_data.get(lvl, {})
    lo, hi = level_data.get(gender_key, (0, 0))
    if lo == 0:
        return "Moderate weight · adjust so last 2 reps are challenging"

    unit_note = " per hand" if eq_key == "dumbbell" else ""
    return f"{lo}–{hi} kg{unit_note} · adjust so last 2 reps are hard but form stays perfect"


# ── Ayurvedic Rest Day Recovery ───────────────────────────────────────────────

_REST_DAY_RECOVERY = {
    "vata": {
        "title": "Vata Rest Day — Ground & Restore",
        "activities": [
            "Abhyanga (warm sesame oil self-massage) — 15–20 min, long slow strokes toward the heart",
            "Restorative yoga — Child's Pose, Supta Baddha Konasana, Legs-Up-The-Wall (5 min each)",
            "Nadi Shodhana pranayama — 10 min alternate nostril breathing to calm the nervous system",
            "Warm herbal bath with calming herbs (Ashwagandha, Brahmi, or Jatamansi)",
            "Light walk (20–30 min) in nature, preferably midday when Vata is naturally pacified",
        ],
        "nutrition_note": "Warm, oily, nourishing foods. Ghee, warm milk, root vegetables. Avoid cold, raw, or dry foods on rest days.",
        "sleep_note": "Aim for 8–9 hrs. Apply warm oil to feet (Padabhyanga) before bed. Asleep by 10pm.",
        "ayurvedic_note": "Vata recovers through stillness and warmth — resist the urge to stay active on rest days.",
    },
    "pitta": {
        "title": "Pitta Rest Day — Cool & Release",
        "activities": [
            "Moon salutation sequence — 3–5 rounds, slow and cooling (opposite of Sun Salutation's heat)",
            "Coconut oil self-massage — focus on scalp and soles of feet to dissipate excess heat",
            "Sheetali pranayama (cooling breath through rolled tongue) — 10 min",
            "Swimming or gentle water activity — Pitta is cooled by water",
            "Evening walk at sunset — avoid direct midday sun on rest days",
        ],
        "nutrition_note": "Cooling, sweet, bitter foods. Coconut water, pomegranate, fresh coriander, mint. Avoid spicy, sour, salty foods.",
        "sleep_note": "Aim for 7–8 hrs. Keep bedroom cool (below 22°C). Avoid screen heat before bed.",
        "ayurvedic_note": "Pitta's drive to push harder on rest days is the enemy — active recovery should feel cooling, not challenging.",
    },
    "kapha": {
        "title": "Kapha Rest Day — Energise & Stimulate",
        "activities": [
            "Brisk walk — minimum 30 min at vigorous pace (Kapha needs movement even on rest days)",
            "Dry brushing (Garshana with raw silk gloves) — stimulates lymphatic circulation",
            "Kapalabhati pranayama — 5–10 min energising breath (fires up Agni and reduces Ama)",
            "Sun salutations — 5 rounds at moderate pace to maintain metabolic rate",
            "Avoid all napping — daytime sleep strongly aggravates Kapha",
        ],
        "nutrition_note": "Light, warm, spiced foods. Ginger-lemon tea, light dal, steamed vegetables. Avoid heavy, oily, cold, or sweet foods.",
        "sleep_note": "7 hrs maximum. Wake before 6am — the Kapha period (6-10am) brings heaviness if you sleep through it.",
        "ayurvedic_note": "Kapha's rest day is still active — complete stillness leads to lethargy and weight gain for this type.",
    },
}


# ── Medical-condition → exercise-contraindication mapping ─────────────────────
# The exercise KB already tags exercises with condition contraindications
# (hypertension, heart_disease, osteoporosis, herniated_disc, cervical_spondylosis…),
# but filter_exercises historically only checked INJURIES — so a hypertensive or
# cardiac user got no exercise gating. We now expand the user's medical_history into
# these tags. Most match directly; this map covers stored/lay variants that don't.
_CONDITION_TO_EXERCISE_CONTRA: dict[str, list[str]] = {
    "high_blood_pressure": ["hypertension"], "high_bp": ["hypertension"], "bp": ["hypertension"],
    "raised_bp": ["hypertension"],
    "coronary_artery_disease": ["heart_disease"], "cad": ["heart_disease"],
    "cardiac": ["heart_disease"], "cardiovascular_disease": ["heart_disease"],
    "heart_condition": ["heart_disease", "heart_condition"],
    "atrial_fibrillation": ["heart_disease"], "arrhythmia": ["heart_disease"],
    "congestive_heart_failure": ["heart_disease"], "angina": ["heart_disease"],
    "lumbar_spondylosis": ["lower_back_pain", "herniated_disc"],
    "ankylosing_spondylitis": ["lower_back_pain"],
    "sciatica": ["lower_back_pain", "herniated_disc"],
    "slipped_disc": ["herniated_disc"], "disc_herniation": ["herniated_disc"],
    "spondylolisthesis": ["lower_back_pain", "herniated_disc"],
    "cervical_radiculopathy": ["cervical_spondylosis", "neck_injury"],
    "osteopenia": ["osteoporosis"],
}


_SENIOR_AGE = 60
_YOUTH_AGE = 18
# The KB tags axial-loading and impact work with `osteoporosis`; it is the closest
# thing it has to a "loads the spine hard" mechanism.
_AGE_AVOID_TAGS = {"osteoporosis"}


def _age_group(age) -> str:
    try:
        age = int(age)
    except (TypeError, ValueError):
        return "adult"
    if age >= _SENIOR_AGE:
        return "senior"
    if age < _YOUTH_AGE:
        return "youth"
    return "adult"


def _condition_contra_tags(medical_history) -> set:
    """Expand a user's medical_history into exercise-contraindication tags.

    A condition contributes its own name (direct KB tags like 'hypertension' match
    as-is) plus any mapped variants. Used exactly like injury tags in filter_exercises."""
    tags: set = set()
    for c in medical_history or []:
        key = str(c).lower().strip().replace(" ", "_").replace("-", "_")
        if not key:
            continue
        tags.add(key)
        tags.update(_CONDITION_TO_EXERCISE_CONTRA.get(key, []))
    return tags


# ── Exercise filtering ────────────────────────────────────────────────────────

# Self-myofascial release — foam rolling. Named as a suffix throughout the
# dataset ("Adductors-Smr", "Peroneals-Smr"); the `-` matters, since `_MOVEMENT_
# PATTERNS` has to keep reading "Smith" and "Smr" apart.
_SMR_NAME = re.compile(r"-\s*smr\b", re.I)


def filter_exercises(user_profile, gym_prefs, exercises, extra_avoid_tags=None):
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")

    # Beginners get beginner + intermediate exercises. The source dataset labels
    # only ~5% of exercises 'beginner' (almost all foundational lifts — bench
    # press, rows, shoulder press — are tagged 'intermediate'), so a beginner-only
    # gate leaves push/pull days with zero chest/back/shoulder options. Genuinely
    # advanced movements (Olympic lifts, plyometrics, elite gymnastics) are tagged
    # 'advanced' in the KB and stay excluded; the scoring pass below still prefers
    # beginner-level exercises so the simplest movements surface first.
    level_map = {
        "beginner":     ["beginner", "intermediate"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    user_level = user_profile.get("fitness_level", "beginner") or "beginner"
    allowed_levels = level_map.get(user_level, ["beginner", "intermediate"])

    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    gym_goal = gym_prefs.get("gym_goal", "general_fitness")
    # Injuries AND medical conditions both gate exercises against the KB's
    # contraindication tags (heart_disease, hypertension, osteoporosis, herniated_disc…).
    avoid_tags = set(user_profile.get("injuries_or_limitations") or [])
    avoid_tags |= _condition_contra_tags(user_profile.get("medical_history") or [])
    # LLM-supplied contraindication tags for rare conditions (validated to the KB
    # vocabulary), merged into the same tag gate.
    avoid_tags |= {str(t).lower() for t in (extra_avoid_tags or [])}
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)

    # Age was not an input to this filter at all: a 65-year-old received a plan
    # identical to a 30-year-old's — same exercises, same loads, same volume. The
    # yoga engine caps seniors at beginner level and blanket-excludes fall risk,
    # intracranial pressure and neck load; both features read the same profile, so
    # the app was careful about a 70-year-old doing a shoulderstand and indifferent
    # to the same person doing a barbell back squat.
    #
    # `osteoporosis` is the KB's own proxy for axial loading and impact — it tags
    # the cleans, the bounds, the Atlas stones, 155 exercises in all. Bone density
    # is declining by 60 whether or not anyone has said so, which is the reasoning
    # the yoga engine already uses for its blanket senior exclusions.
    age_group = _age_group(user_profile.get("age"))
    if age_group in ("senior", "youth"):
        allowed_levels = [lv for lv in allowed_levels if lv != "advanced"]
        avoid_tags = avoid_tags | _AGE_AVOID_TAGS

    scored = []
    for ex in exercises:
        eq = ex.get("equipment", "bodyweight").lower()
        if eq not in available_eq and eq != "bodyweight":
            continue
        if ex.get("level", "intermediate") not in allowed_levels:
            continue
        # Plyometrics are never a beginner's first month. The level allowance
        # above hands beginners the intermediate tier deliberately, because the
        # dataset files foundational lifts — bench press, rows, shoulder press —
        # as intermediate; jump training is not what that allowance was for, and
        # NOT ONE of the 25 plyometrics is rated beginner (16 intermediate, 9
        # advanced). Before this a beginner asking for endurance was served
        # Rocket Jump and Freehand Jump Squat nine times each over four weeks,
        # because "endurance" resolved to cardio plus plyometrics and nothing
        # else.
        if user_level == "beginner" and ex.get("category") == "plyometrics":
            continue
        # A stretch is not a set of eight, and foam rolling is not a lift. The
        # dataset carries 51 stretches and 13 self-myofascial-release entries
        # ("Brachialis-Smr", "Latissimus Dorsi-Smr"), and nothing separated them
        # from training movements — so 20% of generated days prescribed one as
        # main work: "Calves-Smr — 3 sets of 8-12, 90s rest, 82-130 kg". The
        # thirteen SMR rows were filed as `strength` in the dataset, which is
        # how they reached a chest day at all; that is corrected too, so a
        # future reader of the category alone is not misled.
        #
        # Mobility work belongs to the session — it is what `_WARMUP` and
        # `_COOLDOWN` are, written per focus and timed in seconds.
        if ex.get("category") == "stretching" or _SMR_NAME.search(ex.get("name", "")):
            continue
        # Jump training is the wrong risk for a 65-year-old and for a body still
        # growing, whatever level they enter.
        if age_group in ("senior", "youth") and ex.get("category") == "plyometrics":
            continue
        if not ex.get("goal_suitability", {}).get(gym_goal, False):
            continue
        if avoid_tags.intersection(set(ex.get("contraindications", []))):
            continue
        # Pregnancy is described TWICE in the KB — a `pregnancy_safe` boolean and
        # a `pregnancy` contraindication token — and this read only the boolean.
        # Ten exercises say both, and disagree: `pregnancy_safe: true` beside
        # `contraindications: [... "pregnancy"]`. All ten are abdominal (Toe
        # Touchers, Scissor Kick, Hanging Leg Raise, Stomach Vacuum…), so the
        # ones a pregnant practitioner most needs kept away were the ones the
        # flag waved through: a pregnant beginner's four-week plan served Toe
        # Touchers eight times and Seated Leg Tucks seven.
        #
        # The yoga engine has always read both (`filter_poses`, the
        # `"pregnancy" in pose_preg_tags` branch), which is why the same
        # contradiction in the pose KB was harmless. Either field saying no is a
        # no, in both engines. The data is corrected as well, so a future reader
        # of one field alone is not trapped by the other.
        if is_pregnant and (not ex.get("pregnancy_safe", False)
                            or "pregnancy" in set(ex.get("contraindications", []))):
            continue

        score = 0
        dosha_suit = ex.get("dosha_suitability", {}).get(dominant_dosha, "moderate")
        if dosha_suit == "good":     score += 2
        elif dosha_suit == "moderate": score += 1
        elif dosha_suit == "avoid":  score -= 2
        if user_level == "beginner" and ex.get("level") == "beginner":
            score += 1
        scored.append((score, ex))

    scored.sort(key=lambda x: x[0], reverse=True)
    return _cut_pool(scored)


# The library is cut down before selection ever sees it. It used to be a single
# global "best 200 by dosha score", which reads like a preference and behaves
# like a ban: the score gap between `good` (+2) and `avoid` (-2) is wider than
# the pool is deep, so anything scored below the top band was not demoted, it was
# deleted. Every one of the 179 barbell exercises was tagged `pitta: avoid`
# (the tag was derived from the EQUIPMENT, not the movement), and the result was
# that a Vata or Pitta practitioner asking for a strength programme with a full
# gym never saw a barbell squat, deadlift, bench press, row or overhead press.
# Two thirds of users, and the whole foundation of strength training.
#
# The data is corrected — a barbell is a tool and carries no dosha — but the
# mechanism is what made a mislabel fatal, so it is the mechanism that changes.
# The cut is now taken per muscle group, and inside each group the compounds are
# taken first: no scoring rule, present or future, can empty a muscle group or
# strip a group of the movements that train it hardest. Dosha suitability still
# orders what fills the remaining room, which is what a preference does.
_POOL_PER_MUSCLE = 40
_POOL_COMPOUNDS_PER_MUSCLE = 14


def _cut_pool(scored: list) -> list:
    by_muscle: dict = {}
    for _, ex in scored:
        by_muscle.setdefault(_muscle_key(ex), []).append(ex)

    pool = []
    for items in by_muscle.values():
        chosen = [ex for ex in items if _is_compound(ex)][:_POOL_COMPOUNDS_PER_MUSCLE]
        seen = {ex["id"] for ex in chosen}
        for ex in items:
            if len(chosen) >= _POOL_PER_MUSCLE:
                break
            if ex["id"] not in seen:
                chosen.append(ex)
                seen.add(ex["id"])
        pool.extend(chosen)
    return pool


# ── Muscle group split ────────────────────────────────────────────────────────

_MUSCLE_KEYS = ["chest", "triceps", "biceps", "back", "shoulders",
                "legs", "core", "full_body", "cardio"]


def _muscle_key(ex) -> str:
    """The one bucket an exercise belongs to, for splitting AND for budgeting.

    The day builder needs to ask an exercise which muscle it trains — to stop a
    chest day filling up with triceps — and the splitter already knew. It was
    inline in the loop, so there was no way to ask.
    """
    if ex.get("category") == "cardio":
        return "cardio"
    for m in (mm.lower() for mm in ex.get("primary_muscles", [])):
        if "chest" in m or "pectoral" in m:
            return "chest"
        if "tricep" in m:
            return "triceps"
        if "bicep" in m:
            return "biceps"
        if m in ("lats", "middle back", "lower back", "traps", "back"):
            return "back"
        if "shoulder" in m or "deltoid" in m:
            return "shoulders"
        if m in ("quadriceps", "hamstrings", "glutes", "calves", "adductors",
                 "abductors", "legs", "quad", "calf"):
            return "legs"
        if "abdominal" in m or "core" in m or "abs" in m or "hip flex" in m:
            return "core"
    return "full_body"


def split_by_muscle_group(exercises):
    split = {k: [] for k in _MUSCLE_KEYS}
    for ex in exercises:
        split[_muscle_key(ex)].append(ex)
    return split


# ── Weekly schedule builder ───────────────────────────────────────────────────

def _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level):
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
        # Was chest_triceps / back_biceps / legs / shoulders / arms — which hits the
        # triceps on Monday and again on Friday, and the biceps on Tuesday and again
        # on Friday, while the chest and the back get one day each. Weekly volume
        # came out 18 sets of triceps against 12 of chest. Once the week is long
        # enough to afford a dedicated arm day, the arms come OFF the push and pull
        # days; that is what the arm day is for.
        return ["chest", "back", "legs", "shoulders", "arms", "core_cardio", "rest"]
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


# One exercise a week moves; the rest of the day is the same work as last week.
_ROTATING_PER_DAY = 1

# A compound trains several muscles under one load and is where the session's
# value is. The dataset has no such flag, so it is read off the movement's name
# and how many muscles it lists as secondary.
_COMPOUND_NAME = re.compile(
    r"\b(squat|deadlift|press|row|pull-?up|chin-?up|dip|lunge|clean|snatch|"
    r"thruster|push-?up|step-?up|hip thrust|carry|swing)\b", re.I)

# Words that name a VARIANT rather than a movement. Stripping them leaves the
# movement family, so "Incline Dumbbell Press" and "Decline Barbell Press" are
# recognisably the same thing and do not both land in one session.
_VARIANT_WORDS = re.compile(
    r"\b(incline|decline|seated|standing|lying|kneeling|machine|cable|smith|"
    r"barbell|dumbbell|kettlebell|band|bands|resistance|alternate|alternating|"
    r"single|one|two|arm|arms|leg|legs|close|wide|narrow|reverse|neutral|hammer|"
    r"weighted|assisted|bodyweight|floor|bench|preacher|prone|supine|front|back|"
    r"side|rear|overhead|underhand|overhand|grip|medium|with|and|the|on|to|of|a|"
    r"pronated|supinated|low|high|flat|straight|bent|full|half|partial|v|smr)\b",
    re.I)
_MAX_PER_FAMILY = 2
# Two compounds in a five-exercise day, one in a three. A session built of
# isolation work trains the same muscles for less, and the first pick being a
# compound is not enough on its own — the audit's week-one chest day had a
# machine press and then four accessories.
_MIN_COMPOUNDS = 2


# What the movement DOES, as against which muscle it names. A legs day of step-ups,
# calf press, glute kickback and flutter kicks satisfies "two compounds" and still
# never asks the practitioner to squat or to hinge at the hip — the two patterns
# that carry most of what leg training is for. Ordered longest-match-first, since
# "split squat" is a lunge and "leg press" is a squat.
_MOVEMENT_PATTERNS = (
    # `(?:e?s)?` on every alternative: `\b` fails before the plural, so "Step Ups",
    # "Lunges", "Dips" and "Crunches" all fell through to isolation and a leg day
    # could satisfy its lunge slot with none of them.
    # Calf work names the machine it is done on ("Calf Press On The Leg Press
    # Machine"), so it has to be recognised before the leg-press rule sees it.
    ("isolation", re.compile(r"\b(calf|toe raise)(?:e?s)?\b", re.I)),
    ("lunge",  re.compile(r"\b(lunge|split squat|step.?up|bulgarian)(?:e?s)?\b", re.I)),
    ("squat",  re.compile(r"\b(squat|leg press|hack|sissy|wall sit)(?:e?s)?\b", re.I)),
    ("hinge",  re.compile(r"\b(deadlift|good morning|hip thrust|glute bridge|back extension|"
                          r"romanian|swing|clean|snatch|pull.?through|hyperextension)(?:e?s)?\b", re.I)),
    ("push_v", re.compile(r"\b(shoulder press|overhead press|military|arnold|handstand|"
                          r"pike push|upright row|lateral raise|front raise)(?:e?s)?\b", re.I)),
    ("push_h", re.compile(r"\b(bench press|chest press|push.?up|fly|flye|dip|pec deck|"
                          r"butterfly|crossover)(?:e?s)?\b", re.I)),
    ("pull_v", re.compile(r"\b(pull.?up|chin.?up|pulldown|lat pull)(?:e?s)?\b", re.I)),
    ("pull_h", re.compile(r"\b(row|face pull|rear delt|shrug)(?:e?s)?\b", re.I)),
    ("carry",  re.compile(r"\b(carry|farmer)(?:e?s)?\b", re.I)),
    ("core",   re.compile(r"\b(crunch|plank|sit.?up|leg raise|twist|bicycle|hollow|"
                          r"dead bug|bird dog)(?:e?s)?\b", re.I)),
)

# What each day should try to cover, in priority order. These are PREFERENCES, not
# requirements: a bodyweight-only library holds two squats and two hinges in total,
# so a quota that had to be met would either fail or reach past the equipment the
# practitioner actually has.
_FOCUS_PATTERNS = {
    "legs":            ("squat", "hinge", "lunge"),
    "legs_core":       ("squat", "hinge", "core"),
    "push":            ("push_h", "push_v"),
    # Not push_v: a chest/triceps day's pool holds no overhead press, because the
    # muscle split files those under shoulders. Asking for a pattern the day cannot
    # contain is a quota that fails 43% of the time and teaches nothing.
    "chest":           ("push_h",),
    "chest_triceps":   ("push_h",),
    "pull":            ("pull_v", "pull_h"),
    "back":            ("pull_v", "pull_h"),
    "back_biceps":     ("pull_v", "pull_h"),
    "shoulders":       ("push_v", "pull_h"),
    "shoulders_core":  ("push_v", "core"),
    "shoulders_arms":  ("push_v",),
    "full_body":       ("squat", "push_h", "pull_h", "hinge"),
    "core_cardio":     ("core",),
    "arms":            (),
}


# How the day's slots are shared out between the muscles it names.
#
# The pool was the concatenation of the day's muscle groups, and selection drew
# from it without ever asking which muscle an exercise trained — so a day filled
# up with whichever muscle the dataset happens to hold the most of. The library
# carries 90 triceps movements and 68 chest, and it showed: a Chest & Triceps day
# came out three chest and five triceps, and across a four-day week the
# practitioner accumulated 13 sets of triceps against 6 of chest. The day was
# named for the muscle it trained least.
#
# Weights, not counts — they are scaled to whatever the session's length affords.
# The muscle the day is NAMED for gets the majority; the arm or the core it is
# paired with is there to finish it off.
_FOCUS_ALLOCATION = {
    "full_body":       (("legs", 3), ("chest", 2), ("back", 2), ("shoulders", 1), ("core", 1)),
    "push":            (("chest", 3), ("shoulders", 2), ("triceps", 1)),
    "pull":            (("back", 3), ("biceps", 1)),
    "legs":            (("legs", 1),),
    "legs_core":       (("legs", 3), ("core", 1)),
    "chest_triceps":   (("chest", 2), ("triceps", 1)),
    "back_biceps":     (("back", 2), ("biceps", 1)),
    "chest":           (("chest", 1),),
    "back":            (("back", 1),),
    "shoulders":       (("shoulders", 1),),
    "shoulders_core":  (("shoulders", 2), ("core", 1)),
    "shoulders_arms":  (("shoulders", 2), ("biceps", 1), ("triceps", 1)),
    "arms":            (("biceps", 1), ("triceps", 1)),
    "core_cardio":     (("core", 2), ("cardio", 1)),
}


def _slot_allocation(focus: str, target: int) -> dict:
    """Per-muscle slot ceilings for a day of `target` exercises.

    Ceilings, not quotas — a bodyweight library holds four biceps movements in
    total, and a day that had to fill its quota would reach past the equipment
    the practitioner actually has. The fallback pass in `_choose` ignores these
    for the same reason it ignores the family cap: a session has to exist.
    """
    weights = _FOCUS_ALLOCATION.get(focus)
    if not weights or len(weights) == 1:
        return {}
    total = sum(w for _, w in weights)
    caps = {}
    for key, w in weights:
        caps[key] = max(1, int(target * w / total + 0.5))
    # Rounding can leave the day a slot short of its own length; the muscle the
    # day is named for absorbs it.
    shortfall = target - sum(caps.values())
    if shortfall > 0:
        caps[weights[0][0]] += shortfall
    return caps


def _movement_pattern(ex) -> str:
    name = ex.get("name", "")
    for pattern, rx in _MOVEMENT_PATTERNS:
        if rx.search(name):
            return pattern
    return "isolation"


def _is_compound(ex) -> bool:
    return (bool(_COMPOUND_NAME.search(ex.get("name", "")))
            or len(ex.get("secondary_muscles") or []) >= 2)


def _singular(word: str) -> str:
    """`flyes`, `flye` and `fly` are one movement; the family cap could not see it.

    Plurals were left alone, so `Incline Cable Flye` and `Flat Bench Cable Flyes`
    counted as two different families and a chest day came out four fly variants
    deep — under the cap, twice over.
    """
    if len(word) > 3 and word.endswith("es") and not word.endswith("ses"):
        word = word[:-2]
    elif len(word) > 2 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word[:-1] if len(word) > 2 and word.endswith("e") else word


def _movement_family(ex) -> str:
    """`Incline Dumbbell Press` and `Decline Barbell Press` → `press`."""
    core = _VARIANT_WORDS.sub(" ", ex.get("name", ""))
    core = re.sub(r"[^A-Za-z ]", " ", core).lower().split()
    return " ".join(_singular(w) for w in core[-2:]) if core else ex.get("id", "")


def _choose(pool, n, seed_key, taken_ids, families, min_compounds=0, patterns=(),
            caps=None, per_muscle=None):
    """Pick n exercises, compounds first, without stacking one movement family.

    Selection was a plain shuffle-and-take, so nothing preferred a compound or
    noticed that it had chosen five variants of the same thing. Measured over 240
    generated days, 12-44% contained NO compound movement at all, and a week-one
    chest session came out as two flye variants, a pullover, a machine press and
    a dip machine — no flat press anywhere.
    """
    ordered = _deterministic_select(pool, len(pool), seed_key)
    picked = []
    caps = caps or {}
    per_muscle = per_muscle if per_muscle is not None else {}

    def _take(ex):
        picked.append(ex)
        taken_ids.add(ex["id"])
        families[_movement_family(ex)] += 1
        per_muscle[_muscle_key(ex)] = per_muscle.get(_muscle_key(ex), 0) + 1

    def _blocked(ex) -> bool:
        if families[_movement_family(ex)] >= _MAX_PER_FAMILY:
            return True
        key = _muscle_key(ex)
        return key in caps and per_muscle.get(key, 0) >= caps[key]

    # One exercise for each of the day's movement patterns, before anything else
    # competes for the slots. A leg day came out as step-ups, calf press, glute
    # kickback and flutter kicks — two compounds by the letter of the rule, and
    # nothing that squats or hinges.
    for pattern in patterns:
        if len(picked) >= n:
            break
        # Compound first. `push_h` covers the bench press AND the pec deck, and
        # taking whichever surfaced first meant a chest day's horizontal-push
        # slot could be filled by a cable crossover — leaving the session with
        # no main lift at all, which is what happened to one chest day in eight.
        candidates = [ex for ex in ordered
                      if ex["id"] not in taken_ids and _movement_pattern(ex) == pattern
                      and not _blocked(ex)]
        candidates.sort(key=lambda ex: not _is_compound(ex))
        if candidates:
            _take(candidates[0])

    for want_compound in (True, False):
        if want_compound and min_compounds <= 0:
            continue
        have_compounds = sum(1 for ex in picked if _is_compound(ex))
        for ex in ordered:
            if want_compound and have_compounds >= min_compounds:
                break
            if len(picked) >= n:
                break
            if ex["id"] in taken_ids or _is_compound(ex) is not want_compound:
                continue
            if _blocked(ex):
                continue
            _take(ex)
            have_compounds += _is_compound(ex)

    # Two fallbacks, in the order the constraints matter. Variant variety is the
    # cheaper of the two: a chest day whose pressing families are exhausted should
    # take a third press before it takes a fifth triceps movement. Dropping both
    # caps at once let the muscle budget be overrun by whichever group the dataset
    # happens to hold more of — the exact imbalance the budget exists to close.
    if len(picked) < n:
        for ex in ordered:
            if len(picked) >= n:
                break
            key = _muscle_key(ex)
            if ex["id"] in taken_ids or (key in caps and per_muscle.get(key, 0) >= caps[key]):
                continue
            _take(ex)

    # A pool too small or too uniform to respect either cap still has to produce a
    # session; both are preferences, not safety rules.
    if len(picked) < n:
        for ex in ordered:
            if len(picked) >= n:
                break
            if ex["id"] in taken_ids:
                continue
            _take(ex)
    return picked


def _select_for_day(pool, target, user_id, focus, day_num, week):
    """The day's exercises: a stable core, plus one that rotates weekly.

    The seed used to include the week, so every week drew a fresh random set —
    week 1 and week 2 of the same focus day shared 0 to 20% of their exercises.
    Meanwhile that week's own coaching note told the practitioner "same weight as
    W1, push for extra reps" and "add 2.5-5 kg vs Week 1 on main lifts". You
    cannot add 2.5 kg to a lift you are not doing, so the four-week periodisation
    — otherwise the best-built thing in this engine — was decoration.

    Progressive overload needs the same movement to come back. One rotating slot
    keeps a month from going stale without costing the other exercises their
    history. The core is seeded on the DAY, never the week, so it holds across all
    four; the same shape as the yoga engine's core and accent split.
    """
    import collections as _collections

    core_n = max(1, target - _ROTATING_PER_DAY)
    taken: set = set()
    families: dict = _collections.defaultdict(int)
    # The ceilings are for the whole day, so the stable core and the rotating slot
    # share one running count — otherwise the rotating exercise gets a fresh
    # budget and reopens the imbalance the ceilings exist to close.
    caps = _slot_allocation(focus, target)
    per_muscle: dict = {}

    core = _choose(pool, core_n, f"{user_id}-{focus}-d{day_num}-core",
                   taken, families, min_compounds=min(_MIN_COMPOUNDS, max(1, core_n - 1)),
                   patterns=_FOCUS_PATTERNS.get(focus, ()),
                   caps=caps, per_muscle=per_muscle)
    rotating = _choose(pool, target - len(core), f"{user_id}-{focus}-d{day_num}-rotate-w{week}",
                       taken, families, caps=caps, per_muscle=per_muscle)
    return core + rotating


# Below this the week is the same handful of exercises repeated, which the plan
# should say rather than imply. Bodyweight + endurance lands at 16.
_THIN_POOL = 20


# Warm-up and cool-down are written per focus (`_WARMUP` / `_COOLDOWN`), five or
# six movements each. Nine minutes is what they take at a sane pace, and the
# exercise budget is what is left after them.
_OVERHEAD_SECONDS = 9 * 60
# Rest between sets is not lying down, and a warm-up is real work. Both were
# counted as zero.
_REST_KCAL_PER_MINUTE = 2.0
_WARMUP_KCAL_PER_MINUTE = 4.0
_MIN_EXERCISES = 3
_MAX_EXERCISES = 8
_SECONDS_PER_REP = 4


def _reps_to_seconds(reps, sets: int) -> int:
    """Time under tension for one exercise, across all its sets."""
    digits = [int(p) for p in str(reps).replace("\u2013", "-").split("-") if p.strip().isdigit()]
    avg_reps = sum(digits) / len(digits) if digits else 10
    return int(sets * (avg_reps * _SECONDS_PER_REP))


def _target_count(duration, goal, rx=None):
    """How many exercises fit in the session the user asked for.

    This used to bucket duration into 3, 4 or 5 and stop, so a 45-minute and a
    60-minute request produced byte-identical sessions — the extra quarter hour
    bought nothing — and the plan reported back the REQUESTED length rather than
    the one it built: 26 minutes of work under a 60-minute heading.

    The count now comes off the clock, and the clock depends on the goal, because
    the goal sets the rest interval. Strength rests 180 seconds between sets and
    fits three or four exercises into an hour; fat loss rests 30 and fits eight.
    That is the arithmetic a coach does, and it is why one bucket cannot serve
    every goal.
    """
    if rx is None:  # legacy callers keep the old behaviour
        return 3 if duration <= 20 else (4 if duration <= 30 else 5)

    # Exercises no longer cost the same, so the count cannot come from dividing
    # the budget by one of them. A main lift resting three minutes is most of a
    # strength session; the accessories after it cost a third of that each. The
    # session is filled in the order it will be performed, and stops when the
    # next exercise would overrun the clock.
    budget = max(int(duration) * 60 - _OVERHEAD_SECONDS, 300)

    def _fits(primary_slots: int) -> int:
        spent = 0
        count = 0
        while count < _MAX_EXERCISES:
            r = _role_prescription(rx, _role_at(count, primary_slots))
            cost = _reps_to_seconds(r["reps"], r["sets"]) + r["sets"] * r["rest_seconds"]
            if spent + cost > budget and count >= _MIN_EXERCISES:
                break
            spent += cost
            count += 1
        return max(_MIN_EXERCISES, count)

    # How many main lifts the day gets depends on how long it is, and how long it
    # is depends on how many main lifts it gets. One pass settles it: cost the
    # session with a single main lift, and if it came out long enough to carry two,
    # cost it again.
    count = _fits(1)
    return _fits(2) if count >= 5 else count


# ── Day plan builder ──────────────────────────────────────────────────────────

# Below this the difference is absorbed by how briskly someone warms up. Above
# it, the session is a different length from the one they chose and should say so.
_DURATION_TOLERANCE = 0.15


def _duration_notice(built: int, requested: int, goal: str) -> str | None:
    """Say when the session is not the length that was asked for.

    Rest interval is set by the goal, and it dominates: strength rests three
    minutes between sets, so even the fewest exercises that can train a day's
    muscle groups overruns a half-hour slot. The honest move is the one the yoga
    engine makes — build the session the goal requires, and name the gap.
    """
    if not requested or abs(built - requested) / requested <= _DURATION_TOLERANCE:
        return None
    if built > requested:
        return (f"This session runs about {built} minutes rather than the {requested} you asked "
                f"for. At the {goal.replace('_', ' ')} rest intervals, fewer exercises than this "
                f"would leave the day's muscle groups untrained. Shorten the rests if you are "
                f"pressed for time — it changes the training effect, but it keeps the session.")
    return (f"This session runs about {built} minutes rather than the {requested} you asked for. "
            f"Adding exercises past this point stops being productive at these rest intervals — "
            f"take the extra time over the warm-up and cool-down, or add a walk.")


_TIME_UNITS = re.compile(r"\b(min|sec|minute|second)", re.I)


def _prescribe(ex: dict, rx: dict, level: str, role: str = "secondary"):
    """Sets, reps and rest for one exercise, in the job it is doing today.

    The goal prescription was applied to everything, so time-based work came out
    as repetitions: "Brisk Walking — 4 sets of 18-22 reps, 20s rest". The 21
    exercises whose own KB entry is written in minutes or seconds (treadmill,
    rowing machine, jump rope, plank-style holds) keep their own prescription;
    everything else takes the goal's, shifted for its role in the session.
    """
    own = (ex.get("sets_reps") or {}).get(level) or (ex.get("sets_reps") or {}).get("intermediate") or {}
    if own and _TIME_UNITS.search(str(own.get("reps", ""))):
        return int(own.get("sets", 1)), own.get("reps"), int(own.get("rest_seconds", 60))
    r = _role_prescription(rx, role)
    return r["sets"], r["reps"], r["rest_seconds"]


def _modification_for(ex: dict) -> str:
    """The coaching note shown under an exercise.

    873 of 904 rows carry the same generated string — "Reduce weight or switch to
    bodyweight if form breaks down" — including every bodyweight exercise and
    every stretch, where it appeared directly beneath a load field reading
    "Bodyweight". The 31 hand-written ones are kept; the boilerplate is replaced
    with something true of the equipment in question.
    """
    note = (ex.get("modification") or "").strip()
    if note and note != _BOILERPLATE_MODIFICATION:
        return note
    equipment = (ex.get("equipment") or "bodyweight").lower()
    if ex.get("category") == "stretching":
        return "Ease off the moment the stretch turns sharp — range comes from repetition, not force."
    if equipment in ("bodyweight", "bands"):
        return ("Slow the tempo or add a pause to make it harder; shorten the range or drop to "
                "knees if form breaks down.")
    return "Reduce the load if form breaks down — the last clean rep is the set, not the last rep."


_BOILERPLATE_MODIFICATION = "Reduce weight or switch to bodyweight if form breaks down."


def _focus_label(focus: str, main_workout: list) -> str:
    label = focus.replace("_", " ").title()
    if "cardio" in focus.lower() and not any(e.get("category") == "cardio" for e in main_workout):
        stripped = " ".join(w for w in label.split() if w.lower() != "cardio").strip()
        return stripped or "Conditioning"
    return label


def build_day_plan(day_num, day_name, focus, muscle_split, gym_prefs, user_profile,
                   week=1, user_id="default", strength_level="beginner", gender="male",
                   dosha="vata"):
    if focus == "rest":
        recovery = _REST_DAY_RECOVERY.get(dosha, _REST_DAY_RECOVERY["vata"])
        return {
            "day": day_num, "day_name": day_name,
            "focus": "Rest & Recovery", "type": "recovery",
            "warmup": [], "main_workout": [], "cooldown": [],
            "estimated_duration_minutes": 0, "calories_burned_estimate": 0,
            "rest_day_recovery": recovery,
        }

    duration = gym_prefs.get("workout_duration_minutes", 45)
    goal = gym_prefs.get("gym_goal", "general_fitness")
    level = user_profile.get("fitness_level", "beginner") or "beginner"
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"

    rx = _get_goal_prescription(goal, week, level)
    # The COUNT comes off week 1 and holds for the block, while the sets and reps
    # move with the periodisation. Sizing each week against its own prescription
    # made peak weeks (four sets instead of three) drop an exercise, which
    # changed the day's core and cost the very continuity the stable core exists
    # to give. A real programme keeps the lifts and moves the volume.
    target = _target_count(duration, goal, _get_goal_prescription(goal, 1, level))

    pool = []
    for k in _focus_to_keys(focus):
        pool.extend(muscle_split.get(k, []))

    if len(pool) < 3:
        pool = muscle_split.get("full_body", [])
    if len(pool) < 3:
        pool = [ex for group in muscle_split.values() for ex in group]

    selected = _select_for_day(pool, target, user_id, focus, day_num, week)

    # A session is performed in an order, and the order is the programme: the
    # heaviest compound while the practitioner is fresh, its support after it,
    # isolation last, conditioning last of all. Selection optimises for coverage
    # — which movement patterns the day contains — and returned them in whatever
    # order it found them, so a chest day opened with a push-up and then ran
    # three triceps extensions before it reached a fly.
    roles = _assign_roles(selected, _primary_slots(len(selected)))
    ordered = sorted(zip(selected, roles), key=lambda pair: _ROLE_ORDER.index(pair[1]))

    main_workout = []
    total_cals = 0.0
    work_seconds = 0
    rest_seconds_total = 0
    for ex, role in ordered:
        sets, reps, rest = _prescribe(ex, rx, level, role)

        ex_work = _reps_to_seconds(reps, sets)
        work_seconds += ex_work
        rest_seconds_total += sets * rest

        # Calories counted the work and nothing else — a 45-minute muscle-gain
        # session reported 75 kcal, because sets x reps x 4s is nine minutes of
        # it. Rest between sets and the warm-up are still the practitioner being
        # upright and moving, so they are counted at their own lower rates.
        cpm = ex.get("calories_per_minute", 5.0)
        total_cals += (ex_work / 60.0) * cpm
        total_cals += (sets * rest / 60.0) * _REST_KCAL_PER_MINUTE

        main_workout.append({
            "exercise_id": ex.get("id"),
            "exercise_name": ex.get("name"),
            "category": ex.get("category", "strength"),
            "primary_muscles": ex.get("primary_muscles", []),
            "equipment": ex.get("equipment", "bodyweight"),
            "sets": sets,
            "reps": reps,
            "rest_seconds": rest,
            "role": role,
            "role_label": _ROLE_LABEL.get(role, "Accessory"),
            "weight_range": _get_weight_range(ex, strength_level, gender),
            "week_note": rx.get("note", ""),
            "notes": _modification_for(ex),
            "instructions": ex.get("instructions", []),
        })

    return {
        "day": day_num,
        "day_name": day_name,
        # Named for what the day HOLDS. Cardio is filtered out entirely for the
        # muscle-gain and strength goals, so a "Core Cardio" day kept its name and
        # lost its content — every one of the 32 generated for those goals had no
        # cardio in it at all.
        "focus": _focus_label(focus, main_workout),
        "type": "cardio" if "cardio" in focus else "strength",
        "warmup": _warmup_for(focus),
        "main_workout": main_workout,
        "cooldown": _cooldown_for(focus),
        # What was BUILT, not what was asked for. The client shows this as the
        # session-length chip, and it used to echo the preference straight back —
        # so a 60-minute heading sat above 26 minutes of work. Same lesson the
        # yoga engine learned: the number on the card and the session underneath
        # it were different products.
        "estimated_duration_minutes": round((work_seconds + rest_seconds_total
                                             + _OVERHEAD_SECONDS) / 60),
        "requested_duration_minutes": duration,
        "duration_notice": _duration_notice(
            round((work_seconds + rest_seconds_total + _OVERHEAD_SECONDS) / 60), duration, goal),
        "calories_burned_estimate": int(total_cals + (_OVERHEAD_SECONDS / 60.0)
                                        * _WARMUP_KCAL_PER_MINUTE),
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


# ── Vyayama Shakti (classical exercise-capacity principle) ────────────────────

def _vyayama_shakti(dosha: str, age, strength_level: str) -> dict:
    """Classical Vyayama (exercise) dosage principle — Charaka Sutrasthana 7.
    Exercise to Ardhabala (half of maximum capacity); the sign to stop is sweating
    on forehead/nose/joints with onset of mouth-breathing. Over-exercise (Ativyayama)
    depletes Ojas and aggravates Vata."""
    try:
        age_i = int(age or 30)
    except (TypeError, ValueError):
        age_i = 30
    if age_i >= 60 or dosha == "vata" or strength_level == "beginner":
        capacity = ("Keep intensity well within Ardhabala — work to roughly half capacity and stop "
                    "at the first forehead sweat. Vata constitution, beginner strength, and older age "
                    "all lower exercise tolerance; over-exertion here directly depletes Ojas.")
    elif dosha == "kapha" and strength_level in ("intermediate", "advanced") and age_i < 50:
        capacity = ("You have higher Vyayama Shakti — you may work up toward the Ardhabala ceiling with "
                    "good sustained volume. Kapha specifically benefits from exercising until a genuine sweat breaks.")
    else:
        capacity = ("Moderate capacity — work to about half-strength. Pitta types must avoid exercising in "
                    "heat or with a competitive mindset, which pushes past Ardhabala into Pitta aggravation.")
    return {
        "principle": ("Exercise should be performed only to Ardhabala — half of one's maximum capacity "
                      "(Charaka Sutrasthana 7). The classical signal to STOP is sweating on the forehead, "
                      "nose, and joints together with the onset of mouth-breathing."),
        "your_capacity": capacity,
        "signs_adequate": "Sweat on forehead, nose and armpits; lightness in the body; comfortably increased breathing.",
        "signs_overexertion": ("Breathlessness, dizziness, tremor, excessive thirst, joint pain or cough mark "
                               "Ativyayama (over-exercise) — reduce intensity immediately."),
        "bala_note": ("Exercise capacity (Bala) here is estimated from fitness level and age as a practical proxy — "
                      "not a full classical Bala Pareeksha, which also weighs Sara, Samhanana, Satmya, Sattva, and season."),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None, extra_avoid_tags=None):
    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    filtered = filter_exercises(user_profile, gym_prefs, ge, extra_avoid_tags=extra_avoid_tags)
    muscle_split = split_by_muscle_group(filtered)

    workout_days = gym_prefs.get("workout_days_per_week", 4)
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}
    fitness_level = user_profile.get("fitness_level", "beginner") or "beginner"
    strength_level = gym_prefs.get("strength_level", fitness_level)
    gender = user_profile.get("gender", "male") or "male"

    schedule_focus = _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    goal = gym_prefs.get("gym_goal", "general_fitness")

    four_week_plan = []
    for week in range(1, 5):
        week_days = [
            build_day_plan(
                i + 1, days_of_week[i], focus, muscle_split, gym_prefs, user_profile,
                week=week, user_id=user_id, strength_level=strength_level,
                gender=gender, dosha=dominant_dosha,
            )
            for i, focus in enumerate(schedule_focus)
        ]
        # The header used the intermediate prescription whoever was reading it, so
        # two thirds of plans announced a set count no exercise underneath them
        # used — a beginner was told three sets above a page of twos. It is now
        # the practitioner's own, and it names what it describes: the main lift.
        # The supporting roles are published alongside it rather than left for the
        # reader to infer from the exercise rows.
        base_rx = _get_goal_prescription(goal, week, fitness_level)
        four_week_plan.append({
            "week": week,
            "theme": {1: "Foundation", 2: "Volume Build", 3: "Intensity Peak", 4: "Deload & Reset"}[week],
            "prescription": {**_role_prescription(base_rx, "primary"),
                             "note": base_rx.get("note", ""),
                             "applies_to": "main lifts"},
            "role_prescriptions": {
                role: {**_role_prescription(base_rx, role), "label": _ROLE_LABEL[role]}
                for role in ("primary", "secondary", "accessory")
            },
            "days": week_days,
        })

    disclaimer = (
        "PREGNANCY DISCLAIMER: Consult your doctor before starting any exercise program during pregnancy. "
        "Avoid high impact, twisting, and heavy lifting."
        if is_pregnant else
        "This plan is for general wellness guidance only. Consult a physician before beginning any new exercise program."
    )

    # Say when the safe list is too short to be a programme.
    #
    # 56 of the 893 exercises are safe in pregnancy, and after the goal and level
    # gates about 13 reach a beginner — 40 of the 56 are stretches, and there is
    # nothing for the abdomen or the chest, which is correct and also most of a
    # gym. The plan that comes out is safe and extremely repetitive. Presenting a
    # month of neck isometrics and wrist circles as a prenatal programme, in
    # silence, is the failure the yoga engine avoids with `practice_pool_notice`.
    pool_notice = None
    if is_pregnant:
        pool_notice = (
            f"Only {len(filtered)} exercises in the library are safe to prescribe during "
            "pregnancy at your level, so this plan repeats them and leans on stretching and "
            "mobility. It is not a prenatal training programme — for that, work with a "
            "prenatal-qualified instructor."
        )
    elif len(filtered) < _THIN_POOL:
        pool_notice = (
            f"Your equipment, goal and health details narrow the library to {len(filtered)} "
            "exercises, so this plan repeats them more than a fuller one would. Adding "
            "equipment, or widening the goal, opens it up."
        )

    return {
        "plan_id": f"gym_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "bmi_category": user_profile.get("bmi_category", "unknown"),
            "fitness_level": fitness_level,
            "strength_level": strength_level,
            "gym_goal": goal,
            "workout_days": workout_days,
            "duration_per_session": gym_prefs.get("workout_duration_minutes", 45),
        },
        "weekly_schedule": four_week_plan[0]["days"],
        "four_week_plan": four_week_plan,
        "ayurvedic_tips": get_ayurvedic_tips(dominant_dosha),
        "vyayama_shakti": _vyayama_shakti(dominant_dosha, user_profile.get("age"), strength_level),
        "progressive_overload_guide": {
            "week_1": _GOAL_WEEKS[goal][0]["note"] if goal in _GOAL_WEEKS else "",
            "week_2": _GOAL_WEEKS[goal][1]["note"] if goal in _GOAL_WEEKS else "",
            "week_3": _GOAL_WEEKS[goal][2]["note"] if goal in _GOAL_WEEKS else "",
            "week_4": _GOAL_WEEKS[goal][3]["note"] if goal in _GOAL_WEEKS else "",
        },
        "disclaimer": disclaimer,
        "pool_notice": pool_notice,
    }
