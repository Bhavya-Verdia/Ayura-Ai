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


# Below this a session cannot carry a second main lift and the accessories that
# make it worth having; the day is one lift and its support.
_TWO_LIFT_SESSION = 5


def _role_at(index: int, primary_slots: int) -> str:
    """The role of the nth exercise in a session, for costing it before it exists."""
    if index < primary_slots:
        return "primary"
    return "secondary" if index < primary_slots + 1 else "accessory"


# ── Weight / Load Guidance ────────────────────────────────────────────────────
# (lo, hi) in kg. Dumbbell = per-hand weight. Cable/machine = stack weight.
# Female ranges are ~60-65% of male — reflects average population, not a ceiling.

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


# ── Load prescription ─────────────────────────────────────────────────────────
#
# Load used to be looked up by (equipment, coarse muscle group), which is not
# enough information to price a lift. Everything a barbell does to the chest got
# one number and everything it does to the legs got another, so:
#
#     Barbell Bench Press   →  35–55 kg  (beginner)
#     Barbell Curl          →  35–55 kg
#     Barbell Deadlift      →  50–80 kg
#     Barbell Squat         →  50–80 kg
#     Ab Crunch Machine     →  48–78 kg   (`core` is missing from the machine
#     Machine Bicep Curl    →  48–78 kg    table, so both fell back to `chest`)
#
# A beginner told to curl 55 kg does not attempt it — they conclude the app does
# not know what a curl is, and they are right. And a deadlift priced identically
# to a squat is wrong in the direction that gets people hurt.
#
# What a coach actually does is anchor the lift to the practitioner's bodyweight
# and their training age. The multipliers below are the total system load for the
# bilateral barbell or machine version of each movement at INTERMEDIATE level,
# taken from the strength-standards ranges those lifts are ordinarily quoted in.
# Level and sex scale it; the implement converts it.
_LIFT_BW = {
    # lower body
    "squat":         1.25, "front_squat": 1.00, "leg_press": 2.20, "hack_squat": 1.40,
    "deadlift":      1.50, "romanian":    1.20, "hip_thrust": 1.50, "good_morning": 0.70,
    "swing":         0.32,
    "lunge":         0.70, "step_up":     0.55, "calf_raise": 1.00,
    "leg_extension": 0.55, "leg_curl":    0.45, "hip_abduction": 0.50,
    # horizontal push
    "bench":         0.85, "incline_press": 0.70, "chest_press": 0.85, "fly": 0.35,
    # vertical push
    "overhead_press": 0.60, "upright_row": 0.45, "lateral_raise": 0.21,
    "front_raise":   0.20, "rear_delt":   0.20,
    # pull
    "row":           0.80, "pulldown":    0.85, "shrug": 1.20, "face_pull": 0.30,
    "pullover":      0.35,
    # arms and trunk
    "curl":          0.30, "triceps_extension": 0.35, "pushdown": 0.45,
    "core":          0.30,
}

