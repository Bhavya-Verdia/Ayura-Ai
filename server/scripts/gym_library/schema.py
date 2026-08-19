"""The vocabulary a curated gym library is written in.

Every field here exists because the engine was inferring it from an exercise's
NAME. `_movement_pattern` matched "squat" in a string; `_is_compound` counted
secondary muscles and decided a fly was a compound; `_lift_class` fell back to
the muscle group's main lift, which is how a rotator-cuff drill came to be
prescribed at 17-22.5 kg per hand. A name is not a specification. These are.
"""

import re

# ---------------------------------------------------------------- buckets ---
# The muscle buckets the day builder allocates slots from. `full_body` is not a
# bucket a day draws from — it is where a movement lands when it trains no one
# region, and the splitter treats that as its own pool.
BUCKETS = ("chest", "back", "shoulders", "biceps", "triceps",
           "legs", "core", "cardio", "full_body")

# --------------------------------------------------------------- patterns ---
# What the body is doing, not what the movement is called. The day builder asks
# for a squat pattern and a horizontal pull; it should not have to know that a
# hack squat is a squat and a pendlay row is a row.
PATTERNS = ("squat", "hinge", "lunge", "push_h", "push_v", "pull_h", "pull_v",
            "carry", "rotation", "anti_extension", "anti_rotation",
            "isolation", "locomotion")

# ------------------------------------------------------------------ roles ---
# WHAT SLOT A MOVEMENT MAY OCCUPY. This is the field that did not exist, and its
# absence is why 46% of generated training days prescribed a stretch as a
# working set: everything in the library was eligible for everything.
#
#   main       — can open a session and be progressively loaded
#   accessory  — supports the main lift; never opens a session
#   finisher   — conditioning; prescribed by time or effort, not load
#   warmup     — preparation; never a working set
#   mobility   — a stretch or a joint drill; never a working set, never loaded
ROLES = ("main", "accessory", "finisher", "warmup", "mobility")

WORKING_ROLES = ("main", "accessory")

# ------------------------------------------------------------- rep styles ---
# A carry is not "12-15 reps" and neither is a plank. The engine printed reps
# for both because reps were the only thing it could print.
REP_STYLES = ("reps", "time", "distance", "isometric")

# ---------------------------------------------------------------- impact ---
# Landing force through knee and ankle. Withheld at obese BMI classifications.
# Previously derived from `category == "plyometrics"` plus a name regex, which
# 21 running and bounding drills walked straight through.
IMPACT = ("none", "low", "high")

# ------------------------------------------------------------ skill floor ---
# The training age at which someone can PERFORM the movement, which is not the
# training age at which it should be PROGRAMMED for them. A pull-up has an
# advanced skill floor and is a perfectly ordinary thing to programme for an
# intermediate lifter — as a goal, with a progression under it. Splitting the
# two is what stops `Pullups 3x15-20` reaching a 118 kg beginner.
LEVELS = ("beginner", "intermediate", "advanced")

# ------------------------------------------------------------- load model ---
# Starting load as a fraction of bodyweight, for an intermediate male lifting
# with a barbell. `_LIFT_LEVEL`, sex and implement factors in the engine scale
# from here — this table only has to get the RELATIVE weight of movements right.
#
# The old model had one class per muscle group and everything else fell back to
# it. That is defensible for a main lift and indefensible for anything else: a
# lateral raise is not a shoulder press at a different angle, it is a tenth of
# one. Every isolation and prehab movement now names its own class.
LOAD_CLASSES = {
    # lower body, bilateral
    "back_squat":        1.00,
    "front_squat":       0.80,
    "hack_squat":        1.00,
    "leg_press":         1.80,
    "deadlift":          1.25,
    "romanian_deadlift": 0.90,
    "hip_thrust":        1.10,
    "good_morning":      0.45,
    "calf_raise":        0.90,
    "leg_extension":     0.40,
    "leg_curl":          0.35,
    # lower body, unilateral (load quoted per side as performed)
    "lunge":             0.50,
    "split_squat":       0.45,
    "step_up":           0.40,
    # horizontal push
    "bench_press":       0.75,
    "incline_press":     0.60,
    "decline_press":     0.75,
    "floor_press":       0.65,
    "dip":               0.20,
    # vertical push
    "overhead_press":    0.50,
    "push_press":        0.65,
    # horizontal pull
    "barbell_row":       0.65,
    "seated_row":        0.60,
    "chest_supported_row": 0.50,
    # vertical pull
    "pulldown":          0.60,
    "fly":               0.25,
    "pullover":          0.30,
    "straight_arm_pulldown": 0.25,
    # shoulders / upper back isolation
    "shrug":             0.90,
    "upright_row":       0.35,
    "lateral_raise":     0.09,
    "front_raise":       0.09,
    "rear_delt":         0.08,
    "face_pull":         0.25,
    "external_rotation": 0.05,   # 4-6 kg for an 80 kg lifter, which is the point
    # arms
    "curl":              0.30,
    "hammer_curl":       0.28,
    "preacher_curl":     0.25,
    "triceps_extension": 0.30,
    "triceps_pushdown":  0.35,
    "skullcrusher":      0.28,
    # trunk
    "weighted_crunch":   0.20,
    "pallof":            0.20,
    "side_bend":         0.20,
    "cable_woodchop":    0.25,
    # carries
    "farmers_carry":     0.50,
    "suitcase_carry":    0.35,
}