# Movement → lift class, longest-match-first. The class is read off the name for
# the same reason `_MOVEMENT_PATTERNS` is: the dataset records the muscle and the
# machine, and neither of those is the lift.
_LIFT_PATTERNS = (
    ("leg_press",         re.compile(r"\bleg press\b", re.I)),
    ("calf_raise",        re.compile(r"\b(calf|toe raise)", re.I)),
    ("hack_squat",        re.compile(r"\b(hack|sissy)\b", re.I)),
    ("front_squat",       re.compile(r"\bfront (barbell )?squat\b", re.I)),
    ("leg_extension",     re.compile(r"\bleg extension", re.I)),
    ("leg_curl",          re.compile(r"\b(leg curl|lying leg curls|hamstring curl)", re.I)),
    ("hip_abduction",     re.compile(r"\b(abduct|adduct)", re.I)),
    ("step_up",           re.compile(r"\bstep.?up", re.I)),
    ("lunge",             re.compile(r"\b(lunge|split squat|bulgarian)", re.I)),
    ("squat",             re.compile(r"\bsquat|\bwall sit\b", re.I)),
    ("romanian",          re.compile(r"\b(romanian|stiff.?leg|rdl)\b", re.I)),
    ("hip_thrust",        re.compile(r"\b(hip thrust|glute bridge|butt lift)", re.I)),
    ("good_morning",      re.compile(r"\b(good morning|back extension|hyperextension)", re.I)),
    ("swing",             re.compile(r"\b(swing|goblet)", re.I)),
    ("deadlift",          re.compile(r"\b(deadlift|clean|snatch)", re.I)),
    ("incline_press",     re.compile(r"\bincline.*(press|bench)", re.I)),
    ("fly",               re.compile(r"\b(fly|flye|pec deck|butterfly|crossover|iron cross)", re.I)),
    ("pullover",          re.compile(r"\bpullover\b", re.I)),
    ("bench",             re.compile(r"\bbench press\b", re.I)),
    ("chest_press",       re.compile(r"\bchest press\b", re.I)),
    ("lateral_raise",     re.compile(r"\b(lateral raise|side raise|scaption|deltoid raise)", re.I)),
    ("rear_delt",         re.compile(r"\b(rear delt|reverse fly|rear lateral)", re.I)),
    ("front_raise",       re.compile(r"\bfront raise|\bdumbbell raise\b", re.I)),
    ("upright_row",       re.compile(r"\bupright row\b", re.I)),
    ("shrug",             re.compile(r"\bshrug", re.I)),
    ("face_pull",         re.compile(r"\bface pull\b", re.I)),
    ("overhead_press",    re.compile(r"\b(shoulder press|overhead press|military|arnold|"
                                     r"push press|neck press|bradford)", re.I)),
    ("pulldown",          re.compile(r"\b(pulldown|pull.?down|lat pull)", re.I)),
    ("row",               re.compile(r"\brow", re.I)),
    ("pushdown",          re.compile(r"\b(pushdown|push.?down)", re.I)),
    ("triceps_extension", re.compile(r"\b(tricep|skull.?crusher|kickback)", re.I)),
    ("curl",              re.compile(r"\bcurl", re.I)),
    ("core",              re.compile(r"\b(crunch|sit.?up|leg raise|twist|woodchop|"
                                     r"leg pull|knee raise|hip raise|leg tuck)", re.I)),
)

# Training age, as a share of the intermediate standard.
_LIFT_LEVEL = {"untrained": 0.40, "beginner": 0.62, "intermediate": 1.00, "advanced": 1.40}
# Averages, not ceilings. Lower-body strength is closer between the sexes than
# upper-body strength, which one flat factor cannot express.
_LIFT_SEX = {"upper": 0.62, "lower": 0.72}
_LOWER_CLASSES = {"squat", "front_squat", "leg_press", "hack_squat", "deadlift", "romanian",
                  "hip_thrust", "good_morning", "lunge", "step_up", "calf_raise",
                  "leg_extension", "leg_curl", "hip_abduction", "swing"}
# One implement, two hands on it. A swing priced per hand told a beginner to
# swing 29 kg in each of them.
_TWO_HANDED = {"swing"}

# A dumbbell pair carries about 80% of the barbell load for the same movement, so
# each hand takes 40% of it. Cable stacks read low against a free weight through
# the pulley; machines read close to it.
_IMPLEMENT_FACTOR = {"barbell": 1.00, "machine": 1.00, "smith": 1.00,
                     "cable": 0.70, "dumbbell": 0.40, "kettlebell": 0.40}
_PER_HAND = {"dumbbell", "kettlebell"}
# One limb lifts less than two, and the dataset says so in the name.
_UNILATERAL = re.compile(r"\b(one.?arm|single.?arm|one.?leg|single.?leg|one arm|"
                         r"alternating|alternate)\b", re.I)
# Nobody holds a 38 kg dumbbell to squat with; the movement is limited by the grip
# long before the legs run out.
_DUMBBELL_CEILING = 45.0
_DEFAULT_BODYWEIGHT = {"male": 70.0, "female": 60.0}


# When the name does not identify the lift — 94 of the 503 weighted movements,
# the floor presses and windmills and rollouts — the muscle it trains gives a
# conservative class rather than nothing. Legs fall back to the extension rather
# than the squat: under-quoting a starting load costs a set, over-quoting it
# costs a back.
_LIFT_BY_MUSCLE = {
    "chest": "chest_press", "back": "row", "shoulders": "overhead_press",
    "biceps": "curl", "triceps": "triceps_extension", "legs": "leg_extension",
    "core": "core",
}


def _lift_class(ex: dict) -> str | None:
    name = ex.get("name", "")
    for lift, rx in _LIFT_PATTERNS:
        if rx.search(name):
            return lift
    return _LIFT_BY_MUSCLE.get(_muscle_key(ex))


def _round_load(kg: float) -> float:
    """Plates come in fixed sizes. Below 20 kg the useful increment is 1 kg;
    above it, 2.5 — quoting a 63.4 kg bench press implies a precision the
    estimate does not have."""
    step = 1.0 if kg < 20 else 2.5
    return max(step, round(kg / step) * step)


def _fmt_kg(kg: float) -> str:
    return f"{kg:.1f}".rstrip("0").rstrip(".")


def _bodyweight_of(user_profile: dict, gender_key: str) -> float:
    try:
        kg = float(user_profile.get("weight_kg") or 0)
    except (TypeError, ValueError):
        kg = 0.0
    return kg if 30 <= kg <= 250 else _DEFAULT_BODYWEIGHT[gender_key]


def _get_weight_range(ex: dict, strength_level: str, gender: str,
                      bodyweight: float | None = None) -> str:
    """A starting load for THIS lift, at this bodyweight and this training age."""
    eq = (ex.get("equipment") or "bodyweight").lower()
    if (ex.get("category") or "").lower() == "cardio":
        return "Effort-based — see intensity note"

    if eq in ("bodyweight", "other"):
        return _BODYWEIGHT_PROGRESSIONS.get(
            _muscle_key(ex), "Bodyweight · Add band/vest to progress")
    if eq in ("bands", "resistance_bands"):
        return "Light–heavy band · choose resistance that makes last 2 reps challenging"

    implement = next(iter(_EQUIPMENT_ALIASES.get(eq, {eq})))
    factor = _IMPLEMENT_FACTOR.get(implement)
    lift = _lift_class(ex)
    if factor is None or lift is None:
        # An unpriced movement says so rather than guessing. It is the honest
        # answer, and it is what the old table gave 35–55 kg for.
        return "Moderate weight · adjust so the last 2 reps are hard and form holds"

    gender_key = "female" if str(gender).lower() in ("female", "f", "woman") else "male"
    level = strength_level if strength_level in _LIFT_LEVEL else "beginner"

    load = _LIFT_BW[lift] * (bodyweight or _DEFAULT_BODYWEIGHT[gender_key])
    load *= _LIFT_LEVEL[level]
    if gender_key == "female":
        load *= _LIFT_SEX["lower" if lift in _LOWER_CLASSES else "upper"]
    per_hand = implement in _PER_HAND and lift not in _TWO_HANDED
    load *= factor if per_hand else _IMPLEMENT_FACTOR["barbell"]
    if per_hand:
        # A one-arm dumbbell press is the same dumbbell as a two-arm one — the
        # practitioner just does the sides in turn. Halving it here would have
        # priced the single-arm variant of every movement at half the weight it
        # is actually performed with. Unilateral only costs load when the
        # implement is shared between the limbs.
        load = min(load, _DUMBBELL_CEILING)
    elif _UNILATERAL.search(ex.get("name", "")):
        load *= 0.5

    lo, hi = _round_load(load * 0.85), _round_load(load * 1.15)
    # Light isolation rounds to a single plate step and the range collapses —
    # "2–2 kg" reads as a defect rather than a starting point.
    if hi <= lo:
        hi = _round_load(lo + (1.0 if lo < 20 else 2.5))
    unit = " per hand" if per_hand else ""
    return (f"{_fmt_kg(lo)}–{_fmt_kg(hi)} kg{unit} · a starting estimate from your "
            f"bodyweight — adjust so the last 2 reps are hard and form holds")


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
# thing it has to a "loads the spine hard" mechanism. `hypertension` is the same
# kind of proxy for the other direction — the breath-holding strain work and the
# maximal-effort conditioning — and a seventy-year-old was being finished with
# assault-bike sprints and burpees because nobody had said the word out loud.
_AGE_AVOID_TAGS = {"osteoporosis", "hypertension"}


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