# Movements loaded by a fixed implement rather than scaled from bodyweight —
# quoting "0.9 x bodyweight" for a kettlebell swing prices it like a shrug.
FIXED_LOAD_CLASSES = {
    "kettlebell_swing":  {"male": (16, 24), "female": (8, 16)},
    "medicine_ball":     {"male": (4, 8),   "female": (3, 6)},
}


# The only contraindication tokens the engine has a path to. A tag outside this
# set is a safety note nobody reads — `knee_injury` and `shoulder_impingement`
# were both written here before the existing KB-integrity test caught that the
# canonical names are `bad_knee` and `rotator_cuff`.
CONTRA_VOCAB = {
    "heart_disease", "hypertension", "osteoporosis", "herniated_disc",
    "lower_back_pain", "cervical_spondylosis", "neck_injury", "shoulder_injury",
    "rotator_cuff", "elbow_injury", "wrist_injury", "bad_knee", "knee_replacement",
    "hip_injury", "bad_ankle", "ankle_injury", "shin_splints", "pregnancy",
}


# Digits with an imperial unit, a spelled-out count of feet (a plural "feet" with
# a number in front is always a measurement — "both feet" is not), and inches or
# pounds in any form. Deliberately does NOT flag a bare "one foot", which in this
# library means the body part.
_IMPERIAL = re.compile(
    r"\b\d+\s*(?:-\s*\d+\s*)?(?:inch|inches|feet|foot|lb|lbs|pound|pounds)\b"
    r"|\b(?:one|two|three|four|five|six|ten|twelve)[- ](?:inch|inches|feet|lb|lbs|pound|pounds)\b",
    re.I)


def validate(entry: dict) -> list:
    """Everything a curated entry must satisfy. Returned as a list of strings so
    the builder can report every fault in one pass rather than one per run."""
    errs = []
    name = entry.get("name", "<unnamed>")

    def bad(msg):
        errs.append(f"{name}: {msg}")

    if entry.get("bucket") not in BUCKETS:
        bad(f"bucket {entry.get('bucket')!r} not in {BUCKETS}")
    if entry.get("movement_pattern") not in PATTERNS:
        bad(f"movement_pattern {entry.get('movement_pattern')!r} unknown")
    if entry.get("role") not in ROLES:
        bad(f"role {entry.get('role')!r} unknown")
    if entry.get("mechanic") not in ("compound", "isolation"):
        bad(f"mechanic {entry.get('mechanic')!r} must be compound or isolation")
    if entry.get("rep_style") not in REP_STYLES:
        bad(f"rep_style {entry.get('rep_style')!r} unknown")
    if entry.get("impact") not in IMPACT:
        bad(f"impact {entry.get('impact')!r} unknown")
    if entry.get("skill_floor") not in LEVELS:
        bad(f"skill_floor {entry.get('skill_floor')!r} unknown")
    if entry.get("level") not in LEVELS:
        bad(f"level {entry.get('level')!r} unknown")

    lc = entry.get("load_class")
    if lc is not None and lc not in LOAD_CLASSES and lc not in FIXED_LOAD_CLASSES:
        bad(f"load_class {lc!r} is not in the load model")

    # A movement that cannot be loaded must not claim a load class, and a
    # barbell movement that can must not omit one — an unpriced main lift is how
    # "Moderate weight" ended up next to a barbell squat.
    if entry.get("equipment") in ("bodyweight",) and lc:
        bad("bodyweight movement carries a load_class")
    if entry.get("role") == "mobility" and lc:
        bad("a stretch cannot carry a load")
    if entry.get("equipment") in ("barbell", "dumbbell", "machine", "cable",
                                  "kettlebell") and entry.get("role") in WORKING_ROLES \
            and not lc and entry.get("rep_style") == "reps":
        bad("loadable working movement has no load_class")

    # The rule the whole rewrite exists to enforce.
    if entry.get("role") in WORKING_ROLES and entry.get("category") in ("stretching",):
        bad("a stretch cannot hold a working slot")
    if entry.get("role") == "main" and entry.get("mechanic") == "isolation":
        bad("an isolation movement cannot be a main lift")

    # A loaded movement progresses by adding weight, and the quoted range says
    # how. An unloaded one progresses by BECOMING A DIFFERENT MOVEMENT, and if
    # the entry does not say which, the practitioner has no route out of it —
    # which is most of what a home user needs the library for.
    if (entry.get("role") in WORKING_ROLES
            and entry.get("equipment") in ("bodyweight", "bands")
            and not any((entry.get("progression") or {}).values())):
        bad("an unloaded working movement with no progression ladder")

    unknown = set(entry.get("contraindications") or []) - CONTRA_VOCAB
    if unknown:
        bad(f"contraindication tokens outside the engine's vocabulary: {sorted(unknown)}")
    instructions = entry.get("instructions") or []
    if not instructions:
        bad("no instructions")
    # Reused upstream prose is written for an American gym. The app quotes every
    # load in kilograms, so an instruction reading "hands about 36 inches apart"
    # is both off-register and, in that particular case, wrong advice reproduced
    # faithfully. Six entries carried one.
    imperial = _IMPERIAL.search(" ".join(instructions))
    if imperial:
        bad(f"imperial units in instructions: {imperial.group(0)!r}")
    # Two lines is a description, not instructions. `Plank`, `Face Pull` and
    # `Jump Rope` all arrived with fewer than three, and the Jump Rope entry
    # spent one of them on how many calories a 150 lb person burns.
    if entry.get("role") != "mobility" and len(instructions) < 3:
        bad(f"only {len(instructions)} instruction step(s)")
    if not entry.get("primary_muscles"):
        bad("no primary_muscles")
    return errs