# ── Equipment ─────────────────────────────────────────────────────────────────
#
# The preference vocabulary and the dataset's vocabulary were never the same one.
# Preferences offer `dumbbells`, `cables`, `resistance_bands` and `full_gym`; the
# dataset tags exercises `dumbbell`, `cable`, `bands` and `machine`. The filter
# compared them directly, so the only preference that ever matched anything was
# `bodyweight` — which the filter adds unconditionally. A user with `full_gym`
# selected was served a bodyweight plan, and `machine` was not reachable by any
# preference at all.
#
# `_get_weight_range` had a private alias map of its own, which is how the load
# guidance managed to price dumbbells the filter would never have selected.
_EQUIPMENT_ALIASES = {
    "bodyweight":       {"bodyweight"},
    "dumbbells":        {"dumbbell"},
    "dumbbell":         {"dumbbell"},
    "barbell":          {"barbell"},
    "machines":         {"machine"},
    "machine":          {"machine"},
    "cables":           {"cable"},
    "cable":            {"cable"},
    "kettlebell":       {"kettlebell"},
    "kettlebells":      {"kettlebell"},
    "resistance_bands": {"bands"},
    "bands":            {"bands"},
    "jump_rope":        {"jump_rope"},
    "pool":             {"pool"},
    # The cardio machines are one purchase decision as far as the practitioner is
    # concerned: either the gym has a cardio floor or it does not.
    "cardio_machines":  {"treadmill", "stationary_bike", "rowing_machine", "elliptical",
                         "stair_climber", "air_bike", "battle_ropes", "box"},
}
_FULL_GYM = ("dumbbells", "barbell", "machines", "cables", "kettlebell",
             "resistance_bands", "jump_rope", "cardio_machines")


def _normalise_equipment(available) -> set:
    """The dataset's equipment tokens for what the practitioner says they have."""
    requested = {str(eq).lower().strip() for eq in (available or ["bodyweight"])}
    if "full_gym" in requested:
        requested |= set(_FULL_GYM)
    tokens = {"bodyweight"}
    for eq in requested:
        tokens |= _EQUIPMENT_ALIASES.get(eq, {eq})
    return tokens


# ── Exercise filtering ────────────────────────────────────────────────────────

# Self-myofascial release — foam rolling. Named as a suffix throughout the
# dataset ("Adductors-Smr", "Peroneals-Smr"); the `-` matters, since `_MOVEMENT_
# PATTERNS` has to keep reading "Smith" and "Smr" apart.
_SMR_NAME = re.compile(r"-\s*smr\b", re.I)


def filter_exercises(user_profile, gym_prefs, exercises, extra_avoid_tags=None):
    available_eq = _normalise_equipment(gym_prefs.get("available_equipment"))

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


def _muscle_key_from_muscles(ex) -> str:
    """The one bucket an exercise's PRIMARY MUSCLE puts it in.

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


def _muscle_key(ex) -> str:  # noqa: F811 — see the wrapper below
    """As `_muscle_key_from_muscles`, but the movement gets the final word.

    The dataset files the conventional deadlift under "lower back", so it landed
    in the back bucket — and `legs` days draw only from the legs bucket, which
    meant a leg day could not contain a deadlift at all while a back day opened
    with one. A hip hinge is posterior-chain work; that is what a leg day is for
    and it is why the pattern classifier knows the hinge in the first place.
    """
    key = _muscle_key_from_muscles(ex)
    if key == "back" and _movement_pattern(ex) == "hinge":
        return "legs"
    return key


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
    # Flyes, crossovers and the pec deck used to live here, which let a chest
    # day's horizontal-push slot be filled by an isolation movement — and once
    # main lifts were chosen for loadability, a barbell "Bodyweight Flyes"
    # outranked the bench press for it. A press is a press; a fly is accessory
    # work and belongs in the tier that finishes the session.
    ("push_h", re.compile(r"\b(bench press|chest press|floor press|push.?up|dip)(?:e?s)?\b", re.I)),
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


# Specialty variants. Every one of these is a real movement that a real coach
# uses — for a specific athlete, at a specific point in a block, for a reason
# they can name. None of them is what a four-week plan opens a leg day with.
#
# Selection was a uniform shuffle over everything eligible, so a specialty
# variant won a main-lift slot exactly as often as the lift it is a variant of. A
# strength programme came out opening with "Bench Press With Chains" and
# "Dumbbell Squat To A Bench" — two movements whose whole purpose is to change
# something about a barbell bench press and a barbell squat that this
# practitioner has not done yet.
_SPECIALTY_NAME = re.compile(
    r"\b(chain|chains|board|box squat|pin press|guillotine|tate|jm|smith|leverage|"
    r"iso.?lateral|neck|judo|gorilla|clock|"
    r"isometric|vacuum|windmill|jerk|bradford|rocky|cuban|zercher|jefferson|sissy|"
    r"car driver|anti.?gravity|scaption|around the world|kaz|bent press|"
    r"speed band|band skull|hindu|frog|monkey|spider|drag)\b", re.I)


# A main lift has to be loadable, because progressive overload is the point of
# having one. Name plainness alone preferred "Bench Dips" over the barbell bench
# press and "Bodyweight Squat" over the barbell squat — shorter names, and no way
# to add 2.5 kg to either of them in week two.
_LOADABLE_RANK = {"barbell": 3, "machine": 2, "cable": 2, "dumbbell": 2,
                  "kettlebell": 1, "bodyweight": 1, "other": 0, "bands": 0}


# The movement each pattern is really asking for. Name plainness is too crude a
# proxy on its own: the dataset calls the canonical lift "Barbell Bench Press -
# Medium Grip" and a specialty variant "Floor Press", so brevity handed a chest
# day's press slot to the floor press — a triceps movement, two words long.
_PATTERN_HEADLINE_LIFT = {
    "push_h": {"bench", "chest_press"},
    "push_v": {"overhead_press"},
    "squat":  {"squat", "front_squat"},
    "hinge":  {"deadlift", "romanian"},
    "pull_v": {"pulldown"},
    "pull_h": {"row"},
    "lunge":  {"lunge"},
}
_WORD = re.compile(r"[A-Za-z]{2,}")
# Words that change WHICH movement this is rather than describing how it is set
# up. Brevity alone preferred "Barbell Guillotine Bench Press" (four words) and
# "One Arm Lat Pulldown" over "Barbell Bench Press - Medium Grip" (five) — the
# grip qualifier on the canonical lift cost it the slot to two variants of it.
_MODIFIER_NAME = re.compile(
    r"\b(incline|decline|guillotine|cambered|reverse|wide|close|narrow|behind|"
    r"pin|deficit|sumo|rear|one.?arm|single.?arm|one.?leg|single.?leg|"
    r"alternating|alternate|partial|half|paused|tempo)\b", re.I)


def _canonical_score(ex) -> tuple:
    """How well a movement serves as the lift a block is built around.

    A coach writing a programme reaches for the lift they can load and can name
    without qualification. "Barbell Squat" is two words; "Dumbbell Squat To A
    Bench" is five, and the extra three all describe what makes it not a squat.
    """
    name = ex.get("name", "")
    return (
        _LOADABLE_RANK.get((ex.get("equipment") or "bodyweight").lower(), 1),
        -20 * len(_SPECIALTY_NAME.findall(name))
        - 5 * len(_MODIFIER_NAME.findall(name))
        - len(_WORD.findall(name)),
    )


def _pattern_preference(ex, pattern: str, muscle_rank: dict) -> tuple:
    """Sort key for filling a day's movement-pattern slot, best first.

    In order: a compound before an isolation movement; the muscle the day is
    named for before the one it is paired with; the movement the pattern is
    actually asking for before a cousin of it; then loadable and plainly named.
    """
    return (
        not _is_compound(ex),
        muscle_rank.get(_muscle_key(ex), len(muscle_rank)),
        _lift_class(ex) not in _PATTERN_HEADLINE_LIFT.get(pattern, set()),
    ) + tuple(-v for v in _canonical_score(ex))


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
            caps=None, per_muscle=None, muscle_rank=None):
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
    muscle_rank = muscle_rank or {}

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
        candidates.sort(key=lambda ex: _pattern_preference(ex, pattern, muscle_rank))
        if candidates:
            _take(candidates[0])

    for want_compound in (True, False):
        if want_compound and min_compounds <= 0:
            continue
        have_compounds = sum(1 for ex in picked if _is_compound(ex))
        # The compounds are chosen plainest-first; the accessories keep the
        # shuffle, because variety belongs in the work that finishes a session
        # rather than in the lift the block is built around.
        for ex in (sorted(ordered, key=_canonical_score, reverse=True)
                   if want_compound else ordered):
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
    muscle_rank = {key: i for i, (key, _) in enumerate(_FOCUS_ALLOCATION.get(focus, ()))}

    core = _choose(pool, core_n, f"{user_id}-{focus}-d{day_num}-core",
                   taken, families, min_compounds=min(_MIN_COMPOUNDS, max(1, core_n - 1)),
                   patterns=_FOCUS_PATTERNS.get(focus, ()),
                   caps=caps, per_muscle=per_muscle, muscle_rank=muscle_rank)
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


_TIMED_REPS = re.compile(r"(\d+)\s*(min|sec)", re.I)


def _reps_to_seconds(reps, sets: int) -> int:
    """Time under tension for one exercise, across all its sets.

    Prescriptions written in minutes were read as repetitions, so "30 min" on a
    treadmill cost the session 30 reps — two minutes of estimated work for half
    an hour of running, and a calorie figure to match.
    """
    text = str(reps).replace("\u2013", "-")
    timed = _TIMED_REPS.findall(text)
    if timed:
        per_set = sum(int(n) * (60 if unit.lower().startswith("min") else 1)
                      for n, unit in timed)
        return int(sets * per_set)
    digits = [int(p) for p in text.split("-") if p.strip().isdigit()]
    avg_reps = sum(digits) / len(digits) if digits else 10
    return int(sets * (avg_reps * _SECONDS_PER_REP))


def _target_count(duration, goal, rx=None):
    """How many exercises fit. See `_session_shape`, which also says how many of
    them are main lifts."""
    return _session_shape(duration, goal, rx)[0]


def _session_shape(duration, goal, rx=None):
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
        return (3 if duration <= 20 else (4 if duration <= 30 else 5)), 1

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
    # is depends on how many main lifts it gets. Cost the session with a single
    # main lift; if it came out long enough to carry two, cost it again — and keep
    # the second version only if it is STILL long enough, because a second main
    # lift is expensive. A 45-minute strength day priced with one main lift fits
    # five exercises and priced with two fits three, and taking the second answer
    # gave the shorter session the smaller programme.
    count = _fits(1)
    if count >= _TWO_LIFT_SESSION:
        two = _fits(2)
        if two >= _TWO_LIFT_SESSION:
            return two, 2
    return count, 1


# ── Conditioning finisher ─────────────────────────────────────────────────────
#
# Conditioning only ever reached a plan through a `core_cardio` day, and only
# three of the six weekly splits have one. Measured across levels and schedules,
# 60% of fat-loss plans contained no conditioning at all: four days of resistance
# training, prescribed for fat loss, with nothing that raises a heart rate for
# longer than a rest interval.
#
# Fat loss and endurance are the two goals where conditioning IS the training
# effect rather than a supplement to it, so for those it is scheduled rather than
# left to whether the split happens to include a cardio day. It goes last, after
# the lifting, which is the order it should be performed in and the order the
# role sort already produces.
_FINISHER_GOALS = {"fat_loss", "endurance"}
# A finisher is not a cardio session. The library's steady-state entries are
# written as the whole workout — "30 min" on a treadmill — so they are clamped;
# the interval entries are already finisher-shaped and keep their own writing.
_FINISHER_MINUTES = {"beginner": 8, "intermediate": 10, "advanced": 12}


def _finisher_prescription(ex: dict, level: str) -> tuple:
    own = (ex.get("sets_reps") or {}).get(level) or (ex.get("sets_reps") or {}).get("intermediate") or {}
    sets = int(own.get("sets", 1) or 1)
    reps = own.get("reps", "10 min")
    rest = int(own.get("rest_seconds", 0) or 0)
    cap = _FINISHER_MINUTES.get(level, 10)
    if sets == 1 and _TIMED_REPS.search(str(reps)):
        return 1, f"{cap} min", 0
    return sets, reps, rest


def _pick_finisher(cardio_pool, user_id, focus, day_num, week):
    if not cardio_pool:
        return None
    picked = _deterministic_select(cardio_pool, 1, f"{user_id}-{focus}-d{day_num}-finisher-w{week}")
    return picked[0] if picked else None


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
                   dosha="vata", bodyweight=None):
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
    target, primary_slots = _session_shape(
        duration, goal, _get_goal_prescription(goal, 1, level))

    # The finisher takes a slot rather than being added on top of a session that
    # already fills the clock — the practitioner asked for forty-five minutes.
    finisher = None
    if goal in _FINISHER_GOALS and "cardio" not in focus:
        finisher = _pick_finisher(muscle_split.get("cardio") or [],
                                  user_id, focus, day_num, week)
        if finisher:
            target = max(_MIN_EXERCISES, target - 1)

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
    # The same number of main lifts the session was costed with. Deciding it again
    # from the length that came out let the day be built to a shape it was not
    # priced for.
    roles = _assign_roles(selected, primary_slots)
    ordered = sorted(zip(selected, roles), key=lambda pair: _ROLE_ORDER.index(pair[1]))
    if finisher and all(ex["id"] != finisher["id"] for ex in selected):
        ordered.append((finisher, "conditioning"))

    main_workout = []
    total_cals = 0.0
    work_seconds = 0
    rest_seconds_total = 0
    for ex, role in ordered:
        sets, reps, rest = (_finisher_prescription(ex, level) if ex is finisher
                            else _prescribe(ex, rx, level, role))

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
            "weight_range": _get_weight_range(ex, strength_level, gender, bodyweight),
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
    available_eq = _normalise_equipment(gym_prefs.get("available_equipment"))
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}
    fitness_level = user_profile.get("fitness_level", "beginner") or "beginner"
    strength_level = gym_prefs.get("strength_level", fitness_level)
    gender = user_profile.get("gender", "male") or "male"
    bodyweight = _bodyweight_of(
        user_profile, "female" if str(gender).lower() in ("female", "f", "woman") else "male")

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
                gender=gender, dosha=dominant_dosha, bodyweight=bodyweight,
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
