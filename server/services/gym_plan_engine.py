import collections
import json
import hashlib
import random
import re

from services.gym_condition_guidance import _unfalse, guidance_for
from engine.movement_risk import (_INJURY_RISK_TAGS, _LIMITATION_ALIASES, RISK_VOCAB,
                                  condition_risk_tags, injury_risk_tags)
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_PATH = BASE_DIR / "data" / "knowledge_base" / "gym_exercises.json"

gym_exercises = []
if EXERCISES_PATH.exists():
    with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
        gym_exercises = json.load(f)


# ── Warmup / Cooldown libraries ───────────────────────────────────────────────

# Warm-up and cool-down movements, each carrying the same two safety properties
# the library records: whether it lands, and what it is unsuitable for.
#
# These were plain strings, and plain strings pass no gate. A 70-year-old with
# hypertension, a 118 kg practitioner with a knee replacement and a pregnant
# practitioner were each given a main workout with every impact movement
# carefully filtered out of it — and then all three opened the session with
# "Jumping jacks — 30 sec" and "High knees — 30 sec", because the warm-up was
# written per focus and never consulted anybody's profile. It defeated the whole
# impact-gating story from the first line of the session.
#
# `_gate_movements` runs the same checks the exercise pool runs. A line that is
# withheld is replaced from `_WARMUP_SUBSTITUTES` so the warm-up keeps its length
# rather than quietly getting shorter.
def _w(text, impact="none", contra=(), pregnancy_safe=True, risk=()):
    return {"text": text, "impact": impact, "contra": frozenset(contra),
            "pregnancy_safe": pregnancy_safe, "risk": frozenset(risk)}


# Mechanisms the session's edges carry, in `engine.movement_risk`'s vocabulary.
# A 72-year-old with osteoporosis and hypertension had every flexion exercise
# removed from her main workout and still opened each session with an inchworm —
# a forward fold to the floor, head down, weight on the wrists — and closed it
# with a supine twist and child's pose.
_FOLD = ("spinal_flexion",)
_INCHWORM = ("spinal_flexion", "intracranial_pressure", "wrist_weight_bearing")


_WARMUP = {
    "upper": [
        _w("Arm circles — 10 forward, 10 backward"),
        _w("Cross-body shoulder stretch — 30 sec each side", contra=["shoulder_injury"]),
        _w("Shoulder roll — 10 slow rotations"),
        _w("Band pull-apart or doorway chest stretch — 15 reps"),
        _w("Cat-cow — 8 reps"),
        _w("Wrist circles — 10 each direction"),
    ],
    "lower": [
        _w("Hip circles — 10 each direction"),
        _w("Leg swings — 10 forward/back each leg", contra=["hip_injury"]),
        _w("Bodyweight squat — 10 slow reps", contra=["bad_knee", "knee_replacement"]),
        _w("Ankle circles — 10 each direction"),
        _w("Glute bridge — 12 reps", pregnancy_safe=False),
        _w("Walking lunge — 8 each leg", contra=["bad_knee", "knee_replacement"],
           risk=["fall_risk"]),
    ],
    "core": [
        _w("Cat-cow — 10 reps"),
        _w("Dead bug — 8 each side", pregnancy_safe=False),
        _w("Hip flexor stretch — 30 sec each side"),
        _w("Bird dog — 8 each side"),
        _w("High knees — 30 sec", impact="high",
           contra=["hypertension", "heart_disease", "bad_knee"], pregnancy_safe=False),
    ],
    "full": [
        _w("Jumping jacks — 30 sec", impact="high",
           contra=["bad_knee", "knee_replacement", "bad_ankle"], pregnancy_safe=False),
        _w("Arm circles — 10 each direction"),
        _w("Hip circles — 10 each direction"),
        _w("Bodyweight squat — 10 reps", contra=["bad_knee", "knee_replacement"]),
        _w("High knees — 30 sec", impact="high",
           contra=["hypertension", "heart_disease", "bad_knee"], pregnancy_safe=False),
        _w("Inchworm — 5 reps", contra=["lower_back_pain", "wrist_injury"], risk=_INCHWORM),
    ],
    "cardio": [
        _w("Brisk walk or light jog — 3 min"),
        _w("Leg swings — 10 each leg", contra=["hip_injury"]),
        _w("Ankle circles — 10 each direction"),
        _w("Hip circles — 10 each direction"),
        _w("Dynamic quad stretch — 8 each leg", contra=["bad_knee"]),
    ],
}

# Drawn on when a line is withheld, so the warm-up keeps its length. Every one is
# unloaded, non-impact and carries no restriction — they are what is left when
# everything else has been ruled out.
_WARMUP_SUBSTITUTES = [
    _w("Marching on the spot — 60 sec"),
    _w("Shoulder roll — 10 slow rotations"),
    _w("Ankle circles — 10 each direction"),
    _w("Cat-cow — 8 reps"),
    _w("Standing hip hinge, hands on thighs — 10 slow reps"),
    _w("Deep breathing with tall posture — 5 breaths"),
]

# Cool-downs are stretches, so impact is not the risk — position is. Supine and
# prone holds are the ones a pregnant practitioner should not be handed, and the
# same gate that filters the warm-up filters these.
_COOLDOWN = {
    "upper": [
        _w("Doorway chest stretch — 30 sec", contra=["shoulder_injury"]),
        _w("Cross-body shoulder stretch — 30 sec each side", contra=["shoulder_injury"]),
        _w("Overhead tricep stretch — 30 sec each arm", contra=["shoulder_injury"]),
        _w("Lat stretch in doorway — 30 sec each side", contra=["shoulder_injury"]),
        _w("Child's pose — 60 sec", contra=["bad_knee"], risk=_FOLD),
        _w("Deep belly breathing — 5 breaths"),
    ],
    "lower": [
        _w("Standing quad stretch — 30 sec each leg", contra=["bad_knee"]),
        _w("Seated hamstring stretch — 30 sec each leg"),
        _w("Pigeon pose or figure-four stretch — 45 sec each side",
           contra=["hip_injury", "bad_knee"]),
        _w("Calf stretch against wall — 30 sec each leg"),
        _w("Supine spinal twist — 30 sec each side",
           contra=["herniated_disc"], pregnancy_safe=False, risk=_FOLD),
        _w("Child's pose — 60 sec", contra=["bad_knee"], risk=_FOLD),
    ],
    "core": [
        _w("Supine spinal twist — 30 sec each side",
           contra=["herniated_disc"], pregnancy_safe=False, risk=_FOLD),
        _w("Child's pose — 60 sec", contra=["bad_knee"], risk=_FOLD),
        _w("Hip flexor stretch (lunge) — 30 sec each side", contra=["bad_knee"]),
        _w("Cobra stretch — 30 sec",
           contra=["herniated_disc", "lower_back_pain"], pregnancy_safe=False,
           risk=["spinal_extension"]),
        _w("Deep belly breathing — 5 breaths"),
    ],
    "full": [
        _w("Child's pose — 60 sec", contra=["bad_knee"], risk=_FOLD),
        _w("Supine spinal twist — 30 sec each side",
           contra=["herniated_disc"], pregnancy_safe=False, risk=_FOLD),
        _w("Quad stretch — 30 sec each leg", contra=["bad_knee"]),
        _w("Shoulder cross-body stretch — 30 sec each arm", contra=["shoulder_injury"]),
        _w("Deep belly breathing — 5 breaths"),
    ],
    "cardio": [
        _w("Walk at easy pace — 3 min"),
        _w("Standing quad stretch — 30 sec each leg", contra=["bad_knee"]),
        _w("Standing calf stretch — 30 sec each leg"),
        _w("Seated hamstring stretch — 30 sec each leg"),
        _w("Deep belly breathing — 5 breaths"),
    ],
}

_COOLDOWN_SUBSTITUTES = [
    _w("Seated forward fold, knees soft — 30 sec", risk=_FOLD),
    _w("Seated side bend — 30 sec each side", risk=_FOLD),
    _w("Standing chest opener, hands clasped behind — 30 sec"),
    _w("Seated knee hug, one leg at a time — 20 sec each side"),
    _w("Neck tilt, ear to shoulder — 20 sec each side"),
    _w("Standing calf stretch — 30 sec each leg"),
    _w("Deep belly breathing — 5 breaths"),
]

# Balance, for everyone past sixty. WHO's 2020 guidelines ask older adults for
# "varied multicomponent physical activity that emphasises functional balance and
# strength training" on three or more days a week, because falls are the injury
# that ends independence. The engine had strength and nothing else: a 78-year-old
# got squats and rows and not a minute of standing on one leg. These are the
# Otago Exercise Programme's balance progressions, which cut falls by about a
# third in trials, each done beside a counter or a chair back.
#
# Four lines a session, rotated by day so the week covers all of them. They pass
# the same gate as the warm-up.
_BALANCE_SECONDS = 4 * 60
_BALANCE = [
    _w("Supported single-leg stand — hold a counter, 3 × 20 sec each leg; "
       "progress to fingertip support"),
    _w("Sit-to-stand from a chair, arms crossed — 2 × 8, slow on the way down",
       contra=["knee_replacement"]),
    _w("Heel-to-toe walk beside a wall — 3 lengths of 10 steps", risk=["fall_risk"]),
    _w("Heel raises holding a chair back — 2 × 12", contra=["bad_ankle"]),
    _w("Side-stepping along a counter — 2 × 10 steps each way"),
    _w("Toe raises holding a chair back — 2 × 12", contra=["bad_ankle"]),
    _w("Clock reach — stand on one leg holding support, touch the other foot to 12, 3 "
       "and 6 o'clock — 5 each side", risk=["fall_risk"]),
    _w("Supported backwards walk along a counter — 3 lengths of 10 steps",
       risk=["fall_risk"]),
]
# What remains when the fall-risk progressions are withheld: seated and
# fully-supported work, which is where Otago starts anyone who needs it.
_BALANCE_SUBSTITUTES = [
    _w("Seated marching — 2 × 20, tall posture"),
    _w("Seated heel and toe raises — 2 × 15"),
    _w("Supported weight shifts, side to side, both hands on a counter — 2 × 10"),
    _w("Supported weight shifts, front to back, both hands on a counter — 2 × 10"),
]


def _balance_for(day_num: int, avoid_tags=frozenset(), withhold_impact=False,
                 is_pregnant=False, risks=frozenset()) -> list:
    start = ((day_num - 1) * 3) % len(_BALANCE)
    items = [_BALANCE[(start + i) % len(_BALANCE)] for i in range(4)]
    return _gate_movements(items, _BALANCE_SUBSTITUTES, frozenset(avoid_tags),
                           withhold_impact, is_pregnant, frozenset(risks))


_FOCUS_WARMUP_TYPE = {
    "full_body": "full", "push": "upper", "pull": "upper",
    "chest_triceps": "upper", "back_biceps": "upper",
    "chest": "upper", "back": "upper", "shoulders": "upper",
    "shoulders_core": "upper", "arms": "upper",
    "legs": "lower", "legs_core": "lower",
    "shoulders_arms": "upper", "core_cardio": "cardio",
    "upper": "upper", "lower": "lower",
}


def _gate_movements(items, subs, avoid_tags, withhold_impact, is_pregnant,
                    risks=frozenset()):
    """The same checks the exercise pool runs, applied to the session's edges.

    Withheld lines are replaced from `subs` rather than dropped, so a restricted
    practitioner gets a warm-up of the same length as everyone else instead of a
    visibly shorter one. A substitute passes the same gate: the cool-down's
    fallback was a seated forward fold, which is the movement the osteoporosis
    restriction that triggered the substitution exists to prevent.
    """
    def blocked(item):
        return bool(avoid_tags & item["contra"]
                    or risks & item["risk"]
                    or (withhold_impact and item["impact"] == "high")
                    or (is_pregnant and not item["pregnancy_safe"]))

    kept, used = [], set()
    for item in items:
        if not blocked(item):
            kept.append(item["text"])
            used.add(item["text"])
    if len(kept) < len(items):
        for sub in subs:
            if len(kept) >= len(items):
                break
            if sub["text"] in used or blocked(sub):
                continue
            kept.append(sub["text"])
            used.add(sub["text"])
    return kept


def _warmup_for(focus: str, avoid_tags=frozenset(), withhold_impact=False,
                is_pregnant=False, risks=frozenset()) -> list:
    items = _WARMUP.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _WARMUP["full"])
    return _gate_movements(items, _WARMUP_SUBSTITUTES, frozenset(avoid_tags),
                           withhold_impact, is_pregnant, frozenset(risks))


def _cooldown_for(focus: str, avoid_tags=frozenset(), withhold_impact=False,
                  is_pregnant=False, risks=frozenset()) -> list:
    items = _COOLDOWN.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _COOLDOWN["full"])
    return _gate_movements(items, _COOLDOWN_SUBSTITUTES, frozenset(avoid_tags),
                           withhold_impact, is_pregnant, frozenset(risks))


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
    # Fat loss was written as sets of 15-20 — the "light weights for toning"
    # scheme. Under an energy deficit the job of the lifting is to keep the
    # muscle the diet would otherwise take, and that needs a load heavy enough to
    # ask for it (ACSM position stand on weight loss, Donnelly 2009; Helms 2014 on
    # resistance training in a deficit). The metabolic demand comes from the
    # short rest and the conditioning, not from making the sets light.
    "fat_loss": [
        {"sets": 3, "reps": "12-15", "rest_seconds": 45, "note": "Keep rest short to keep your heart rate up, with a weight that makes the last 2 reps hard."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 35, "note": "Cut rest by 10 sec vs Week 1 to increase metabolic demand."},
        {"sets": 4, "reps": "12-15", "rest_seconds": 30, "note": "Peak metabolic week — minimum rest, circuit style if possible."},
        {"sets": 3, "reps": "10-12", "rest_seconds": 45, "note": "Deload — slightly fewer reps, full rest, let connective tissue recover."},
    ],
    "endurance": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 30, "note": "Light weight, high reps. Focus on breathing rhythm throughout."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 25, "note": "Add 1 set vs Week 1. Cut rest to challenge aerobic capacity."},
        {"sets": 4, "reps": "20-25", "rest_seconds": 20, "note": "Peak endurance week — go to near-failure on each set."},
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


# Which of the tables above a block is written in.
#
# `training_style` is a required field in the gym form — Strength, Hypertrophy,
# Endurance, Circuit Training — and nothing read it. It is not a duplicate of the
# goal: the goal is what you are training FOR, and it drives which exercises are
# eligible (`goal_suitability`), how the week is split, and whether the day ends
# with conditioning. The style is how the sets are WRITTEN, and that is exactly
# what `_GOAL_WEEKS` is — a set, rep and rest scheme with a four-week
# periodisation on it. The four styles map onto four of the five tables, so the
# field costs nothing to honour and lets someone cut weight on heavy triples if
# that is how they want to do it.
_STYLE_SCHEME = {
    "strength":    "strength",
    "hypertrophy": "muscle_gain",
    "endurance":   "endurance",
    "circuit":     "fat_loss",   # short rest, high reps — the table's own notes say "circuit style"
}
# What each goal implies when the practitioner has expressed no preference. The
# form preselects the same pairing, so the two agree on screen and in the plan.
_GOAL_SCHEME = {
    "strength": "strength", "muscle_gain": "muscle_gain", "fat_loss": "fat_loss",
    "endurance": "endurance", "general_fitness": "general_fitness",
}


# Sets of 3-5 at near-maximal load are lifted holding the breath against a
# closed glottis — the Valsalva manoeuvre — whether or not the lifter means to.
# It sends blood pressure to 300/200 in a trained lifter and raises intraocular
# and intra-abdominal pressure with it. A hypertensive 50-year-old was written a
# 4 x 3-5 barbell bench press; a glaucoma patient the same triples. The exercise
# gates had removed the deadlift for hypertension and left the scheme that makes
# every lift in the block a maximal one.
#
# ACSM's guidance for these populations, and for older adults generally, is
# moderate loads for 8-12 repetitions. The strength scheme is replaced with the
# hypertrophy one, which is exactly that, and the plan says why.
_INTENSITY_CEILING = (
    ("blood pressure and your heart",
     ("hypertension", "high_blood_pressure", "heart", "cardiac", "atrial_fibrillation",
      "arrhythmia", "angina", "stroke", "aneurysm")),
    ("the pressure inside your eyes",
     ("glaucoma", "retinopathy", "retinal")),
    ("the abdominal wall",
     ("hernia", "abdominal_surgery", "recent_surgery")),
)
_CEILING_SCHEMES = {"strength": "muscle_gain"}


def _intensity_ceiling(user_profile) -> str | None:
    """What near-maximal sets would put at risk for this practitioner, if anything."""
    if not user_profile:
        return None
    declared = " ".join(_unfalse(c) for c in _conditions_and_injuries(user_profile))
    for reason, terms in _INTENSITY_CEILING:
        if any(t in declared for t in terms):
            return reason
    if user_profile.get("pregnancy_or_nursing"):
        return "your pregnancy"
    group = _age_group(user_profile.get("age"))
    if group == "senior":
        return "joints and blood vessels past sixty"
    if group == "youth":
        return "a body that is still growing"
    return None


# Under 18. An 11-year-old who had never lifted was written six days a week of
# 3-5 rep strength sets on a body-part split — the programme of an adult
# competitor. Youth resistance training is safe and worthwhile (NSCA 2009, AAP
# 2020, UKSCA 2014), and the same statements agree on its shape: two or three
# non-consecutive days a week, moderate loads for 8-15 reps, technique before
# load, and qualified supervision. Older teenagers with a training history can
# carry a fourth day.
_YOUTH_MAX_DAYS = 3
_YOUTH_MAX_DAYS_TRAINED = 4
_YOUTH_TRAINED_FROM = 16


def _youth_day_cap(age, fitness_level) -> int:
    try:
        age = int(age)
    except (TypeError, ValueError):
        return _YOUTH_MAX_DAYS
    if age >= _YOUTH_TRAINED_FROM and fitness_level in ("intermediate", "advanced"):
        return _YOUTH_MAX_DAYS_TRAINED
    return _YOUTH_MAX_DAYS


def _youth_notice(requested: int, built: int) -> str:
    days = (f"{built} days a week" if built >= requested
            else f"{built} days a week rather than the {requested} you asked for")
    return (f"Because you are under 18, this plan trains {days}, with a rest day "
            "between sessions, uses 8–15 reps at a weight you can move with perfect form, "
            "and leaves out maximal lifts. That is the guidance for young people who are "
            "still growing, and resistance training done this way is safe and good for "
            "you. Learn each lift from a qualified coach or PE teacher and train with an "
            "adult supervising.")


def _resolve_scheme(goal: str, training_style=None, user_profile=None) -> str:
    """The `_GOAL_WEEKS` key this block is written in."""
    scheme = _STYLE_SCHEME.get(str(training_style or "").lower())
    scheme = scheme or _GOAL_SCHEME.get(goal, "general_fitness")
    if scheme in _CEILING_SCHEMES and _intensity_ceiling(user_profile):
        return _CEILING_SCHEMES[scheme]
    return scheme


def _intensity_notice(goal, training_style, user_profile) -> str | None:
    requested = (_STYLE_SCHEME.get(str(training_style or "").lower())
                 or _GOAL_SCHEME.get(goal, "general_fitness"))
    reason = _intensity_ceiling(user_profile)
    if requested not in _CEILING_SCHEMES or not reason:
        return None
    return (f"Your sets are written as 8–12 reps at a moderate weight rather than 3–5 at "
            f"a near-maximal one, because of {reason}. Lifting that heavy makes you hold "
            "your breath and strain, which spikes pressure in the chest, head and belly. "
            "You still get stronger — breathe out on every effort and never hold your "
            "breath.")


def _get_goal_prescription(goal: str, week: int, level: str = "intermediate",
                           activity: str = None) -> dict:
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
    delta = _LEVEL_SET_DELTA.get(level, 0) + _ACTIVITY_SET_DELTA.get(
        str(activity or "").lower(), 0)
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


# The rep ranges a coach writes, for each tier under a given main-lift range.
# Shifting the main lift's range by a fixed number of reps produced ranges
# nobody writes — 11-13, 13-15, 17-22, 5-7 — on 4,587 exercise rows of a
# 400-plan sweep, which reads as generated before a single movement is looked
# at. The tiers are the same idea (support work lighter and longer than the
# main lift, isolation lighter again) expressed in the ranges that exist.
_TIER_REPS = {
    "3-5":   ("6-8", "8-12"),
    "4-5":   ("6-8", "8-12"),
    "4-6":   ("6-8", "8-12"),
    "6-8":   ("8-10", "10-12"),
    "8-10":  ("10-12", "12-15"),
    "8-12":  ("10-12", "12-15"),
    "10-12": ("12-15", "12-15"),
    "12-15": ("12-15", "15-20"),
    "15-20": ("15-20", "15-20"),
    "20-25": ("20-25", "20-25"),
}
# Support work does not need the main lift's volume on top of it. A strength
# block wrote 5 x 5-7 on every compound after the first, four of them in one
# session — twenty heavy pressing sets on a chest day.
_SECONDARY_MAX_SETS = 4


def _role_prescription(rx: dict, role: str) -> dict:
    """The goal's week prescription, shifted for what this exercise is doing."""
    sets = int(rx.get("sets", 3)) + _ROLE_SETS.get(role, 0)
    if role == "accessory":
        sets = min(sets, _ACCESSORY_MAX_SETS)
    elif role == "secondary":
        sets = min(sets, _SECONDARY_MAX_SETS)
    sets = max(_MIN_SETS, min(_MAX_SETS, sets))

    reps = rx.get("reps", "10-12")
    parsed = _parse_reps(reps)
    tiers = _TIER_REPS.get(str(reps).replace("\u2013", "-"))
    if tiers and role in ("secondary", "accessory"):
        reps = tiers[0] if role == "secondary" else tiers[1]
    elif parsed:
        delta = _rep_delta(parsed[1], role)
        reps = f"{parsed[0] + delta}-{parsed[1] + delta}" if delta else reps

    rest = int(rx.get("rest_seconds", 60)) * _ROLE_REST.get(role, 1.0)
    floor = _ROLE_MIN_REST.get(role, 40)
    if role == "primary":
        floor = max(floor, int(rx.get("base_rest_seconds", 0)))
    rest = max(floor, int(rest / 5 + 0.5) * 5)
    return {"sets": sets, "reps": reps, "rest_seconds": rest}


# What a strength block's main lift is loaded with. A heavy triple is a
# free-weight or plate-loaded movement; a cable row or a lat pulldown at 3-5
# reps is a machine set to the top of its stack, and it opened a strength
# block's second upper day.
_STRENGTH_MAIN_EQUIPMENT = {"barbell", "dumbbell", "kettlebell", "machine"}


def _can_lead(ex: dict, scheme=None) -> bool:
    if scheme != "strength":
        return True
    return ((ex.get("equipment") or "").lower() in _STRENGTH_MAIN_EQUIPMENT
            and _movement_pattern(ex) != "pull_v")


def _assign_roles(selected: list, primary_slots: int, scheme=None) -> list:
    """Label each selected exercise with the job it does in the session."""
    roles = []
    taken = 0
    for ex in selected:
        if ex.get("category") == "cardio":
            roles.append("conditioning")
        # `role` from the library has the final say on what may lead a session.
        # Compound-and-a-primary-pattern was the best available proxy while the
        # library did not state it, and a loaded carry satisfies both — so a core
        # day opened with a farmer's walk, under a header promising 3 x 8-10.
        elif (taken < primary_slots and ex.get("role", "main") == "main"
              and _is_compound(ex) and _movement_pattern(ex) in _PRIMARY_PATTERNS
              and _can_lead(ex, scheme)):
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
    # Calibrated 2026-10 against Strength Level's published standards
    # (strengthlevel.com, ~2M logged lifts, read at a 70 kg man and a 60 kg
    # woman). "Intermediate" here is the midpoint of their Novice and
    # Intermediate rows — their population is people who log lifts, which runs
    # stronger than the people this app serves, so their median is not ours.
    #
    # The table it replaced was written from memory and ran 15-30% light on the
    # main lifts and about HALF on isolation work: an untrained woman was told
    # to hammer-curl 1-2 kg and lateral-raise 1-2 kg, and an intermediate man to
    # lateral-raise 3-4 kg against a published novice 1RM of 9. A load that is
    # obviously too light is ignored, and with it the rest of the number column.
    # lower body
    "squat":         1.44, "front_squat": 1.15, "leg_press": 2.40, "hack_squat": 1.60,
    "deadlift":      1.71, "romanian":    1.28, "hip_thrust": 1.60, "good_morning": 0.70,
    "swing":         0.35,
    "lunge":         0.70, "step_up":     0.55, "calf_raise": 1.00,
    "leg_extension": 0.80, "leg_curl":    0.60, "hip_abduction": 0.50,
    # horizontal push
    "bench":         1.07, "incline_press": 0.90, "chest_press": 0.98, "fly": 0.50,
    # vertical push
    "overhead_press": 0.66, "upright_row": 0.55, "lateral_raise": 0.43,
    "front_raise":   0.36, "rear_delt":   0.34,
    # pull
    "row":           0.95, "pulldown":    0.96, "shrug": 1.35, "face_pull": 0.45,
    "pullover":      0.40,
    # arms and trunk
    "curl":          0.50, "triceps_extension": 0.42, "pushdown": 0.62,
    "core":          0.30,
    # Classes the curated library names that the name-matcher never had, because
    # a name-matcher can only price what it recognises and everything else fell
    # through to the muscle group's main lift. These are the movements that
    # fallback priced wrongly, and the cuff drill is the extreme of it: four to
    # six kilos for an 80 kg lifter, against the 17-22.5 kg it used to be quoted.
    "external_rotation": 0.06,
    "floor_press":   0.95, "dip":          0.25, "push_press":   0.85,
    "straight_arm_pulldown": 0.45,
    "hammer_curl":   0.48, "preacher_curl": 0.44, "skullcrusher": 0.42,
    "pallof":        0.25, "side_bend":    0.90, "cable_woodchop": 0.30,
    "farmers_carry": 1.00, "suitcase_carry": 0.70,
}

# The curated library and this table grew their vocabularies separately — the
# library names a movement the way a coach would ("back_squat"), this table the
# way the old name-matcher did ("squat"). Aliasing keeps ONE set of calibrated
# numbers rather than two that can drift apart.
_LOAD_CLASS_ALIAS = {
    "back_squat":        "squat",
    "romanian_deadlift": "romanian",
    "bench_press":       "bench",
    "decline_press":     "bench",
    "barbell_row":       "row",
    "seated_row":        "row",
    "chest_supported_row": "row",
    "triceps_pushdown":  "pushdown",
    "weighted_crunch":   "core",
    "kettlebell_swing":  "swing",
    "split_squat":       "lunge",
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
# Strength Level's Beginner row sits at 0.61 of the midpoint above on the
# barbell lifts and their Advanced row at 1.47; untrained and advanced are set a
# little inside both, because a first-session estimate that errs light costs a
# set and one that errs heavy costs a back.
_LIFT_LEVEL = {"untrained": 0.50, "beginner": 0.72, "intermediate": 1.00, "advanced": 1.45}
# Averages, not ceilings. Lower-body strength is closer between the sexes than
# upper-body strength, which one flat factor cannot express.
_LIFT_SEX = {"upper": 0.62, "lower": 0.67}
_LOWER_CLASSES = {"squat", "front_squat", "leg_press", "hack_squat", "deadlift", "romanian",
                  "hip_thrust", "good_morning", "lunge", "step_up", "calf_raise",
                  "leg_extension", "leg_curl", "hip_abduction", "swing"}
# One implement, two hands on it. A swing priced per hand told a beginner to
# swing 29 kg in each of them.
_TWO_HANDED = {"swing"}

# A dumbbell pair carries about 80% of the barbell load for the same movement, so
# each hand takes 40% of it. Cable stacks read a little low against a free
# weight through the pulley (Strength Level: seated cable row 63 kg against a
# bent-over row of 66 at the same level); machines read close to it.
_IMPLEMENT_FACTOR = {"barbell": 1.00, "machine": 1.00, "smith": 1.00,
                     "cable": 0.85, "dumbbell": 0.40, "kettlebell": 0.40}
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
    """What this movement is loaded like.

    The curated library names it outright. The fallbacks below are for a library
    that does not, and the second of them is the reason the field exists: when a
    movement matched no name pattern it was priced as its MUSCLE GROUP'S main
    lift, so an external rotation — a cuff drill done with four kilos — was
    quoted at 17-22.5 kg per hand because it trains the shoulder and a shoulder
    press is what shoulders are loaded with. 90 of 502 priced movements were
    reaching that fallback."""
    stated = ex.get("load_class")
    if stated:
        return _LOAD_CLASS_ALIAS.get(stated, stated)
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


# Kettlebells come in fixed sizes, and someone training with one owns one or two
# of them — "25-27.5 kg" is not a bell. The quote names the bells either side of
# the estimate, lighter first, and never says "per hand": a kettlebell plan is
# written for a single bell, worked one side at a time where the movement is
# one-armed.
_BELL_SIZES = (4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 48)


def _load_basis(ex: dict, lift, calibration) -> str:
    """Where the number came from. A load the practitioner logged and a load
    inferred from their bodyweight deserve different amounts of trust, and the
    card used to present both as "a starting estimate from your bodyweight"."""
    cal = calibration or {}
    logged = (cal.get("by_exercise") or {}).get(ex.get("id"))
    if logged:
        return f"from your logged {logged.get('source', 'sets')}"
    source = (cal.get("source") or {}).get(lift)
    if source:
        return f"from {source}"
    if cal.get("by_class"):
        return "scaled from the lifts you entered"
    return "a starting estimate from your bodyweight"


def _bell_for(load: float, basis: str = "a starting estimate from your bodyweight") -> str:
    lighter = max([b for b in _BELL_SIZES if b <= load * 1.05] or [_BELL_SIZES[0]])
    heavier = min([b for b in _BELL_SIZES if b > lighter] or [lighter])
    if load <= _BELL_SIZES[0] or heavier == lighter:
        text = f"A {lighter} kg bell"
    else:
        text = f"A {lighter} kg bell, moving to {heavier} kg"
    return (f"{text} · {basis} — move up a bell when every set reaches the top of the "
            "range with clean form")


def _fmt_kg(kg: float) -> str:
    return f"{kg:.1f}".rstrip("0").rstrip(".")


def _bodyweight_of(user_profile: dict, gender_key: str) -> float:
    try:
        kg = float(user_profile.get("weight_kg") or 0)
    except (TypeError, ValueError):
        kg = 0.0
    return kg if 30 <= kg <= 250 else _DEFAULT_BODYWEIGHT[gender_key]


# How the week's load relates to week one, matched to what each week's own note
# tells the practitioner to do. Strength deloads 20% and the others 15%, which is
# what those notes say; the peak week adds a little, which is what "add weight if
# form is solid" means.
#
# Without this the quoted range was computed once and printed under all four
# weeks — so the deload week's note said "reduce weight 15%" directly above a
# number identical to week one's, and the peak week said "add weight" above the
# same. The engine already knew which week was the deload; the load display was
# simply never asked. Same fault as the session-length heading that echoed the
# request back over a shorter session: the number on the card and the instruction
# beside it were different products.
_WEEK_LOAD_FACTOR = {
    "strength":        (1.00, 1.05, 1.08, 0.80),
    "muscle_gain":     (1.00, 1.00, 1.05, 0.85),
    "fat_loss":        (1.00, 1.00, 1.00, 0.90),
    "endurance":       (1.00, 1.00, 1.00, 0.90),
    "general_fitness": (1.00, 1.00, 1.05, 0.90),
}


def _week_load_factor(scheme: str, week: int) -> float:
    factors = _WEEK_LOAD_FACTOR.get(scheme, _WEEK_LOAD_FACTOR["general_fitness"])
    return factors[min(max(week, 1), len(factors)) - 1]


# ── What a set of N costs ────────────────────────────────────────────────────
#
# `_LIFT_BW` is a one-rep-max standard, and the quoted load used to be that
# standard ±15% whatever the set was: an intermediate 75 kg lifter was given the
# same 80–107.5 kg squat for sets of 3-5 and for sets of 15-20. The top of that
# range is their whole 1RM, so the plan asked for twenty reps at a weight they
# could lift once. Every higher-rep scheme — fat loss, endurance, muscle gain,
# which is most users — was over-prescribed by the whole of the gap.
#
# A set of N taken to two reps short of failure (the "last 2 reps are hard" the
# card already tells them) is lifted at the load whose max is N + 2, and Epley
# gives the fraction of 1RM that is.
_REPS_IN_RESERVE = 2
# What a prescription with no rep range (a direct call, a hold) is priced at.
_REFERENCE_REPS = 10

# Strength does not scale with bodyweight one for one. It follows muscle cross-
# section, which grows as mass to the two-thirds — the allometric exponent the
# strength-sport literature normalises by. Linear scaling priced a 118 kg
# sedentary beginner's first deadlift at 60-82 kg for sets of fifteen: every
# extra kilo of bodyweight bought a kilo and a half of bar, as though it were
# muscle.
_ALLOMETRIC_EXPONENT = 0.67

# Strength falls about one percent a year from the forties, and faster later. A
# starting estimate that errs light costs a set; one that errs heavy is how a
# first session injures someone. An 80-year-old sedentary beginner was quoted the
# same 32.5–45 kg bench press as a 25-year-old.
_AGE_LOAD_FROM = 40
_AGE_LOAD_PER_YEAR = 0.01
_AGE_LOAD_FLOOR = 0.60
# A body still growing is started lighter than its bodyweight suggests; the
# technique is the adaptation being trained, not the load.
_YOUTH_LOAD_FACTOR = 0.80

# An Olympic bar weighs 20 kg before a plate goes on it. The rack lifts below are
# done with one; a curl or a skull-crusher usually is not (EZ-bars and fixed
# barbells go far lighter), so they are not held to it.
_EMPTY_BAR_KG = 20.0
_LIGHTEST_BAR_KG = 7.5
_LIGHTEST_STACK_KG = 4.0
_RACK_LIFTS = {"squat", "front_squat", "deadlift", "romanian", "good_morning",
               "hip_thrust", "bench", "incline_press", "floor_press", "overhead_press",
               "push_press", "row", "shrug", "upright_row"}


def _rep_fraction(reps) -> float:
    """Share of one-rep max a set of `reps` is lifted at, two reps in reserve."""
    parsed = _parse_reps(reps)
    top = parsed[1] if parsed else _REFERENCE_REPS
    return 1.0 / (1.0 + (top + _REPS_IN_RESERVE) / 30.0)


def _age_load_factor(age) -> float:
    try:
        age = int(age)
    except (TypeError, ValueError):
        return 1.0
    if age < _YOUTH_AGE:
        return _YOUTH_LOAD_FACTOR
    if age <= _AGE_LOAD_FROM:
        return 1.0
    return max(_AGE_LOAD_FLOOR, 1.0 - _AGE_LOAD_PER_YEAR * (age - _AGE_LOAD_FROM))


def _is_two_handed(ex: dict, lift: str) -> bool:
    """One implement held in both hands. A goblet squat is one dumbbell at the
    chest, and was quoted "per hand" — which reads as a pair."""
    return (lift in _TWO_HANDED or bool(_GOBLET.search(ex.get("name", "")))
            or bool(_BOTH_HANDS.search(ex.get("name", ""))))


_GOBLET = re.compile(r"\bgoblet\b", re.I)
_GOBLET_SHARE = 0.35
# "Dumbbell Overhead Triceps Extension - Two Hands" is one dumbbell held in both
# hands, and was quoted "per hand". One dumbbell lifted by two arms is about
# two thirds of what a pair would total (Strength Level's two-handed dumbbell
# triceps extension against their single-arm one).
_BOTH_HANDS = re.compile(r"\btwo hands?\b|\bboth hands\b|\bkettlebell deadlift\b", re.I)
_BOTH_HANDS_SHARE = 0.65
# Done holding a single dumbbell. "14-16 kg per hand" on a side bend reads as a
# pair, and the movement is a side bend because the other hand is empty.
_ONE_HAND_LIFTS = {"side_bend", "suitcase_carry"}


def _standard_1rm(lift: str, strength_level: str, gender: str,
                  bodyweight: float | None = None, age=None) -> float:
    """The bilateral barbell one-rep max the standards predict for this person."""
    gender_key = "female" if str(gender).lower() in ("female", "f", "woman") else "male"
    level = strength_level if strength_level in _LIFT_LEVEL else "beginner"
    reference = _DEFAULT_BODYWEIGHT[gender_key]
    scaled = reference * ((bodyweight or reference) / reference) ** _ALLOMETRIC_EXPONENT
    load = _LIFT_BW[lift] * scaled * _LIFT_LEVEL[level]
    if gender_key == "female":
        load *= _LIFT_SEX["lower" if lift in _LOWER_CLASSES else "upper"]
    elif str(gender or "").lower() not in ("male", "m", "man"):
        load *= (1 + _LIFT_SEX["lower" if lift in _LOWER_CLASSES else "upper"]) / 2
    return load * _age_load_factor(age)


# ── Calibrating to what the practitioner actually lifts ─────────────────────
#
# Every load was priced from bodyweight, sex, age and a self-rated training age.
# That lands inside published standards on average and can be well off for any
# one trained lifter — an advanced man benching 140 was quoted 92.5-107.5 kg for
# triples. Two sources correct it:
#
#   * `known_lifts` on the gym form — "a weight you can lift N times with good
#     form" for five anchor lifts. Each rescales the movements that share its
#     muscles and pattern; movements no anchor covers move part of the way, by
#     the average of the anchors given.
#   * logged sets (`workout_logs`) — the heaviest recent set of THAT exercise,
#     which replaces the estimate outright. A logged lift is a measurement; an
#     anchor is still an inference.
_ANCHOR_FAMILIES = {
    "squat": {"squat", "front_squat", "leg_press", "hack_squat", "lunge", "step_up",
              "leg_extension", "calf_raise", "hip_abduction"},
    "deadlift": {"deadlift", "romanian", "hip_thrust", "good_morning", "swing", "leg_curl"},
    "bench": {"bench", "incline_press", "chest_press", "floor_press", "fly", "dip",
              "triceps_extension", "skullcrusher", "pushdown"},
    "overhead_press": {"overhead_press", "push_press", "lateral_raise", "front_raise",
                       "upright_row", "rear_delt", "external_rotation"},
    "row": {"row", "pulldown", "face_pull", "shrug", "straight_arm_pulldown", "pullover",
            "curl", "hammer_curl", "preacher_curl", "farmers_carry", "suitcase_carry"},
}
# A typo ("600" for 60) should not write a plan around it.
_CALIBRATION_BOUNDS = (0.35, 3.0)
# The share of an anchor's correction that reaches a movement no anchor covers.
_UNANCHORED_SHARE = 0.6
# The entered set is "a weight you can lift N times with good form" — taken as
# one rep short of failure.
_ENTERED_RIR = 1


def _one_rm(kg: float, reps: int, rir: int = 0) -> float:
    """Epley, counting the reps left in reserve as reps the set could have had."""
    return float(kg) * (1.0 + (int(reps) + rir) / 30.0)


def _load_calibration(known_lifts, logged=None, *, strength_level="beginner",
                      gender="male", bodyweight=None, age=None) -> dict | None:
    """{by_class, default, source, by_exercise} or None when there is nothing to
    calibrate from."""
    by_class, sources, ratios = {}, {}, []
    lo, hi = _CALIBRATION_BOUNDS
    for anchor, entry in (known_lifts or {}).items():
        if anchor not in _ANCHOR_FAMILIES or not isinstance(entry, dict):
            continue
        try:
            kg, reps = float(entry["kg"]), int(entry["reps"])
        except (KeyError, TypeError, ValueError):
            continue
        model = _standard_1rm(anchor, strength_level, gender, bodyweight, age)
        if model <= 0 or kg <= 0 or reps <= 0:
            continue
        ratio = max(lo, min(hi, _one_rm(kg, reps, _ENTERED_RIR) / model))
        ratios.append(ratio)
        label = anchor.replace("_", " ")
        for lift in _ANCHOR_FAMILIES[anchor]:
            by_class[lift] = ratio
            sources[lift] = f"your {_fmt_kg(kg)} kg × {reps} {label}"
    default = 1.0
    if ratios:
        mean = 1.0
        for r in ratios:
            mean *= r
        mean **= 1.0 / len(ratios)
        default = 1.0 + (mean - 1.0) * _UNANCHORED_SHARE
    by_exercise = dict(logged or {})
    if not by_class and not by_exercise:
        return None
    return {"by_class": by_class, "default": default, "source": sources,
            "by_exercise": by_exercise}


def _estimated_load(ex: dict, strength_level: str, gender: str,
                    bodyweight: float | None = None, week_factor: float = 1.0,
                    reps=None, age=None, calibration=None):
    """The working load for one set of this lift, or None if it is not priced.

    Returns (kg, per_hand, implement, lift)."""
    eq = (ex.get("equipment") or "bodyweight").lower()
    if (ex.get("category") or "").lower() == "cardio":
        return None
    if eq in ("bodyweight", "other", "bands", "resistance_bands"):
        return None
    implement = next(iter(_EQUIPMENT_ALIASES.get(eq, {eq})))
    factor = _IMPLEMENT_FACTOR.get(implement)
    lift = _lift_class(ex)
    if factor is None or lift is None:
        return None

    per_hand = implement in _PER_HAND and not _is_two_handed(ex, lift)
    logged = ((calibration or {}).get("by_exercise") or {}).get(ex.get("id"))
    if logged:
        # A measurement of this exercise, in the units it is performed in (per
        # hand for a dumbbell pair). Nothing about the model applies to it.
        return (float(logged["one_rm"]) * _rep_fraction(reps) * week_factor,
                per_hand, implement, lift)

    # "Other" and unanswered sex take the midpoint of the two standards, as the
    # diet path's energy equation does. Age is inside the standard too.
    load = _standard_1rm(lift, strength_level, gender, bodyweight, age)
    if calibration:
        load *= (calibration.get("by_class") or {}).get(lift, calibration.get("default", 1.0))
    load *= factor if per_hand else _IMPLEMENT_FACTOR["barbell"]
    if implement in _PER_HAND and _BOTH_HANDS.search(ex.get("name", "")):
        load = min(load * _BOTH_HANDS_SHARE, _DUMBBELL_CEILING)
    if implement in _PER_HAND and _GOBLET.search(ex.get("name", "")):
        # One dumbbell held at the chest, priced until now as the barbell front
        # squat it shares a load class with: an intermediate 72 kg man was quoted
        # a 46-51 kg goblet squat, a dumbbell most gyms do not own. The grip and
        # the upper back give out long before the legs do; Strength Level's
        # goblet squat sits at about a third of their front squat.
        load = min(load * _GOBLET_SHARE, _DUMBBELL_CEILING)
    if per_hand:
        # A one-arm dumbbell press is the same dumbbell as a two-arm one — the
        # practitioner just does the sides in turn. Halving it here would have
        # priced the single-arm variant of every movement at half the weight it
        # is actually performed with. Unilateral only costs load when the
        # implement is shared between the limbs.
        load = min(load, _DUMBBELL_CEILING)
    elif _UNILATERAL.search(ex.get("name", "")):
        load *= 0.5

    load *= _rep_fraction(reps)
    load *= week_factor
    return load, per_hand, implement, lift


def _below_the_bar(ex: dict, **kw) -> bool:
    """A barbell lift whose working load is lighter than the bar it is done with.

    The rack lifts use a 20 kg bar. Curls and skull-crushers use an EZ-bar or a
    fixed barbell, and those start at about 7.5 kg — so an obese 55-year-old was
    written a "2-3 kg" barbell curl, which is not a weight that exists."""
    est = _estimated_load(ex, **kw)
    if not est:
        return False
    kg, _, implement, lift = est
    if implement != "barbell":
        return False
    return kg < (_EMPTY_BAR_KG if lift in _RACK_LIFTS else _LIGHTEST_BAR_KG)


def _unloaded_progression(ex: dict) -> str:
    """How a movement with no weight on it gets harder, in its own words.

    The library authors an `easier` and a `harder` step for every bodyweight and
    band movement, and nothing read them: the load column printed a ladder keyed
    on the MUSCLE, so a glute bridge, a calf raise and a glute kickback all told
    the practitioner to progress to a pistol squat, and a wall-angel row to a
    weighted pull-up. Across a 400-plan sweep that was 574 exercise rows. A
    bodyweight set has no number to raise, so the next step IS the progression —
    it is the one thing this field has to get right."""
    eq = (ex.get("equipment") or "bodyweight").lower()
    head = "Band" if eq in ("bands", "resistance_bands") else "Bodyweight"
    prog = ex.get("progression") or {}
    # Most movements' authored note already reads "Too hard? Use X. Too easy?
    # Move to Y" and is shown directly beneath; saying it twice in one card is
    # how a reader learns to skip both.
    if prog.get("harder") and prog["harder"] in (ex.get("modification") or ""):
        return head if head == "Bodyweight" else "Band · choose a band that makes the last 2 reps hard"
    parts = []
    if prog.get("harder"):
        parts.append(f"Next step: {prog['harder']} (once every set reaches the top of the range)")
    if prog.get("easier"):
        parts.append(f"Easier option: {prog['easier']}")
    if parts:
        return f"{head} · " + " · ".join(parts)
    if head == "Band":
        return "Band · choose a band that makes the last 2 reps hard"
    return _BODYWEIGHT_PROGRESSIONS.get(
        _muscle_key(ex), "Bodyweight · slow the tempo or add a pause to progress")


def _get_weight_range(ex: dict, strength_level: str, gender: str,
                      bodyweight: float | None = None,
                      week_factor: float = 1.0, reps=None, age=None,
                      calibration=None) -> str:
    """A starting load for THIS set of this lift, for this person."""
    eq = (ex.get("equipment") or "bodyweight").lower()
    if (ex.get("category") or "").lower() == "cardio":
        # It said "see intensity note", and there is no intensity note on the
        # page for conditioning. The talk test is the effort scale that needs
        # no equipment and holds under a beta-blocker, which a heart rate does
        # not (ACSM).
        if ex.get("rep_style") == "interval":
            return ("Hard intervals at about 8/10 — too breathless to talk; easy intervals "
                    "at a walk until your breathing settles")
        return ("Steady, about 5–6/10 — breathing harder, but you can still talk in "
                "full sentences")

    if eq in ("bodyweight", "other", "bands", "resistance_bands"):
        return _unloaded_progression(ex)

    est = _estimated_load(ex, strength_level, gender, bodyweight, week_factor, reps, age,
                          calibration=calibration)
    if est is None:
        # An unpriced movement says so rather than guessing. It is the honest
        # answer, and it is what the old table gave 35–55 kg for.
        return "Moderate weight · adjust so the last 2 reps are hard and form holds"
    load, per_hand, implement, lift = est

    if implement == "barbell" and lift in _RACK_LIFTS and _round_load(load) < _EMPTY_BAR_KG:
        # Selection keeps these away from anyone with another way to train the
        # pattern; this is for the practitioner whose only implement is the bar.
        return (f"Empty bar (20 kg) — heavier than your ~{_fmt_kg(_round_load(load))} kg "
                "starting estimate, so take fewer reps than written until it moves "
                "cleanly for all of them")
    if implement in ("machine", "cable") and _round_load(load) < _LIGHTEST_STACK_KG:
        # A weight stack starts at its first plate. "Dip Machine 1-2 kg" was
        # written for a 72-year-old; there is no such setting to choose.
        return ("The lightest setting on the stack — lighter than that is not needed yet; "
                "add a plate when every set reaches the top of the range")
    if implement == "barbell" and lift not in _RACK_LIFTS and load < _LIGHTEST_BAR_KG:
        return ("The lightest EZ-bar or fixed barbell (about 7.5–10 kg) — heavier than "
                f"your ~{_fmt_kg(_round_load(load))} kg starting estimate, so take fewer "
                "reps than written until it moves cleanly")

    basis = _load_basis(ex, lift, calibration)
    if implement == "kettlebell":
        return _bell_for(load, basis)

    # The estimate is the load two reps short of failure, so it is the top of the
    # range: the bottom is where a first session should start.
    lo, hi = _round_load(load * 0.85), _round_load(load)
    # The bottom of the range cannot be lighter than the bar either: a row quoted
    # "18–22.5 kg" starts below what an empty bar weighs.
    if implement == "barbell":
        lo = max(lo, _EMPTY_BAR_KG if lift in _RACK_LIFTS else _LIGHTEST_BAR_KG)
    # Light isolation rounds to a single plate step and the range collapses —
    # "2–2 kg" reads as a defect rather than a starting point.
    if hi <= lo:
        hi = _round_load(lo + (1.0 if lo < 20 else 2.5))
    unit = (" in one hand" if lift in _ONE_HAND_LIFTS
            else " per hand" if per_hand else "")
    return (f"{_fmt_kg(lo)}–{_fmt_kg(hi)} kg{unit} · {basis} — adjust so the last 2 reps "
            f"are hard and form holds")


# ── Ayurvedic Rest Day Recovery ───────────────────────────────────────────────

# Rest-day activities and Ayurvedic tips are prose, and prose passes no gate —
# the same fault the warm-up had, in the one place where the practices carry
# genuine contraindications rather than merely being unsuitable.
#
# `Kapalabhati` reached a hypertensive, a cardiac and a pregnant practitioner in
# two separate fields. The yoga engine has had a deliberate gate for exactly this
# since the demo-hardening pass, and its own comment reads: forceful breath
# "can never reach a hypertensive, cardiac, epileptic, glaucoma, hernia, or
# pregnant user". Both features read the same profile. The gym engine simply
# never asked.
#
# The vocabulary is imported rather than restated. Two copies of a safety list is
# how they drift apart, and the yoga one is the one that has been reviewed.
_RESTRICTED_PRACTICE = {
    # substring matched against the practitioner's declared conditions, the same
    # way `_pranayama_hard_blocked` matches, so "high_blood_pressure" catches a
    # "hypertension" tag and the reverse.
    "kapalabhati": ("hypertension", "high_blood_pressure", "heart", "cardiac",
                    "epilep", "seizure", "hernia", "glaucoma", "retina",
                    "vertigo", "pregnan", "ulcer", "recent_surgery", "stroke"),
    "bhastrika":   ("hypertension", "high_blood_pressure", "heart", "cardiac",
                    "epilep", "seizure", "hernia", "glaucoma", "pregnan", "stroke"),
    "sun salutation": ("pregnan", "hypertension", "herniated_disc",
                       "lower_back_pain", "wrist_injury", "shoulder_injury"),
    "vigorous":    ("heart", "cardiac", "hypertension", "pregnan"),
    "breath retention": ("hypertension", "high_blood_pressure", "heart",
                         "cardiac", "epilep", "pregnan", "glaucoma"),
    # The Pitta rest day recommends swimming to every Pitta practitioner, and the
    # epilepsy note beside it says never to swim alone.
    "swimming": ("epilep", "seizure"),
    # The Vata rest day's restorative line is two supine poses. The pregnancy
    # note on the same plan says to avoid lying flat on the back after the first
    # trimester; nothing compared the two.
    "supta baddha": ("pregnan",),
    "legs-up-the-wall": ("pregnan",),
    # The same position in the model's own words. A pregnant reviewer persona's
    # coaching said "a few minutes of legs-elevated rest" on the line the gate
    # reads, and the names above are all it matched.
    "legs up the wall": ("pregnan",),
    "legs-elevated": ("pregnan",),
    "legs elevated": ("pregnan",),
    "supine": ("pregnan",),
}

# What the line is replaced with when it is withheld — same intent, no
# contraindication. A rest day that silently loses an item reads as an oversight.
_PRACTICE_SUBSTITUTES = {
    "kapalabhati": "Anulom Vilom (alternate nostril breathing, no retention) — 10 min",
    "bhastrika": "Anulom Vilom (alternate nostril breathing, no retention) — 10 min",
    "sun salutation": "Gentle joint-mobility sequence — 10 min, moving with the breath",
    "vigorous": "Brisk walk — 30 min at a pace where talking takes effort but stays possible",
    "breath retention": "Even-count breathing without retention — 10 min",
    "swimming": ("Water activity only with someone beside you who knows your condition — "
                 "otherwise an easy evening walk"),
    "supta baddha": ("Side-lying rest with a pillow between the knees, or sitting reclined "
                     "against cushions — 10 min of slow breathing"),
}
for _phrase in ("legs up the wall", "legs-elevated", "legs elevated", "supine"):
    _PRACTICE_SUBSTITUTES[_phrase] = _PRACTICE_SUBSTITUTES["supta baddha"]


# The same practices by what they do, in `engine.movement_risk`'s vocabulary. A
# 78-year-old cardiac patient's Kapha rest day prescribed five rounds of sun
# salutation — repeated forward folds, the head dropped below the heart, the
# weight on the wrists — because the condition list above names neither age nor
# the mechanisms. The Vata day's "Legs-Up-The-Wall" is an inversion.
_PRACTICE_RISK = {
    "sun salutation": {"spinal_flexion", "intracranial_pressure", "wrist_weight_bearing"},
    "legs-up-the-wall": {"intracranial_pressure"},
}
_PRACTICE_SUBSTITUTES["legs-up-the-wall"] = (
    "Restorative rest — lie on your side with a pillow between the knees, or sit "
    "reclined against cushions — 10 min of slow breathing")


def _gate_practices(lines, conditions, is_pregnant, risks=frozenset()):
    """Withhold a restricted practice from the practitioner it is restricted for,
    and put something equivalent in its place."""
    tokens = {str(c).lower() for c in conditions if c}
    if is_pregnant:
        tokens.add("pregnancy")
    if not tokens and not risks:
        return list(lines)
    out = []
    for line in lines:
        low = line.lower()
        swapped = None
        for practice, contra in _RESTRICTED_PRACTICE.items():
            if practice not in low:
                continue
            if any(tok in uc or uc in tok for tok in contra for uc in tokens):
                swapped = _PRACTICE_SUBSTITUTES[practice]
                break
        if swapped is None:
            for practice, mechanisms in _PRACTICE_RISK.items():
                if practice in low and mechanisms & set(risks):
                    swapped = _PRACTICE_SUBSTITUTES[practice]
                    break
        out.append(swapped or line)
    return out


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


# Body composition changes what a session can safely ask for, and how much of it
# the practitioner can absorb. `bmi_category` was echoed into `user_summary` and
# read by nothing; `activity_level` was not read at all. A sedentary 118 kg
# beginner and an active 118 kg beginner were given the same plan.
# TWO vocabularies reach this field and they are not the same one. `BMICalculator`
# defines seven bands (severely_underweight … obese_class3); `routes/profile.py`
# computes BMI inline on save and writes four (underweight / normal / overweight /
# obese), and it is the route's value that lands on the user document. Reading
# only the calculator's names meant a live user at BMI 32.8 came back `obese`,
# fell through to `normal`, and was prescribed the jump training this map exists
# to keep away from them. Both vocabularies are read; see
# `test_every_bmi_category_the_profile_can_write_is_understood`.
_BMI_GROUPS = {
    "severely_underweight": "underweight", "underweight": "underweight",
    "normal": "normal", "normal_weight": "normal",
    "overweight": "overweight",
    "obese": "obese",
    "obese_class1": "obese", "obese_class2": "obese", "obese_class3": "obese",
    "severely_obese": "obese", "morbidly_obese": "obese",
}

# Impact is a property of the movement, and the dataset has no tag for it — its
# contraindication vocabulary describes joints, not forces. Jumping, skipping,
# bounding and running land at several times bodyweight through the knee and the
# ankle; at obese classifications that is the wrong risk to open a programme
# with, whatever the practitioner's training age. Everything else stays: squats,
# lunges, the whole resistance library, and the low-impact conditioning that
# actually suits the goal.
_IMPACT_NAME = re.compile(
    r"\b(jump|jumping|skip|skipping|rope|sprint|running|run|burpee|jack|jacks|"
    r"hop|hops|bound|bounding|plyo|leap|high knee|depth|tuck jump)\b", re.I)

# Training volume someone can absorb from where they are starting. The same shape
# as `_LEVEL_SET_DELTA`: reps and rest belong to the goal, and how much of them a
# body recovers from is a property of the practitioner.
_ACTIVITY_SET_DELTA = {"sedentary": -1, "light": 0, "moderate": 0,
                       "active": 0, "very_active": +1}


def _bmi_group(bmi_category) -> str:
    return _BMI_GROUPS.get(str(bmi_category or "").lower(), "normal")


def _is_impact(ex: dict) -> bool:
    """Landing force, stated rather than guessed. The name regex missed butt
    kicks, carioca and the acceleration drills — 21 movements in all."""
    stated = ex.get("impact")
    if stated:
        return stated == "high"
    return (ex.get("category") == "plyometrics"
            or bool(_IMPACT_NAME.search(ex.get("name", ""))))


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


# ── Mechanisms ────────────────────────────────────────────────────────────────
#
# The contraindication tokens above name body parts, and 62 of the 70 conditions
# onboarding offers are not body parts — so they changed nothing. A glaucoma
# patient was given decline push-ups and heavy triples; someone with epilepsy a
# barbell over the face; osteoporosis kept the crunches, twists and side bends
# its fracture mechanism is about, because only the axial lifts carried its tag.
#
# `risk_tags` on each movement name what it does (`gym_library/mechanisms.py`),
# and `engine.movement_risk` — the map the yoga engine already used — names the
# conditions each mechanism endangers. One map, both features.
#
# Past sixty, head-below-heart positions are withheld as the yoga engine does.
# Fall risk is not blanket-applied by age here: a loaded lunge is one thing, but
# balance and stepping are what older adults most need to keep, and the
# conditions that make a fall likely — or dangerous — reach it on their own.
_SENIOR_RISKS = frozenset({"intracranial_pressure"})

# Joint conditions for which landing impact is the aggravating load. Obesity,
# age and training age already withheld impact; osteoarthritis, the commonest
# joint disease there is, did not.
_IMPACT_CONDITIONS = ("arthritis", "gout", "osteoporosis", "osteopenia", "fibromyalgia",
                      "lupus", "neuropathy", "knee_replacement", "hip_replacement",
                      "plantar", "chronic_fatigue", "long_covid", "varicose",
                      # Declared rather than computed: `bmi_category` withheld
                      # impact, and the same person saying "obesity" did not.
                      "obes")


def _conditions_and_injuries(user_profile) -> list:
    return [*(user_profile.get("medical_history") or []),
            *(user_profile.get("injuries_or_limitations") or [])]


def _avoided_risks(user_profile, extra=()) -> set:
    """Mechanisms this practitioner's movements must not carry.

    A hernia or a recent abdominal operation is the same mechanism whether it was
    declared as a condition or ticked as an injury, so both lists go through both
    maps."""
    declared = _conditions_and_injuries(user_profile)
    risks = condition_risk_tags(declared)
    risks |= injury_risk_tags(declared)
    if _age_group(user_profile.get("age")) == "senior":
        risks |= _SENIOR_RISKS
    risks |= {str(t).lower() for t in extra or ()} & RISK_VOCAB
    return risks


def _withholds_impact(user_profile) -> bool:
    if _bmi_group(user_profile.get("bmi_category")) == "obese":
        return True
    # The pool has kept jump training from beginners since the plyometrics pass;
    # the warm-up beside it still opened a sedentary beginner's first session
    # with jumping jacks and high knees.
    if (user_profile.get("fitness_level") or "beginner") == "beginner":
        return True
    # A sedentary 47-year-old who rated himself intermediate opened every session
    # with jumping jacks. `_steady_only` already reads a sedentary answer as
    # "moderate continuous work first"; landing is the same question.
    if str(user_profile.get("activity_level") or "").lower() == "sedentary":
        return True
    if _age_group(user_profile.get("age")) in ("senior", "youth"):
        return True
    return any(term in str(c).lower() for c in _conditions_and_injuries(user_profile)
               for term in _IMPACT_CONDITIONS)


# ── Injuries ──────────────────────────────────────────────────────────────────
#
# Two vocabularies again, and nothing between them. The profile field describes
# itself as "bad_knee / lower_back / shoulder / wrist / neck / ankle / hip"; the
# library's tokens are `bad_knee`, `lower_back_pain`, `shoulder_injury`,
# `rotator_cuff`, `wrist_injury`, `neck_injury`, `bad_ankle`, `hip_injury`. The
# filter intersected them directly, so of the seven documented values only
# `bad_knee` would ever have matched — had any screen collected the field, which
# none did. The gym form now asks, and this translates.
_INJURY_TOKENS = {
    "knee_replacement": {"knee_replacement", "bad_knee"},
    "knee":             {"bad_knee"},
    "lower_back":       {"lower_back_pain"},
    "back":             {"lower_back_pain"},
    "disc":             {"herniated_disc", "lower_back_pain"},
    "shoulder":         {"shoulder_injury", "rotator_cuff"},
    "elbow":            {"elbow_injury"},
    "wrist":            {"wrist_injury"},
    "neck":             {"neck_injury", "cervical_spondylosis"},
    "hip":              {"hip_injury"},
    "ankle":            {"bad_ankle"},
    # Mechanisms, not body parts: `engine.movement_risk` reads the words.
    "hernia":           set(),
    "abdominal_surgery": set(),
}
_INJURY_SPLIT = re.compile(r"[,;/\n]|\band\b", re.I)


def _injury_phrases(user_profile, gym_prefs) -> list:
    phrases = [str(i) for i in (user_profile.get("injuries_or_limitations") or [])]
    phrases += [str(i) for i in (gym_prefs.get("injuries") or [])]
    detail = gym_prefs.get("injury_detail")
    if detail:
        phrases += [p.strip() for p in _INJURY_SPLIT.split(str(detail)) if p.strip()]
    return phrases


def _resolve_injuries(user_profile, gym_prefs) -> tuple:
    """(what the gates read, the typed phrases nothing could act on).

    The words themselves are kept beside the tokens, because the mechanism maps
    match on them — "wrist" and "hernia" reach `engine.movement_risk`, and
    `hip_replacement` reaches the impact gate."""
    resolved, unmatched = set(), []
    for phrase in _injury_phrases(user_profile, gym_prefs):
        low = phrase.lower().replace("-", "_")
        low = " ".join([low, *(v for k, v in _LIMITATION_ALIASES.items() if k in low)])
        hits = {k for k in _INJURY_TOKENS if k in low.replace(" ", "_") or k in low}
        risky = injury_risk_tags([low]) | condition_risk_tags([low])
        if not hits and not risky and not any(k in low for k in _INJURY_RISK_TAGS):
            unmatched.append(phrase)
            continue
        resolved.add(low.strip())
        for k in hits:
            resolved |= _INJURY_TOKENS[k]
    return sorted(resolved), unmatched


def _injury_notice(unmatched) -> str | None:
    """Silence would read as "we took that into account"."""
    if not unmatched:
        return None
    named = ", ".join(f"“{u}”" for u in unmatched)
    return (f"We could not match {named} to anything this plan knows how to adjust "
            "for, so no exercise was removed because of it. Show the plan to a "
            "physiotherapist or doctor before starting, and skip anything that "
            "reproduces the pain.")


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
    # Only equipment the library actually holds. `box` was in here and in
    # nothing else, so the alias named a machine no exercise could be selected by.
    "cardio_machines":  {"treadmill", "stationary_bike", "rowing_machine", "elliptical",
                         "stair_climber", "air_bike", "battle_ropes"},
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


# ── Likes and dislikes ────────────────────────────────────────────────────────
#
# `exercise_preferences` — `{"likes": [...], "dislikes": [...]}` — has been in the
# schema since the beginning and was never read, and the form never collected it.
# Someone who cannot stand burpees had nowhere to say so, and would have been
# ignored if they had.
#
# A term matches an exercise on its name, its movement pattern, its lift class or
# its equipment, so "deadlift" removes the whole hinge family by name, "cardio"
# removes conditioning, and "barbell" removes an implement. That is deliberately
# loose: someone typing a dislike is describing a category, not selecting rows.
_PREFERENCE_SPLIT = re.compile(r"[,;/]| and ", re.I)


def _squash(text: str) -> str:
    """Lowercase and drop everything that is not a letter or digit.

    The dataset writes "Pullups", a practitioner writes "pull-up", and the yoga
    engine learned the same lesson about hyphens. Squashing both sides is what
    makes the two the same word.
    """
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _preference_terms(value) -> list:
    if isinstance(value, str):
        value = _PREFERENCE_SPLIT.split(value)
    terms = []
    for term in value or []:
        squashed = _squash(term)
        if len(squashed) >= 3:
            terms.append(squashed)
    return terms


def _matches_preference(ex: dict, terms: list) -> bool:
    if not terms:
        return False
    haystack = _squash(" ".join((
        ex.get("name", ""),
        ex.get("equipment", ""),
        ex.get("category", ""),
        _movement_pattern(ex),
        _lift_class(ex) or "",
    )))
    return any(term in haystack for term in terms)


# A dislike is a preference, not a contraindication. Honouring one must never
# leave a muscle group too thin to build a day from — the practitioner said they
# would rather not, not that they cannot.
_MIN_PER_MUSCLE_AFTER_DISLIKES = 8


def _apply_dislikes(scored: list, terms: list) -> tuple:
    """Drop disliked exercises, and put back the ones a muscle group cannot spare."""
    if not terms:
        return scored, []
    kept = [(score, ex) for score, ex in scored if not _matches_preference(ex, terms)]
    dropped = [(score, ex) for score, ex in scored if _matches_preference(ex, terms)]
    if not dropped:
        return scored, []

    counts: dict = {}
    for _, ex in kept:
        key = _muscle_key(ex)
        counts[key] = counts.get(key, 0) + 1

    restored = []
    for score, ex in dropped:
        key = _muscle_key(ex)
        if counts.get(key, 0) < _MIN_PER_MUSCLE_AFTER_DISLIKES:
            kept.append((score, ex))
            counts[key] = counts.get(key, 0) + 1
            restored.append(ex.get("name", ""))
    kept.sort(key=lambda pair: pair[0], reverse=True)
    return kept, restored


# ── Exercise filtering ────────────────────────────────────────────────────────

# Self-myofascial release — foam rolling. Named as a suffix throughout the
# dataset ("Adductors-Smr", "Peroneals-Smr"); the `-` matters, since `_MOVEMENT_
# PATTERNS` has to keep reading "Smith" and "Smr" apart.
_SMR_NAME = re.compile(r"-\s*smr\b", re.I)


def filter_exercises(user_profile, gym_prefs, exercises, extra_avoid_tags=None,
                     preference_report=None):
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
    prefs = gym_prefs.get("exercise_preferences") or {}
    likes = _preference_terms(prefs.get("likes"))
    dislikes = _preference_terms(prefs.get("dislikes"))
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
    risks = _avoided_risks(user_profile, extra_avoid_tags)
    withhold_impact = _withholds_impact(user_profile)

    scored = []
    for ex in exercises:
        eq = ex.get("equipment", "bodyweight").lower()
        if eq not in available_eq and eq != "bodyweight":
            continue
        if ex.get("level", "intermediate") not in allowed_levels:
            continue
        # Whether they can PERFORM it, which the level field never described. A
        # pull-up is an ordinary thing to programme and an impossible thing for
        # an untrained 118 kg beginner to do — and `Pullups 3x15-20` is exactly
        # what they were given, 4,897 times across a sweep. The progression
        # ladder in the entry is how they get there.
        floor = ex.get("skill_floor")
        if floor and _LEVEL_RANK.get(floor, 1) > _LEVEL_RANK.get(user_level, 0):
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
        # Impact, not category. The curated library records landing force as its
        # own field and files jump work as the conditioning it is, so keying this
        # gate on `category == "plyometrics"` would have quietly stopped firing —
        # and a beginner asking for endurance would have been back on jump
        # training, which is the exact thing this gate was written for.
        if user_level == "beginner" and (ex.get("impact") == "high"
                                         or ex.get("category") == "plyometrics"):
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
        # The curated library states what slot a movement may occupy, so this is
        # now one field rather than an accumulating list of things that turned
        # out not to be lifts. Before the field existed, 46% of generated
        # training days prescribed at least one stretch as a working set —
        # `Seated Front Deltoid` 518 times across a sweep — because a stretch
        # whose name did not contain the word "stretch" was filed as `strength`
        # by the importer and nothing downstream could tell the difference.
        role = ex.get("role")
        if role and role not in _POOL_ROLES:
            continue
        if not role and (ex.get("category") == "stretching"
                         or _SMR_NAME.search(ex.get("name", ""))):
            continue
        # Jump training is the wrong risk for a 65-year-old and for a body still
        # growing, whatever level they enter.
        #
        # Keyed on `impact`, not on `category == "plyometrics"`. The curated
        # library records landing force as its own field and files jump work as
        # the conditioning it is, so the category test silently stopped matching
        # anything and a 65-year-old was offered jumping jacks. The beginner gate
        # above had the same fault and was fixed; this one was missed, which is
        # why `_is_impact` now backs both rather than each testing its own thing.
        # And for a body carrying enough mass that the landing forces are the
        # limiting factor rather than the muscles, and for the joint conditions
        # landing aggravates. Resistance work is untouched — squats, lunges and
        # the whole library stay; it is the airborne half that goes.
        if withhold_impact and _is_impact(ex):
            continue
        if risks.intersection(ex.get("risk_tags") or ()):
            continue
        # Conditioning is exempt from the goal gate. The dataset marks cardio
        # unsuitable for `muscle_gain` and `strength` — true of what it builds,
        # and not the question being asked of a finisher, whose goal IS
        # conditioning. Without the exemption a hypertrophy lifter asking for
        # heavy cardio had none available to give them. How much of it they get
        # is `_conditioning_days`' decision, not this gate's.
        if (ex.get("category") != "cardio"
                and not ex.get("goal_suitability", {}).get(gym_goal, False)):
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
        # A like outranks every other preference in the scoring, because it is the
        # only one the practitioner typed themselves. It reorders the pool; it does
        # not reach past the safety gates above, which have all already run.
        if _matches_preference(ex, likes):
            score += 5
        scored.append((score, ex))

    scored.sort(key=lambda x: x[0], reverse=True)
    scored, restored = _apply_dislikes(scored, dislikes)
    if preference_report is not None:
        preference_report["dislikes_overridden"] = restored
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
# Roles that may fill a working slot. `warmup` and `mobility` movements are
# still prescribed — as the warm-up and cool-down the session already has — but
# never as a set of eight with a weight next to it.
_WORKING_ROLES = ("main", "accessory")
# Conditioning survives the filter — it is the finisher, and `generate_gym_plan`
# lifts it straight back out into its own pool. Excluding it here emptied that
# pool and a fat-loss plan came back with no conditioning at all.
_POOL_ROLES = ("main", "accessory", "finisher")
_LEVEL_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}

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
    stated = ex.get("bucket")
    if stated:
        return stated
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

# A week built around the region the practitioner asked to prioritise.
#
# `target_muscle_focus` is a required field in the gym form — Full Body, Upper,
# Lower, Core or Back — and nothing read it. Someone who said "my back is the
# priority" got the same four-day split as someone who said "core", which is the
# split everybody got.
#
# Emphasis is a second day for the region, not the removal of the others: every
# schedule below still trains legs, still pushes and still pulls. A specialised
# block that drops a movement pattern is how people get hurt in the eleventh week,
# and it is not what someone means when they say they want to focus on their back.
# Emphasis schedules, per training age.
#
# An emphasis has to give the region MORE work than the balanced week does — that
# is the whole content of the field. Two ways it failed to:
#
#   * The novice tables written alongside the split fix reused the same `upper`
#     and `lower` days the balanced week uses, so an "upper" emphasis had the
#     same two upper days and one fewer lower day. It only took work away.
#   * Making the intermediate baseline better (push/pull/legs twice, rather than
#     one day per body part) raised the bar the emphasis tables had to clear, and
#     the six-day lower and back emphases quietly stopped clearing it.
#
# Both were caught by `test_the_region_you_asked_to_prioritise_gets_more_work`,
# which compares against the balanced week rather than against a fixed number —
# which is why it kept working when the baseline moved.
_BEGINNER_FOCUS_SCHEDULES = {
    "upper": {
        4: ["upper", "lower", "rest", "upper", "upper", "rest", "rest"],
        5: ["upper", "lower", "rest", "upper", "lower", "upper", "rest"],
        6: ["upper", "lower", "core_cardio", "upper", "lower", "upper", "rest"],
    },
    "lower": {
        4: ["lower", "upper", "rest", "lower", "lower", "rest", "rest"],
        5: ["lower", "upper", "rest", "lower", "upper", "lower", "rest"],
        6: ["lower", "upper", "core_cardio", "lower", "upper", "lower", "rest"],
    },
    "back": {
        4: ["pull", "lower", "rest", "upper", "pull", "rest", "rest"],
        5: ["pull", "lower", "rest", "upper", "pull", "core_cardio", "rest"],
        6: ["pull", "lower", "core_cardio", "upper", "pull", "lower", "rest"],
    },
    "core": {
        4: ["upper", "legs_core", "rest", "upper", "core_cardio", "rest", "rest"],
        5: ["upper", "legs_core", "core_cardio", "shoulders_core", "legs_core",
            "rest", "rest"],
        6: ["upper", "legs_core", "core_cardio", "shoulders_core", "legs_core",
            "core_cardio", "rest"],
    },
}

# Intermediate and advanced. These were body-part weeks — a "lower" emphasis
# was legs, push, legs-and-core, pull and a core day — and once the balanced
# week moved to push / pull / legs and upper / lower, which trains everything
# twice, four of them gave the emphasised region LESS work than not asking:
# advanced six-day lower came out 42 leg sets against 54 balanced.
# `test_the_region_you_asked_to_prioritise_gets_more_work` caught it, as it was
# written to. An emphasis is now the balanced structure with the region trained
# a third time, never a body-part week.
_FOCUS_SCHEDULES = {
    "upper": {
        4: ["upper", "lower", "rest", "push", "pull", "rest", "rest"],
        5: ["push", "pull", "lower", "rest", "upper", "shoulders_arms", "rest"],
        6: ["push", "pull", "legs_core", "push", "pull", "arms", "rest"],
    },
    "lower": {
        4: ["lower", "upper", "rest", "legs", "rest", "lower", "rest"],
        5: ["lower", "push", "legs", "rest", "pull", "lower", "rest"],
        6: ["legs", "push", "lower", "pull", "legs", "upper", "rest"],
    },
    "back": {
        4: ["pull", "lower", "rest", "upper", "back_biceps", "rest", "rest"],
        5: ["pull", "push", "legs", "rest", "upper", "back_biceps", "rest"],
        6: ["pull", "push", "legs", "back_biceps", "upper", "pull", "rest"],
    },
    "core": {
        4: ["upper", "legs_core", "rest", "shoulders_core", "legs_core", "rest", "rest"],
        5: ["push", "pull", "legs_core", "rest", "upper", "core_cardio", "rest"],
        6: ["push", "pull", "legs_core", "upper", "legs_core", "core_cardio", "rest"],
    },
}
# Below four days there is one balanced rotation and no room for a second day of
# anything. Saying so beats quietly ignoring the field, which is what used to
# happen at every day count.
_MIN_DAYS_TO_SPECIALISE = 4


# A strength block is built around the squat, the bench, the deadlift and the
# press, each trained heavy at least twice a week — upper/lower or whole-body
# days, which is how every mainstream strength programme is laid out. A
# body-part split is a hypertrophy structure: an advanced lifter asking to get
# STRONGER was written a "Chest" day of four bench-press variants and a
# "Shoulders & Arms" day, squatting and deadlifting once a week.
_STRENGTH_SCHEDULES = {
    2: ["full_body", "rest", "rest", "full_body", "rest", "rest", "rest"],
    3: ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"],
    4: ["upper", "lower", "rest", "upper", "lower", "rest", "rest"],
    5: ["upper", "lower", "rest", "upper", "lower", "core_cardio", "rest"],
    6: ["upper", "lower", "core_cardio", "upper", "lower", "core_cardio", "rest"],
}


def _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level,
                           muscle_focus="full_body", goal=None):
    days = min(workout_days, 6)
    if (goal == "strength" and fitness_level != "beginner"
            and muscle_focus in (None, "full_body") and not is_bodyweight_only):
        return list(_STRENGTH_SCHEDULES.get(max(days, 2)))
    if fitness_level == "beginner":
        specialised = _BEGINNER_FOCUS_SCHEDULES.get(muscle_focus, {}).get(days)
    else:
        specialised = _FOCUS_SCHEDULES.get(muscle_focus, {}).get(days)
    if specialised and not (is_bodyweight_only and fitness_level == "beginner"):
        return specialised
    return _base_weekly_schedule(workout_days, is_bodyweight_only, fitness_level)


def _base_weekly_schedule(workout_days, is_bodyweight_only, fitness_level):
    if is_bodyweight_only and fitness_level == "beginner":
        if workout_days <= 2:
            return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
        elif workout_days == 3:
            return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]
        else:
            return ["full_body", "rest", "full_body", "rest", "full_body", "core_cardio", "rest"]

    # HOW OFTEN each muscle is trained, which is the variable a split exists to
    # set — and which used to be the same for everybody. `fitness_level` was
    # passed into this function and read for exactly one case (bodyweight-only
    # beginners); everyone else, novice or competitive, got the same body-part
    # split. A "Chest & Triceps day" trains the chest ONCE a week. That is a
    # structure for an advanced lifter with years of accumulated work, and it is
    # the single most recognisable sign a plan was not written by a coach.
    #
    # Novices adapt to frequency: two or three exposures per muscle per week, at
    # low complexity. Intermediates can carry push/pull/legs. A body-part split
    # is the reward for being advanced enough to need it.
    if fitness_level == "beginner":
        if workout_days == 2:
            return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
        elif workout_days == 3:
            return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]
        elif workout_days == 4:
            return ["upper", "lower", "rest", "upper", "lower", "rest", "rest"]
        elif workout_days == 5:
            return ["upper", "lower", "rest", "upper", "lower", "core_cardio", "rest"]
        elif workout_days >= 6:
            return ["upper", "lower", "core_cardio", "upper", "lower", "core_cardio", "rest"]

    # Three days of push / pull / legs trains each muscle ONCE a week, which is
    # the frequency the body-part split was taken away from novices for. The
    # meta-analytic evidence (Schoenfeld, Ogborn & Krieger 2016) favours twice a
    # week at every training age, and three days affords it only as whole-body
    # sessions. Five days was push / pull / legs / upper and then a "Core" day —
    # forty-five minutes of planks and crunches for someone training to grow.
    # Push / pull / legs then upper / lower trains everything twice.
    if fitness_level == "intermediate":
        if workout_days == 2:
            return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
        elif workout_days == 3:
            return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]
        elif workout_days == 4:
            return ["upper", "lower", "rest", "upper", "lower", "rest", "rest"]
        elif workout_days == 5:
            return ["push", "pull", "legs", "rest", "upper", "lower", "rest"]
        elif workout_days >= 6:
            return ["push", "pull", "legs", "push", "pull", "legs", "rest"]

    if workout_days == 2:
        return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
    elif workout_days == 3:
        return ["upper", "rest", "lower", "rest", "full_body", "rest", "rest"]
    elif workout_days == 4:
        return ["chest_triceps", "rest", "back_biceps", "legs", "rest", "shoulders_core", "rest"]
    elif workout_days == 5:
        return ["push", "pull", "legs", "rest", "upper", "lower", "rest"]
    elif workout_days == 6:
        # Was chest_triceps / back_biceps / legs / shoulders / arms — which hits the
        # triceps on Monday and again on Friday, and the biceps on Tuesday and again
        # on Friday, while the chest and the back get one day each. Weekly volume
        # came out 18 sets of triceps against 12 of chest. Once the week is long
        # enough to afford a dedicated arm day, the arms come OFF the push and pull
        # days; that is what the arm day is for.
        #
        # That split then trained the legs once a week and closed on a core day.
        # Six days is enough for push / pull / legs twice, which gives every
        # muscle the twice-weekly frequency at the volume an advanced lifter
        # carries — the arm and shoulder work rides on the push and pull days.
        return ["push", "pull", "legs", "push", "pull", "legs", "rest"]
    if workout_days >= 7:
        # The schema accepts 7 and the form offers it, and nothing here handled it
        # — a request for seven training days fell through to the catch-all below
        # and came back as THREE full-body days. Silently, with four rest days the
        # practitioner had not asked for.
        #
        # Seven lifting days is not a programme; the seventh day is where the
        # adaptation happens. So the week is the six-day split with its rest day
        # turned into the active-recovery day the engine already writes per dosha
        # — abhyanga and a walk for Vata, a brisk 30 minutes for Kapha — and
        # `_schedule_notice` says that is what happened.
        return ["push", "pull", "legs", "push", "pull", "legs", "rest"]
    return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]


def _focus_notice(muscle_focus, workout_days, is_bodyweight_only, fitness_level) -> str | None:
    """Say when the requested emphasis could not shape the week."""
    if muscle_focus not in _FOCUS_SCHEDULES:
        return None
    region = {"upper": "upper body", "lower": "lower body",
              "core": "core", "back": "back"}[muscle_focus]
    if is_bodyweight_only and fitness_level == "beginner":
        return (f"You asked to prioritise the {region}. A bodyweight beginner's week is "
                f"built from full-body sessions, which is the right place to start and "
                f"leaves no separate day to give the {region}. Adding equipment, or "
                f"moving past beginner, opens the split up.")
    if workout_days < _MIN_DAYS_TO_SPECIALISE:
        return (f"You asked to prioritise the {region}, and a {workout_days}-day week has "
                f"room for one balanced rotation and no second day of anything. This plan "
                f"trains you evenly; four days a week is where an emphasis starts to mean "
                f"something.")
    return None


def _adaptation_notice(bmi_group: str, activity_level) -> str | None:
    """Say what the practitioner's starting point changed about the plan."""
    parts = []
    if bmi_group == "obese":
        parts.append(
            "This plan leaves out jumping, skipping and running. Landing forces run to "
            "several times bodyweight through the knee and ankle, and at your current "
            "weight that is the limiting factor rather than the muscles — so the "
            "conditioning here is low-impact, and it works just as well. Squats, lunges "
            "and the rest of the resistance work are untouched.")
    if bmi_group == "underweight":
        parts.append(
            "Conditioning is kept light here. Putting mass on means holding onto a "
            "surplus, and the resistance work is what asks the body to build with it.")
    if str(activity_level or "").lower() == "sedentary":
        parts.append(
            "Starting volume is one set below the standard prescription. Coming from a "
            "sedentary baseline, the first month is about turning up — the volume goes "
            "up from there, and it will still be more than enough to be sore.")
    return " ".join(parts) or None


def _preference_notice(report: dict) -> str | None:
    """Say when a dislike could not be honoured in full.

    Removing every rowing movement leaves nothing to train a back with, and a plan
    that quietly trains one muscle less because of a typed preference is worse
    than one that says it kept a few.
    """
    overridden = report.get("dislikes_overridden") or []
    if not overridden:
        return None
    shown = ", ".join(sorted(set(overridden))[:3])
    return (f"You asked to avoid some of these movements, and this plan still includes "
            f"{shown}{' and others' if len(set(overridden)) > 3 else ''}. Leaving them out "
            f"would have left a muscle group with too little to train it. Everything else "
            f"you named has been kept out.")


def _cardio_notice(goal, preference, finisher_days: int, training_days: int) -> str | None:
    """Say when the amount of conditioning is not what the goal would have chosen.

    Both directions matter. Someone who asked for none on a fat-loss plan should
    know what they have opted out of; someone who asked for heavy on a strength
    block should know why they did not get it every day.
    """
    if preference == "none" and goal in _FINISHER_GOALS:
        return ("You asked for no cardio, so this plan has none — every session is "
                "resistance training. For fat loss that puts the entire energy deficit "
                "on what you eat, since lifting alone burns comparatively little. It is "
                "a workable plan; it is a harder one.")
    if preference == "heavy" and goal in _MAX_CONDITIONING_SHARE and finisher_days < training_days:
        return (f"You asked for heavy cardio. This plan ends {finisher_days} of your "
                f"{training_days} sessions with conditioning rather than all of them — "
                f"daily conditioning on a {goal.replace('_', ' ')} block interferes with "
                f"the adaptation the block is for. Add walking or cycling on the recovery "
                f"day if you want more.")
    return None


def _main_lifts_of(week: dict) -> list:
    """The block's main lifts, by name and load, in the order they are performed."""
    lifts = []
    seen = set()
    for day in week.get("days", []):
        for ex in day.get("main_workout", []):
            if ex.get("role") != "primary" or ex["exercise_name"] in seen:
                continue
            seen.add(ex["exercise_name"])
            lifts.append({
                "exercise": ex["exercise_name"],
                "day": day.get("focus"),
                "load": ex.get("weight_range", "").split(" · ")[0],
            })
    return lifts


def _progression_spine(four_week_plan: list, scheme: str) -> list:
    """One entry per week: what changes, by how much, and on which lifts."""
    table = _GOAL_WEEKS.get(scheme, _GOAL_WEEKS["general_fitness"])
    main_lifts = _main_lifts_of(four_week_plan[0]) if four_week_plan else []
    spine = []
    for i, week in enumerate(four_week_plan):
        rx = week["prescription"]
        spine.append({
            "week": week["week"],
            "theme": week["theme"],
            "main_lift_prescription": f"{rx['sets']} × {rx['reps']}, {rx['rest_seconds']}s rest",
            "role_prescriptions": week.get("role_prescriptions", {}),
            "note": table[min(i, 3)]["note"],
            "is_deload": week["theme"].lower().startswith("deload"),
            "main_lifts": main_lifts,
        })
    return spine


# What to put in a day's place when its own muscle cannot be trained, most
# generally useful first. A day that becomes a second back day is honest; a day
# that keeps its name and fills with wrist curls is not.
_SUBSTITUTE_FOCUSES = ("legs", "back", "full_body", "core_cardio", "arms",
                       "chest", "pull", "push", "shoulders")
# Below this a muscle group cannot fill even the shortest session. Kept in step
# with `_MIN_EXERCISES`, which is declared further down the module.
_TRAINABLE_MINIMUM = 3


def _focus_headline(focus: str):
    """The muscle a focus day is named for — the first entry of its allocation.

    Read lazily rather than precomputed, because `_FOCUS_ALLOCATION` is defined
    further down the module than this is used.
    """
    alloc = _FOCUS_ALLOCATION.get(focus)
    return alloc[0][0] if alloc else None


def _trainable_muscles(muscle_split: dict) -> set:
    return {key for key, pool in muscle_split.items() if len(pool) >= _TRAINABLE_MINIMUM}


def _resolve_untrainable_days(schedule: list, muscle_split: dict) -> tuple:
    """Replace focus days whose own muscle group has been filtered away.

    A rotator-cuff injury correctly empties the chest and shoulder pools — that
    gating is the feature working. But the week was still built from a fixed
    split, so it kept a Shoulders day and a Push day, and the day builder's
    fallback filled them from whatever was left: a live plan came back with a
    27-minute "Shoulders" session of wrist curls and neck isometrics, and a
    "Push" day of five triceps movements and no pressing.

    Naming a day for a muscle it does not contain is the part that reads as
    broken. The safe list is right; the timetable has to follow it.
    """
    trainable = _trainable_muscles(muscle_split)
    candidates = [f for f in _SUBSTITUTE_FOCUSES if _focus_headline(f) in trainable]
    replacements = {}
    resolved = []
    # Spread the replacements over what IS trainable instead of stacking them on
    # the first thing that fits. Taking the head of the list every time turned a
    # week with three unbuildable days into four identical leg days.
    used = collections.Counter(f for f in schedule if _focus_headline(f) in trainable)
    for focus in schedule:
        headline = _focus_headline(focus)
        if focus == "rest" or headline is None or headline in trainable:
            resolved.append(focus)
            continue
        substitute = min(candidates, key=lambda f: (used[f], candidates.index(f))) \
            if candidates else "full_body"
        used[substitute] += 1
        replacements.setdefault(focus, substitute)
        resolved.append(substitute)
    return resolved, replacements


def _substitution_notice(replacements: dict) -> str | None:
    if not replacements:
        return None
    swaps = ", ".join(f"{was.replace('_', ' ')} → {now.replace('_', ' ')}"
                      for was, now in sorted(replacements.items()))
    return (f"Your injuries and health details leave too little in the library to build "
            f"some of the days this split would normally have, so they have been "
            f"replaced rather than filled with whatever was left over ({swaps}). This is "
            f"the safe list doing its job — but it does mean a muscle group is going "
            f"untrained, which is worth raising with a physiotherapist.")


def _schedule_notice(requested_days: int, schedule: list) -> str | None:
    """Say when the week that was built is not the week that was asked for."""
    built = sum(1 for focus in schedule if focus != "rest")
    if built >= requested_days:
        return None
    if requested_days >= 7:
        return (
            "You asked to train seven days a week; this plan trains six and keeps the "
            "seventh for active recovery. Muscle is built between sessions, not during "
            "them — a week with no recovery day accumulates fatigue faster than it "
            "accumulates training. The recovery day is not a day off: it has its own "
            "prescription below.")
    return (f"This plan trains {built} days a week rather than the {requested_days} you "
            f"asked for — your equipment and level do not support more distinct sessions "
            f"than that without repeating one.")


def _focus_to_keys(focus):
    # Shoulders were missing, so no full-body day — the whole week of a novice,
    # a teenager or anyone training two or three days — could contain an
    # overhead press, whatever its pattern list asked for.
    if "full_body" in focus:        return ["full_body", "chest", "back", "legs", "shoulders",
                                            "core", "biceps", "triceps"]
    elif focus == "upper":          return ["chest", "back", "shoulders", "biceps", "triceps"]
    elif focus == "lower":          return ["legs", "core"]
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
# Two of a family is a coach pairing a flat and an incline press. Two of an
# ISOLATION family is a barbell curl followed by an EZ-bar curl, which is one
# movement done twice. The cap could not tell them apart because it had one
# number, and the authored `family` field is what finally makes the distinction
# expressible.
_MAX_PER_FAMILY = 2
_MAX_PER_ISOLATION_FAMILY = 1
# Two compounds in a five-exercise day, one in a three. A session built of
# isolation work trains the same muscles for less, and the first pick being a
# compound is not enough on its own — the audit's week-one chest day had a
# machine press and then four accessories.
_MIN_COMPOUNDS = 2

# The patterns a session's main work is built from. A day holds at most
# `_pattern_cap(focus)` compounds of any one of them: one on a full-body, upper
# or lower day, whose job is to cover every pattern, and two on a day named for
# a region. Without it a 400-plan sweep produced 549 days that pressed or rowed
# the same way two to four times — a strength chest day of bench, floor press,
# incline bench and dumbbell bench at 5 sets each, and a leg day of a deadlift
# AND a Romanian deadlift after squats.
_CAPPED_PATTERNS = {"squat", "hinge", "lunge", "push_h", "push_v", "pull_h", "pull_v"}
_SPREAD_FOCUSES = {"full_body", "upper", "lower", "legs_core"}
# One loaded hinge a session, whatever the day is called. A glute bridge after a
# Romanian deadlift is a pairing; a sumo deadlift after one is the lower back
# taking the heaviest load of the week twice in an hour.
_HEAVY_HINGES = {"deadlift", "romanian", "good_morning"}
_LOW_VALUE_ACCESSORIES = {"shrug", "side_bend"}


def _pattern_cap(focus: str) -> int:
    return 1 if focus in _SPREAD_FOCUSES else 2


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
    # The vertical patterns come last, so a three-exercise home session still
    # opens on the legs, a push and a pull; a longer one gets an overhead press
    # and a pulldown rather than a second row. A 14-year-old's three full-body
    # days used to hold two horizontal presses each and no overhead press all
    # week.
    "full_body":       ("squat", "push_h", "pull_h", "hinge", "push_v", "pull_v"),
    "upper":           ("push_h", "pull_h", "push_v", "pull_v"),
    "lower":           ("squat", "hinge", "lunge"),
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
    # Arms last and lightest: a long full-body day finished on shrugs and side
    # bends because they were the only accessories its pool held.
    "full_body":       (("legs", 3), ("chest", 2), ("back", 2), ("shoulders", 1), ("core", 1),
                        ("biceps", 1), ("triceps", 1)),
    # Upper/lower. A novice needs each muscle two or three times a week, which a
    # body-part split cannot give — it trains everything once. These two days are
    # what makes a four-day beginner week a beginner's week.
    "upper":           (("chest", 3), ("back", 3), ("shoulders", 2), ("triceps", 1), ("biceps", 1)),
    "lower":           (("legs", 4), ("core", 1)),
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
    # Conditioning no longer arrives through the day's own pool — it is the
    # finisher, on the days `cardio_preference` puts one there — so this day is
    # trunk work plus whatever finishes it.
    "core_cardio":     (("core", 1),),
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
    r"\b(chain|chains|with bands|reverse band|board|box squat|pin press|guillotine|"
    r"tate|jm|smith|leverage|"
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


def _pattern_preference(ex, pattern: str, muscle_rank: dict, preferred_ids=(),
                        headline=None) -> tuple:
    """Sort key for filling a day's movement-pattern slot, best first.

    In order: a compound before an isolation movement; a movement the
    practitioner said they enjoy before one they did not mention; the muscle the
    day is named for before the one it is paired with; the movement the pattern is
    actually asking for before a cousin of it; then loadable and plainly named.

    A like sits under "is it a compound" and above everything else, so someone who
    says they love chin-ups opens their pull day with one — and someone who says
    they love cable flyes still does not open a chest day with them.
    """
    return (
        not _is_compound(ex),
        # A movement the library says can open a session, before one it says
        # supports it. A farmer's walk is a fine carry and a poor thing to build
        # a block around, and it took the primary slot on a core day — where the
        # week header then announced "3 sets of 8-10" over "3 x 20 m".
        ex.get("role", "main") != "main",
        ex["id"] not in preferred_ids,
        # Stated by the library. Name plainness was the proxy for it, and it
        # ranked "T-Bar Row" (three words) above "Bent Over Barbell Row" (four)
        # as the barbell row a back day is built around.
        not ex.get("canonical", False),
        muscle_rank.get(_muscle_key(ex), len(muscle_rank)),
        _lift_class(ex) not in (headline or _PATTERN_HEADLINE_LIFT).get(pattern, set()),
    ) + tuple(-v for v in _canonical_score(ex))


def _movement_pattern(ex) -> str:
    """The curated library states this. The name-matching below is the fallback
    for a library that does not, and it is why a hack squat was not a squat."""
    stated = ex.get("movement_pattern")
    if stated:
        return stated
    name = ex.get("name", "")
    for pattern, rx in _MOVEMENT_PATTERNS:
        if rx.search(name):
            return pattern
    return "isolation"


def _is_compound(ex) -> bool:
    """Counting secondary muscles decided a fly was a compound, which let it
    outrank the bench press for a chest day's main lift."""
    mech = ex.get("mechanic")
    if mech:
        return mech == "compound"
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
    stated = ex.get("family")
    if stated:
        return stated
    # Last two words of the name. It gave `shrug`, `shoulder shrug`, `leverag
    # shrug` and `middl shrug` for four shrugs, so a back day could hold all of
    # them: four families, one movement.
    core = _VARIANT_WORDS.sub(" ", ex.get("name", ""))
    core = re.sub(r"[^A-Za-z ]", " ", core).lower().split()
    return " ".join(_singular(w) for w in core[-2:]) if core else ex.get("id", "")


# How far down the preference order a repeated day is allowed to reach for its
# main lift. Deep enough that a second leg day squats something else; shallow
# enough that it is still one of the movements a coach would have picked.
_VARIANT_DEPTH = 3


# A full-body day that fits three exercises gets two from the pattern list and
# one rotating. Rotating the whole list by the day's variant turned
# (squat, push, pull, hinge) into (push, pull, hinge, squat) on the second
# full-body day, so a 20-minute home session came out as incline push-ups,
# doorway rows and a plank — a "full body" day with no legs in it. The swap now
# stays inside each half: squat trades with hinge, push with pull, and the lower
# body keeps its place at the front.
_PAIRED_ROTATION = {
    ("squat", "push_h", "pull_h", "hinge", "push_v", "pull_v"): (
        ("squat", "push_h", "pull_h", "hinge", "push_v", "pull_v"),
        ("hinge", "push_v", "pull_v", "squat", "push_h", "pull_h"),
        ("squat", "push_v", "pull_h", "hinge", "push_h", "pull_v"),
    ),
    # A second upper day that opened on a row put a cable row at the head of a
    # strength block. The second day presses overhead and pulls vertically
    # first, which is the other half of the upper body.
    ("push_h", "pull_h", "push_v", "pull_v"): (
        ("push_h", "pull_h", "push_v", "pull_v"),
        ("push_v", "pull_v", "push_h", "pull_h"),
    ),
    ("squat", "hinge", "lunge"): (
        ("squat", "hinge", "lunge"),
        ("hinge", "squat", "lunge"),
    ),
}


def _rotate_patterns(patterns: tuple, variant: int) -> tuple:
    paired = _PAIRED_ROTATION.get(patterns)
    if paired:
        return paired[variant % len(paired)]
    offset = variant % len(patterns)
    return patterns[offset:] + patterns[:offset]


def _choose(pool, n, seed_key, taken_ids, families, min_compounds=0, patterns=(),
            caps=None, per_muscle=None, muscle_rank=None, preferred_ids=(), variant=0,
            loadable_first=False, pattern_counts=None, pattern_cap=2, headline=None,
            prefer_barbell=False, rotate_patterns=True):
    """Pick n exercises, compounds first, without stacking one movement family.

    Selection was a plain shuffle-and-take, so nothing preferred a compound or
    noticed that it had chosen five variants of the same thing. Measured over 240
    generated days, 12-44% contained NO compound movement at all, and a week-one
    chest session came out as two flye variants, a pullover, a machine press and
    a dip machine — no flat press anywhere.
    """
    ordered = _deterministic_select(pool, len(pool), seed_key)
    if preferred_ids:
        # Movements the practitioner said they enjoy go to the front of the draw.
        # A higher pool score only decided whether a liked exercise SURVIVED the
        # cut, and selection shuffles uniformly over whatever survived — so a like
        # changed nothing for anything already in the library. The main lift is
        # unaffected: it is re-sorted by what the day needs, further down.
        ordered.sort(key=lambda ex: ex["id"] not in preferred_ids)
    picked = []
    taken_before = len(taken_ids)
    caps = caps or {}
    per_muscle = per_muscle if per_muscle is not None else {}
    muscle_rank = muscle_rank or {}
    pattern_counts = pattern_counts if pattern_counts is not None else collections.Counter()

    def _take(ex):
        picked.append(ex)
        taken_ids.add(ex["id"])
        families[_movement_family(ex)] += 1
        per_muscle[_muscle_key(ex)] = per_muscle.get(_muscle_key(ex), 0) + 1
        if _is_compound(ex):
            pattern_counts[_movement_pattern(ex)] += 1
        if _lift_class(ex) in _HEAVY_HINGES:
            pattern_counts["heavy_hinge"] += 1

    def _blocked(ex) -> bool:
        cap = (_MAX_PER_FAMILY if _is_compound(ex)
               else _MAX_PER_ISOLATION_FAMILY)
        # Bodyweight variants of one movement are difficulty levels of it, not a
        # pairing: a chest day came out Push-Up, Incline Push-Up and Knee Push-Up
        # — the same exercise at three levels, two of them too easy for whoever
        # can do the third.
        if (ex.get("equipment") or "bodyweight").lower() in ("bodyweight", "bands"):
            cap = 1
        if families[_movement_family(ex)] >= cap:
            return True
        if (_is_compound(ex) and _movement_pattern(ex) in _CAPPED_PATTERNS
                and pattern_counts[_movement_pattern(ex)] >= pattern_cap):
            return True
        if _lift_class(ex) in _HEAVY_HINGES and pattern_counts["heavy_hinge"] >= 1:
            return True
        key = _muscle_key(ex)
        return key in caps and per_muscle.get(key, 0) >= caps[key]

    # One exercise for each of the day's movement patterns, before anything else
    # competes for the slots. A leg day came out as step-ups, calf press, glute
    # kickback and flutter kicks — two compounds by the letter of the rule, and
    # nothing that squats or hinges.
    # A week can train the same muscle twice — a lower-body emphasis has two leg
    # days, and an emptied pool can put two back days in a week. Both used to open
    # with the identical two lifts, because the main-lift preference is
    # deterministic and nothing told the second day it was the second. Rotating
    # the pattern order makes one of them a squat day and the other a hinge day,
    # which is what a coach would have written anyway.
    if variant and patterns and rotate_patterns:
        patterns = _rotate_patterns(tuple(patterns), variant)

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
        candidates.sort(key=lambda ex: _pattern_preference(ex, pattern, muscle_rank,
                                                            preferred_ids, headline))
        if candidates:
            # Vary within the movements a coach would have picked, not past them.
            # Reaching for the third-best hinge is how a second leg day stops
            # repeating the first; reaching for a band-resisted deadlift because
            # it happens to sit third is not, so specialty variants are only
            # considered when there is nothing plain left to rotate through.
            plain = [ex for ex in candidates if not _SPECIALTY_NAME.search(ex.get("name", ""))]
            shortlist = plain if len(plain) > 1 else candidates
            # Rotation reached past the Romanian deadlift to the conventional one
            # on a hypertrophy block's second lower day — the variety step found
            # the lift `_headline_lifts` exists to keep out of high-rep sets.
            # Rotation varies between lifts that can lead a session. With a
            # thin pool the second-best candidate was an accessory: a
            # kettlebell-only lifter's second day pressed with a chest dip
            # instead of the press, and hinged with a swing instead of the
            # deadlift.
            leaders = [ex for ex in shortlist if ex.get("role", "main") == "main"]
            if leaders:
                shortlist = leaders
            # A strength block's second upper day opened on dumbbell presses at
            # 3-5, because rotation reached past the barbell. Heavy triples are
            # what the bar is for; variety in a strength block belongs in the
            # supporting work.
            if prefer_barbell:
                bars = [ex for ex in shortlist if (ex.get("equipment") or "") == "barbell"]
                shortlist = bars or shortlist
            if headline and "deadlift" not in headline.get(pattern, {"deadlift"}):
                shortlist = [ex for ex in shortlist if _lift_class(ex) != "deadlift"] or shortlist
            # Rotation varies WHICH lift opens a repeated day; it should not
            # vary whether the day opens with a lift at all. Reaching for the
            # third-best horizontal push in a fully equipped gym found an
            # incline push-up, because the pool is deep enough to have one and
            # the rotation did not care what it was loaded with.
            if loadable_first:
                # A movement the practitioner said they enjoy stays in the draw
                # whatever it is loaded with. Filtering on loadability alone
                # meant someone who wrote "I love pull-ups" could not be given
                # one in a gym that has a pull-up bar — the preference ranked
                # below a rule that had already removed it from the list.
                loaded = [ex for ex in shortlist
                          if ex["id"] in preferred_ids
                          or (ex.get("equipment") or "bodyweight").lower()
                          not in ("bodyweight", "bands")]
                shortlist = loaded or shortlist
            _take(shortlist[variant % min(len(shortlist), _VARIANT_DEPTH)])

    for want_compound in (True, False):
        if want_compound and min_compounds <= 0:
            continue
        have_compounds = sum(1 for ex in picked if _is_compound(ex))
        # The compounds are chosen plainest-first; the accessories keep the
        # shuffle, because variety belongs in the work that finishes a session
        # rather than in the lift the block is built around.
        # Accessories keep the shuffle for variety, but a practitioner standing
        # in a gym should not be handed a prone swimmer while the cable stack is
        # free. Loadable work sorts first when they have something to load —
        # an advanced back day came out as Superman Hold, Prone Swimmer and Wall
        # Angel Row, which are good movements written for someone with no
        # equipment at all.
        if want_compound:
            candidates_pass = sorted(
                ordered, key=lambda ex: (ex["id"] in preferred_ids,
                                         _canonical_score(ex)), reverse=True)
        elif loadable_first:
            candidates_pass = sorted(
                ordered, key=lambda ex: (ex["id"] in preferred_ids,
                                         _LOADABLE_RANK.get(
                                             (ex.get("equipment") or "bodyweight").lower(), 1)),
                reverse=True)
        else:
            candidates_pass = ordered
        if not want_compound:
            # Shrugs and side bends filled the last slot of every session for a
            # dumbbell-only lifter — legitimate movements, and the last thing a
            # short session should spend a slot on. They stay available; they
            # simply wait until nothing more useful is left.
            candidates_pass = sorted(candidates_pass,
                                     key=lambda ex: _lift_class(ex) in _LOW_VALUE_ACCESSORIES)
        for ex in candidates_pass:
            if want_compound and have_compounds >= min_compounds:
                break
            if len(picked) >= n:
                break
            # In a gym, an unloaded drill waits until the loaded compounds have
            # had their turn. The accessory pass ran before the compound
            # fallback, so a full-gym pull day took Prone Swimmer and Wall Angel
            # Row ahead of a cable row and a dumbbell row it never reached.
            if (loadable_first and not want_compound and ex["id"] not in preferred_ids
                    and (ex.get("equipment") or "bodyweight").lower() in ("bodyweight", "bands")):
                continue
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
    # Both fallbacks keep the loadable-first ordering. Without it a pull day
    # whose loaded families were spent finished on Wall Angel Row, Prone Swimmer
    # and Superman Hold — three bodyweight drills handed to someone standing in
    # front of a cable stack.
    fallback_order = (sorted(ordered, key=lambda ex: _LOADABLE_RANK.get(
        (ex.get("equipment") or "bodyweight").lower(), 1), reverse=True)
        if loadable_first else ordered)

    if len(picked) < n:
        for ex in fallback_order:
            if len(picked) >= n:
                break
            key = _muscle_key(ex)
            if ex["id"] in taken_ids or (key in caps and per_muscle.get(key, 0) >= caps[key]):
                continue
            # The family cap holds here as well. It used not to, which was
            # harmless while a family was two words off the end of a name and
            # every press variant counted as a different one — and stopped being
            # harmless the moment families were authored: a chest-and-triceps day
            # came out four `bench_press` movements deep.
            if _blocked(ex):
                continue
            _take(ex)

    # A pool too small or too uniform to respect either cap still has to produce a
    # session; both are preferences, not safety rules.
    # Only as far as the fewest exercises a session can be. Past that a day short
    # of distinct movements takes more sets of the ones it has (see
    # `_fill_session`) rather than a third variant of one of them — four bench
    # presses is not a longer chest day, it is the same one done badly.
    floor = min(n, max(_MIN_EXERCISES - taken_before, 0))
    if len(picked) < floor:
        # Family-blocked movements go to the back rather than being skipped: the
        # session still has to exist, but a fourth row variant is the last thing
        # it should reach for, not the first thing in the leftovers.
        for ex in sorted(fallback_order, key=_blocked):
            if len(picked) >= floor:
                break
            if ex["id"] in taken_ids:
                continue
            _take(ex)
    return picked


# The conventional deadlift is a strength lift. Written for sets of 8-20 it is
# the movement whose technique degrades first under fatigue, with the heaviest
# load in the programme on the spine; the Romanian deadlift trains the same
# hinge and the same muscles at a load that suits the reps. A hypertrophy leg
# day opened squat 4x8-10, deadlift 4x8-10; an endurance one, deadlift 4x15-20.
def _headline_lifts(scheme) -> dict:
    if scheme == "strength":
        return _PATTERN_HEADLINE_LIFT
    return {**_PATTERN_HEADLINE_LIFT, "hinge": {"romanian"}}


def _select_for_day(pool, target, user_id, focus, day_num, week, preferred_ids=(),
                    variant=0, loadable_first=False, scheme=None):
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
    core_n = max(1, target - _ROTATING_PER_DAY)
    taken: set = set()
    families: dict = collections.defaultdict(int)
    # The ceilings are for the whole day, so the stable core and the rotating slot
    # share one running count — otherwise the rotating exercise gets a fresh
    # budget and reopens the imbalance the ceilings exist to close.
    caps = _slot_allocation(focus, target)
    per_muscle: dict = {}
    muscle_rank = {key: i for i, (key, _) in enumerate(_FOCUS_ALLOCATION.get(focus, ()))}

    pattern_counts: collections.Counter = collections.Counter()
    cap = _pattern_cap(focus)
    core = _choose(pool, core_n, f"{user_id}-{focus}-d{day_num}-v{variant}-core",
                   taken, families, min_compounds=min(_MIN_COMPOUNDS, max(1, core_n - 1)),
                   patterns=_FOCUS_PATTERNS.get(focus, ()),
                   caps=caps, per_muscle=per_muscle, muscle_rank=muscle_rank,
                   preferred_ids=preferred_ids, variant=variant,
                   loadable_first=loadable_first, pattern_counts=pattern_counts,
                   pattern_cap=cap, headline=_headline_lifts(scheme),
                   prefer_barbell=scheme == "strength")
    # The rotating slot drew accessories only, so a three-exercise session — the
    # 20-minute one — was a squat, a press and a barbell shrug, every day, and a
    # hypertensive executive never rowed. A pattern the core left uncovered is
    # filled first, and the week varies WHICH lift fills it.
    covered = {_movement_pattern(ex) for ex in core if _is_compound(ex)}
    # In the order the day itself used, so a day that opened hinge-and-press
    # takes its pull next, not a second press.
    day_order = _rotate_patterns(tuple(_FOCUS_PATTERNS.get(focus, ())), variant) \
        if variant and _FOCUS_PATTERNS.get(focus) else _FOCUS_PATTERNS.get(focus, ())
    missing = tuple(p for p in day_order if p not in covered)
    rotating = _choose(pool, target - len(core), f"{user_id}-{focus}-d{day_num}-rotate-w{week}",
                       taken, families, caps=caps, per_muscle=per_muscle,
                       preferred_ids=preferred_ids, loadable_first=loadable_first,
                       pattern_counts=pattern_counts, pattern_cap=cap,
                       patterns=missing, variant=week - 1, rotate_patterns=False,
                       muscle_rank=muscle_rank,
                       headline=_headline_lifts(scheme), prefer_barbell=scheme == "strength")
    return core + rotating


# Below this the week is the same handful of exercises repeated, which the plan
# should say rather than imply. Bodyweight + endurance lands at 16.
_THIN_POOL = 20


# Warm-up and cool-down are written per focus (`_WARMUP` / `_COOLDOWN`), five or
# six movements each. Nine minutes is what they take at a sane pace, and the
# exercise budget is what is left after them.
_OVERHEAD_SECONDS = 9 * 60
# A twenty-minute session cannot spend nine of them warming up and cooling down
# — that left eleven minutes for the work, and the work then overran the clock
# by half again. Short sessions keep the first four warm-up drills and the first
# three cool-down stretches, which is about six minutes.
_SHORT_SESSION_MINUTES = 30
_SHORT_OVERHEAD_SECONDS = 6 * 60
_SHORT_WARMUP_ITEMS, _SHORT_COOLDOWN_ITEMS = 4, 3


def _overhead_seconds(duration) -> int:
    try:
        short = int(duration) <= _SHORT_SESSION_MINUTES
    except (TypeError, ValueError):
        short = False
    return _SHORT_OVERHEAD_SECONDS if short else _OVERHEAD_SECONDS
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
    budget = max(int(duration) * 60 - _overhead_seconds(duration), 300)

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

# How much of the week ends with conditioning.
#
# `cardio_preference` is a required field in the gym form — None, Light,
# Moderate, Heavy — and nothing read it, including the finisher added in the pass
# that put conditioning into fat-loss plans. Someone who ticked "None" was given
# a stair climber, which is worse than the original bug: the field was not merely
# ignored, it was contradicted.
#
# It is a share of the week's training days rather than a per-day switch, because
# that is how the decision is really made — three sessions ending on the bike is
# a different programme from six, and neither is "some cardio".
_CONDITIONING_SHARE = {"none": 0.0, "light": 1 / 3, "moderate": 2 / 3, "heavy": 1.0}
_DEFAULT_CARDIO_PREFERENCE = "moderate"
# A strength or hypertrophy block cannot absorb daily conditioning — the
# interference costs the adaptation the block exists for. Someone on those goals
# asking for heavy cardio gets the most a strength block can carry, which is not
# all of it.
_MAX_CONDITIONING_SHARE = {"strength": 1 / 3, "muscle_gain": 1 / 3}
# And how long each one runs. Someone asking for heavy cardio on the days they
# get it should get more of it, not just more days.
_MINUTE_SCALE = {"none": 0.0, "light": 0.75, "moderate": 1.0, "heavy": 1.25}


def _cardio_preference(gym_prefs) -> str:
    pref = str(gym_prefs.get("cardio_preference") or "").lower()
    return pref if pref in _CONDITIONING_SHARE else _DEFAULT_CARDIO_PREFERENCE


# Someone who needs to put mass on should not be spending the surplus on the
# bike. The cap is the same shape as the one that protects a strength block.
_UNDERWEIGHT_CONDITIONING_SHARE = 1 / 3


def _conditioning_days(training_days: int, goal: str, preference: str,
                       bmi_group: str = "normal") -> int:
    """How many of the week's training days end with conditioning."""
    share = _CONDITIONING_SHARE.get(preference, _CONDITIONING_SHARE[_DEFAULT_CARDIO_PREFERENCE])
    share = min(share, _MAX_CONDITIONING_SHARE.get(goal, 1.0))
    if bmi_group == "underweight":
        share = min(share, _UNDERWEIGHT_CONDITIONING_SHARE)
    if share <= 0:
        return 0
    return max(1, min(training_days, round(training_days * share)))


def _spread(count: int, total: int) -> set:
    """`count` indices spread evenly across `total` slots, earliest first."""
    if count <= 0 or total <= 0:
        return set()
    return {min(total - 1, round(i * total / count)) for i in range(count)}


def _finisher_prescription(ex: dict, level: str, preference: str = "moderate") -> tuple:
    own = (ex.get("sets_reps") or {}).get(level) or (ex.get("sets_reps") or {}).get("intermediate") or {}
    sets = int(own.get("sets", 1) or 1)
    reps = own.get("reps", "10 min")
    rest = int(own.get("rest_seconds", 0) or 0)
    if ex.get("rep_style") == "interval":
        # Rounds, scaled the way the steady-state minutes are.
        rounds = max(4, round(sets * _MINUTE_SCALE.get(preference, 1.0)))
        return rounds, f"{reps} hard / {rest} sec easy", 0
    cap = _FINISHER_MINUTES.get(level, 10) * _MINUTE_SCALE.get(preference, 1.0)
    if sets == 1 and _TIMED_REPS.search(str(reps)):
        return 1, f"{max(5, round(cap))} min", 0
    return sets, reps, rest


def _pick_finisher(cardio_pool, user_id, focus, day_num, week, steady=False):
    if not cardio_pool:
        return None
    pool = cardio_pool
    if steady:
        # A conditioning day's block is the steady aerobic work the week
        # otherwise lacks — 20-40 minutes a talking pace can hold. Thirty-five
        # minutes of burpee intervals is not that session.
        pool = [ex for ex in cardio_pool if ex.get("rep_style") != "interval"] or cardio_pool
    picked = _deterministic_select(pool, 1, f"{user_id}-{focus}-d{day_num}-finisher-w{week}")
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
            f"It already holds as much lifting as one session can use well — past this, "
            f"extra sets add fatigue faster than they add results. Spend the remaining time "
            f"on a longer warm-up, the cool-down stretches, or an easy walk.")


# ── Fitting a session to the clock ────────────────────────────────────────────
#
# `_session_shape` decides how many exercises the day gets; it cannot make them
# fit. Across a 400-plan sweep, 543 training days came out under three quarters
# of the length asked for and 237 over a quarter beyond it. A 20-minute request
# built 44-47 minute sessions — three main lifts at five sets each plus a
# fifteen-minute walk — and a 90-minute endurance request with "heavy" cardio
# built 55 minutes, closed by a twelve-minute treadmill walk and a note telling
# the practitioner to "add a walk". Both are things a coach adjusts without
# being asked: a short session loses sets, a long one gains them, and a long
# endurance session's extra time is cardio.
_FIT_TOLERANCE = 0.10
_CONDITIONING_DAY_EXERCISES = 4
_CONDITIONING_FLOOR_MINUTES = 5
_CONDITIONING_CEILING_MINUTES = {"heavy": 40}
_CONDITIONING_DEFAULT_CEILING = 30
_INTERVAL_ROUNDS = (4, 12)
_STEADY_MINUTES = re.compile(r"^(\d+)\s*min$")


def _steady_only(user_profile) -> bool:
    """Whether hard intervals should wait. A sedentary 96 kg beginner was
    written mountain-climber intervals in week one. ACSM's starting advice for
    a sedentary, obese, older or cardiac population is moderate continuous work
    first; intervals are a progression from a base, not the base."""
    if not user_profile:
        return False
    if str(user_profile.get("activity_level") or "").lower() == "sedentary":
        return True
    if _bmi_group(user_profile.get("bmi_category")) == "obese":
        return True
    if _age_group(user_profile.get("age")) == "senior":
        return True
    if user_profile.get("pregnancy_or_nursing"):
        return True
    # Anaemia's own note tells the practitioner to work below the plan's effort
    # and stop for breathlessness. The same plan wrote mountain climbers "too
    # breathless to talk" two lines further down.
    if any(g["key"] == "anemia" for g in guidance_for(_conditions_and_injuries(user_profile))):
        return True
    reason = _intensity_ceiling(user_profile)
    return bool(reason) and "heart" in reason


def _trim_notice(fit: dict, ordered, duration) -> str | None:
    """Say so when the clock took sets off a main lift. The week's header
    announces the main-lift prescription, and a 20-minute day that quietly ran
    them at two sets read as a contradiction of it."""
    trimmed = [i for i, (_, role) in enumerate(ordered)
               if role == "primary" and fit["set_delta"][i] < 0 and fit["keep"][i]]
    if not trimmed:
        return None
    cut = -min(fit["set_delta"][i] for i in trimmed)
    return (f"To fit {duration} minutes, the main lifts today are {cut} set"
            f"{'s' if cut > 1 else ''} short of the week's prescription. Given more time, "
            "do the full number.")


def _stretches_conditioning(goal: str, preference: str) -> bool:
    """Whether a session's spare time goes to conditioning rather than to sets."""
    if preference == "none":
        return False
    return (goal in _FINISHER_GOALS or preference == "heavy"
            or (goal == "general_fitness" and preference == "moderate"))


def _fit_to_clock(ordered, rx, budget_seconds, stretch_conditioning=False,
                  preference="moderate"):
    """Adjust a session so it runs close to the time it was asked for.

    `ordered` is [(exercise, role)], `rx` the matching [(sets, reps, rest)].
    Returns per-index set deltas, which exercises to keep, and any rewritten
    conditioning prescription. Over the clock: conditioning shrinks first, then
    sets come off accessories before main lifts, then accessories go. Under it:
    conditioning grows when that is the goal, then each lift gains at most one
    set — a longer session is not licence to double the volume.
    """
    n = len(ordered)
    delta = [0] * n
    keep = [True] * n
    cond_reps: dict = {}
    cond_sets: dict = {}

    def _cost(i):
        sets, reps, rest = rx[i]
        if ordered[i][1] == "conditioning":
            sets = cond_sets.get(i, sets)
            reps = cond_reps.get(i, reps)
        elif sets >= _MIN_SETS:
            sets = max(_MIN_SETS, sets + delta[i])
        return _reps_to_seconds(reps, sets) + sets * rest

    def _total():
        return sum(_cost(i) for i in range(n) if keep[i])

    lo = budget_seconds * (1 - _FIT_TOLERANCE)
    hi = budget_seconds * (1 + _FIT_TOLERANCE)
    conditioning = [i for i in range(n) if ordered[i][1] == "conditioning"]

    def _resize_conditioning(target_extra_seconds, ceiling_minutes):
        for i in conditioning:
            sets, reps, _ = rx[i]
            if ordered[i][0].get("rep_style") == "interval":
                per_round = _reps_to_seconds(reps, 1) or 60
                lo_r, hi_r = _INTERVAL_ROUNDS
                rounds = cond_sets.get(i, sets) + int(target_extra_seconds / per_round)
                cond_sets[i] = max(lo_r, min(hi_r, rounds))
            else:
                m = _STEADY_MINUTES.match(str(cond_reps.get(i, reps)).strip())
                if not m or sets != 1:
                    continue
                minutes = int(m.group(1)) + int(target_extra_seconds / 60)
                minutes = max(_CONDITIONING_FLOOR_MINUTES, min(ceiling_minutes, minutes))
                cond_reps[i] = f"{minutes} min"

    total = _total()
    if total > hi:
        _resize_conditioning(budget_seconds - total, _CONDITIONING_DEFAULT_CEILING)
        for role in ("accessory", "secondary", "primary"):
            changed = True
            while _total() > hi and changed:
                changed = False
                for i in reversed(range(n)):
                    if _total() <= hi:
                        break
                    if (keep[i] and ordered[i][1] == role and rx[i][0] >= _MIN_SETS
                            and rx[i][0] + delta[i] > _MIN_SETS):
                        delta[i] -= 1
                        changed = True
        lifts = [i for i in range(n) if keep[i] and ordered[i][1] != "conditioning"]
        for i in reversed(lifts):
            if _total() <= hi or sum(1 for j in lifts if keep[j]) <= _MIN_EXERCISES:
                break
            if ordered[i][1] == "accessory":
                keep[i] = False
    elif total < lo:
        if stretch_conditioning and conditioning:
            _resize_conditioning(budget_seconds - total,
                                 _CONDITIONING_CEILING_MINUTES.get(
                                     preference, _CONDITIONING_DEFAULT_CEILING))
        ceiling = {"secondary": _SECONDARY_MAX_SETS, "accessory": _ACCESSORY_MAX_SETS}
        # Support work takes the extra sets. The main lift stays at the
        # prescription the week's header announces and the progression is
        # written against.
        for role in ("secondary", "accessory"):
            for i in range(n):
                if _total() >= lo:
                    break
                sets = rx[i][0]
                if (ordered[i][1] == role and sets >= _MIN_SETS
                        and sets + 1 <= max(sets, ceiling[role])):
                    delta[i] = 1
    return {"set_delta": delta, "keep": keep,
            "conditioning_reps": cond_reps, "conditioning_sets": cond_sets}


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
    # The curated library states how a movement is measured. Sniffing the reps
    # string for "min"/"sec" caught holds and cardio but not carries, so a
    # farmer's walk was prescribed as "5 sets of 8-10" — of what, it did not say.
    if ex.get("rep_style") in ("time", "distance", "isometric", "interval"):
        return int(own.get("sets", 1)), own.get("reps"), int(own.get("rest_seconds", 60))
    if own and _TIME_UNITS.search(str(own.get("reps", ""))):
        return int(own.get("sets", 1)), own.get("reps"), int(own.get("rest_seconds", 60))
    r = _role_prescription(rx, role)
    # Trunk work is trained for control, not for a heavy single effort. A strength
    # block wrote "Glute Bridge March 5 x 5-7, 135 s rest" and "Standing Cable Wood
    # Chop 5 x 5-7" — a stability drill given a powerlifting prescription.
    if ex.get("bucket") == "core":
        parsed = _parse_reps(r["reps"])
        if parsed and parsed[1] < _CORE_MIN_REPS[1]:
            return r["sets"], f"{_CORE_MIN_REPS[0]}-{_CORE_MIN_REPS[1]}", min(
                r["rest_seconds"], _CORE_MAX_REST)
    return r["sets"], r["reps"], r["rest_seconds"]


_CORE_MIN_REPS = (8, 12)
_CORE_MAX_REST = 60


def _load_reps(ex: dict, rx_week1: dict, level: str, role: str):
    """The rep count a lift's load is priced at: its role's reps in WEEK ONE.

    The block's weekly notes are written against the first week's weight — "same
    weight as W1, push for extra reps", "reduce weight 15%" — and
    `_week_load_factor` carries them. Pricing each week at its own reps as well
    would move the number twice, and in the wrong direction: a volume week's
    extra reps would lower the quoted load beneath a note saying to hold it."""
    if role == "conditioning":
        return None
    return _prescribe(ex, rx_week1, level, role)[1]


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
    if focus == "core_cardio" and any(e.get("category") == "cardio" for e in main_workout):
        # The aerobic block is most of the session; "Core Cardio" read as a
        # kind of core work.
        return "Conditioning & Core"
    label = focus.replace("_", " ").title()
    if "cardio" in focus.lower() and not any(e.get("category") == "cardio" for e in main_workout):
        stripped = " ".join(w for w in label.split() if w.lower() != "cardio").strip()
        return stripped or "Conditioning"
    return label


def build_day_plan(day_num, day_name, focus, muscle_split, gym_prefs, user_profile,
                   week=1, user_id="default", strength_level="beginner", gender="male",
                   dosha="vata", bodyweight=None, with_finisher=False,
                   conditioning_pool=(), preferred_ids=(), variant=0,
                   loadable_first=False, extra_avoid_tags=()):
    if focus == "rest":
        recovery = dict(_REST_DAY_RECOVERY.get(dosha, _REST_DAY_RECOVERY["vata"]))
        recovery["activities"] = _gate_practices(
            recovery["activities"],
            set(user_profile.get("medical_history") or [])
            | set(user_profile.get("injuries_or_limitations") or []),
            bool(user_profile.get("pregnancy_or_nursing")),
            _avoided_risks(user_profile, extra_avoid_tags))
        recovery["nutrition_note"] = _screen_food_line(recovery.get("nutrition_note"),
                                                       user_profile)
        return {
            "day": day_num, "day_name": day_name,
            "focus": "Rest & Recovery", "type": "recovery",
            "warmup": [], "main_workout": [], "cooldown": [],
            "estimated_duration_minutes": 0, "calories_burned_estimate": 0,
            "rest_day_recovery": recovery,
        }

    duration = gym_prefs.get("workout_duration_minutes", 45)
    goal = gym_prefs.get("gym_goal", "general_fitness")
    # The goal picks the exercises and the split; the style writes the sets.
    scheme = _resolve_scheme(goal, gym_prefs.get("training_style"), user_profile)
    level = user_profile.get("fitness_level", "beginner") or "beginner"
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"
    activity = user_profile.get("activity_level")

    rx = _get_goal_prescription(scheme, week, level, activity)
    # The COUNT comes off week 1 and holds for the block, while the sets and reps
    # move with the periodisation. Sizing each week against its own prescription
    # made peak weeks (four sets instead of three) drop an exercise, which
    # changed the day's core and cost the very continuity the stable core exists
    # to give. A real programme keeps the lifts and moves the volume.
    rx_week1 = _get_goal_prescription(scheme, 1, level, activity)
    # Past sixty the session carries a balance block, and it comes out of the
    # time the practitioner gave rather than being added on top of it.
    is_senior = _age_group(user_profile.get("age")) == "senior"
    balance_seconds = _BALANCE_SECONDS if is_senior else 0
    target, primary_slots = _session_shape(
        max(duration - balance_seconds // 60, 20), scheme, rx_week1)

    # The finisher takes a slot rather than being added on top of a session that
    # already fills the clock — the practitioner asked for forty-five minutes.
    finisher = None
    # The conditioning day is named for its conditioning. It used to receive a
    # finisher only when the week's cardio share happened to land on it, so for
    # the strength and muscle-gain goals — capped at a third of the week — it
    # came out as forty-five minutes of planks and crunches under the label
    # "Core". It always carries the aerobic block unless cardio was declined,
    # and the trunk work is the part of it that is short.
    is_conditioning_day = focus == "core_cardio"
    if is_conditioning_day:
        target = min(target, _CONDITIONING_DAY_EXERCISES)
    if with_finisher or (is_conditioning_day and _cardio_preference(gym_prefs) != "none"):
        finisher = _pick_finisher(conditioning_pool or [],
                                  user_id, focus, day_num, week,
                                  steady=is_conditioning_day or _steady_only(user_profile))
        if finisher:
            target = max(_MIN_EXERCISES, target - 1)

    # The session's edges take the same restrictions its middle does. `avoid_tags`
    # is rebuilt here rather than passed down, because `build_day_plan` is called
    # directly by tests and by the holistic path, and a warm-up that is only safe
    # when the caller remembers to say so is not safe.
    edge_avoid = set(user_profile.get("injuries_or_limitations") or [])
    edge_avoid |= _condition_contra_tags(user_profile.get("medical_history") or [])
    # The rare-condition classifier's tags reached the exercise pool and not the
    # warm-up beside it.
    edge_avoid |= {str(t).lower() for t in extra_avoid_tags or ()}
    edge_age = _age_group(user_profile.get("age"))
    if edge_age in ("senior", "youth"):
        edge_avoid |= _AGE_AVOID_TAGS
    withhold_impact = _withholds_impact(user_profile)
    edge_risks = _avoided_risks(user_profile, extra_avoid_tags)
    is_pregnant = bool(user_profile.get("pregnancy_or_nursing"))

    pool = []
    for k in _focus_to_keys(focus):
        pool.extend(muscle_split.get(k, []))

    if len(pool) < 3:
        pool = muscle_split.get("full_body", [])
    if len(pool) < 3:
        pool = [ex for group in muscle_split.values() for ex in group]

    selected = _select_for_day(pool, target, user_id, focus, day_num, week, preferred_ids,
                               variant=variant, loadable_first=loadable_first, scheme=scheme)

    # A session is performed in an order, and the order is the programme: the
    # heaviest compound while the practitioner is fresh, its support after it,
    # isolation last, conditioning last of all. Selection optimises for coverage
    # — which movement patterns the day contains — and returned them in whatever
    # order it found them, so a chest day opened with a push-up and then ran
    # three triceps extensions before it reached a fly.
    # The same number of main lifts the session was costed with. Deciding it again
    # from the length that came out let the day be built to a shape it was not
    # priced for.
    roles = _assign_roles(selected, primary_slots, scheme)
    ordered = sorted(zip(selected, roles), key=lambda pair: _ROLE_ORDER.index(pair[1]))
    if finisher and all(ex["id"] != finisher["id"] for ex in selected):
        ordered.append((finisher, "conditioning"))

    overhead = _overhead_seconds(duration)
    short_session = overhead < _OVERHEAD_SECONDS

    def _rx_for(week_rx):
        return [(_finisher_prescription(ex, level, _cardio_preference(gym_prefs))
                 if ex is finisher else _prescribe(ex, week_rx, level, role))
                for ex, role in ordered]

    # The session is fitted to the clock on week one, and the same adjustment is
    # carried to every week, so the block's own periodisation — more sets in the
    # peak week, fewer in the deload — survives the fitting.
    fit = _fit_to_clock(
        ordered, _rx_for(rx_week1),
        duration * 60 - overhead - balance_seconds,
        stretch_conditioning=(is_conditioning_day
                              or _stretches_conditioning(goal, _cardio_preference(gym_prefs))),
        preference=_cardio_preference(gym_prefs))
    prescriptions = []
    for i, ((ex, role), (sets, reps, rest)) in enumerate(zip(ordered, _rx_for(rx))):
        if not fit["keep"][i]:
            continue
        if role == "conditioning":
            reps = fit["conditioning_reps"].get(i, reps)
            sets = fit["conditioning_sets"].get(i, sets)
        elif sets >= _MIN_SETS:
            sets = min(_MAX_SETS, max(_MIN_SETS, sets + fit["set_delta"][i]))
        prescriptions.append(((ex, role), (sets, reps, rest)))

    main_workout = []
    total_cals = 0.0
    work_seconds = 0
    rest_seconds_total = 0
    for (ex, role), (sets, reps, rest) in prescriptions:

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
            "weight_range": _get_weight_range(ex, strength_level, gender, bodyweight,
                                              _week_load_factor(scheme, week),
                                              reps=_load_reps(ex, rx_week1, level, role),
                                              age=user_profile.get("age"),
                                              calibration=gym_prefs.get("_load_calibration")),
            "week_note": rx.get("note", ""),
            "notes": _modification_for(ex),
            # The one sentence a coach would say about the movement. It is the
            # difference between a list of exercises and a session someone wrote
            # for you, and the library carries it for every movement.
            "coaching_cue": ex.get("coaching_cue"),
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
        "warmup": _warmup_for(focus, edge_avoid, withhold_impact, is_pregnant,
                              edge_risks)[:_SHORT_WARMUP_ITEMS if short_session else None],
        "main_workout": main_workout,
        "cooldown": _cooldown_for(focus, edge_avoid, withhold_impact, is_pregnant,
                                  edge_risks)[:_SHORT_COOLDOWN_ITEMS if short_session else None],
        "balance": (_balance_for(day_num, edge_avoid, withhold_impact, is_pregnant,
                                 edge_risks) if is_senior else []),
        # What was BUILT, not what was asked for. The client shows this as the
        # session-length chip, and it used to echo the preference straight back —
        # so a 60-minute heading sat above 26 minutes of work. Same lesson the
        # yoga engine learned: the number on the card and the session underneath
        # it were different products.
        "estimated_duration_minutes": round((work_seconds + rest_seconds_total
                                             + overhead + balance_seconds) / 60),
        "requested_duration_minutes": duration,
        "duration_notice": _trim_notice(fit, ordered, duration) or _duration_notice(
            round((work_seconds + rest_seconds_total + overhead + balance_seconds) / 60),
            duration, scheme),
        "calories_burned_estimate": int(total_cals + (overhead / 60.0)
                                        * _WARMUP_KCAL_PER_MINUTE),
    }


# ── Ayurvedic tips ────────────────────────────────────────────────────────────

# What a food line becomes when it names something this person should not be
# eating. The dosha notes are generic by construction, and the diet plan is the
# place that has chosen foods for their health details.
_FOOD_LINE_SUBSTITUTE = ("Eat as your diet plan sets out — it has chosen foods for "
                         "your health details, which this general note does not know.")


def _screen_food_line(text: str, user_profile: dict) -> str:
    """Hold a line of food advice to the diet path's floor.

    The rest-day nutrition note and the pre/post-workout tips are written per
    dosha and shown to everyone of that dosha: "Ghee, warm milk" to a Vata
    practitioner with a dairy allergy, "coconut water" to a Pitta one with
    kidney disease, "ginger-lemon tea" to a Kapha one with acid reflux. They
    passed no screen — the same shape as the Kapalabhati that reached a
    hypertensive through the tips. The screen is `apply_advisory_safety`, the
    one the diet plan's own Pathya card goes through, so the two features cannot
    disagree about what a person may eat."""
    if not text or not user_profile:
        return text
    history = user_profile.get("medical_history") or []
    allergies = user_profile.get("allergies") or []
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))
    if not history and not allergies and not pregnant:
        return text
    from services.ahara_safety import apply_advisory_safety
    card = apply_advisory_safety({"pathya_apathya": {"pathya": [text]}},
                                 list(history) if not isinstance(history, str) else [history],
                                 allergies=allergies, pregnant=pregnant)
    if not card.get("advisory_safety_checked") or card.get("withheld_recommendations"):
        return _FOOD_LINE_SUBSTITUTE
    return text


def _screen_tips(tips: dict, user_profile: dict) -> dict:
    return {k: (_screen_food_line(v, user_profile) if k in ("pre_workout", "post_workout") else v)
            for k, v in tips.items()}


def get_ayurvedic_tips(dosha, conditions=(), is_pregnant=False):
    """The Kapha tip prescribed Kapalabhati by name, to everybody. Same gate as
    the rest day — the practice does not become safe because it is offered as a
    tip rather than as an activity."""
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
            "post_workout": _gate_practices(
                ["Stimulating pranayama (Kapalabhati), light protein meal"],
                conditions, is_pregnant)[0],
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
    # Ardhabala is a SESSION dose, not a set dose. This card used to say "stop
    # at the first forehead sweat", beside sets whose own note says the last two
    # reps must be hard — and in a gym session the forehead sweats during the
    # warm-up, so the two could not both be followed. The classical sign (sweat
    # on forehead, nose and joints TOGETHER with mouth-breathing) marks the point
    # the session has reached its dose; the plan's volume is set to arrive there
    # near its end, and arriving early is the reason to cut it short.
    if age_i >= 60 or dosha == "vata" or strength_level in ("untrained", "beginner"):
        capacity = ("Keep well inside Ardhabala. Each set should end with two reps still in "
                    "you, and the session as a whole should leave you with energy to spare. "
                    "If the classical sign — sweat on the forehead, nose and joints together "
                    "with breathing through the mouth — arrives before the session's end, "
                    "stop there and skip what is left. Vata constitution, a beginner's "
                    "strength and older age all lower exercise tolerance, and over-exertion "
                    "here depletes Ojas directly.")
    elif dosha == "kapha" and strength_level in ("intermediate", "advanced") and age_i < 50:
        capacity = ("You have higher Vyayama Shakti — you can work up toward the Ardhabala "
                    "ceiling with good sustained volume, and Kapha benefits from training until "
                    "a genuine sweat breaks. Still stop the session if you are breathing through "
                    "the mouth and cannot slow it down between sets.")
    else:
        capacity = ("Moderate capacity — the sets are hard near their end, the session stops "
                    "well short of exhaustion. Pitta types should avoid training in heat or with "
                    "a competitive mindset, which pushes past Ardhabala into Pitta aggravation.")
    return {
        "principle": ("Exercise should be performed only to Ardhabala — half of one's maximum "
                      "capacity (Charaka Sutrasthana 7). It describes the whole session, not a "
                      "single set: the classical signal that the dose has been reached is sweat "
                      "on the forehead, nose and joints together with the onset of "
                      "mouth-breathing."),
        "your_capacity": capacity,
        "signs_adequate": "Sweat on forehead, nose and armpits; lightness in the body; comfortably increased breathing.",
        "signs_overexertion": ("Breathlessness, dizziness, tremor, excessive thirst, joint pain or cough mark "
                               "Ativyayama (over-exercise) — reduce intensity immediately."),
        "bala_note": ("Exercise capacity (Bala) here is estimated from fitness level and age as a practical proxy — "
                      "not a full classical Bala Pareeksha, which also weighs Sara, Samhanana, Satmya, Sattva, and season."),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

# ── Inputs ────────────────────────────────────────────────────────────────────
#
# Both plan paths read the preferences back from Mongo, not from the validated
# request, so what arrives is whatever was stored — including documents written
# before a field existed or by an older form. A 1,500-case fuzz of plausible
# stored shapes found eight crashes: a duration saved as null (`.get(k, 45)`
# returns None when the key is present), days saved as the string "4",
# `exercise_preferences` saved as a string, an age of "abc". Each is a user who
# cannot regenerate their plan. They are coerced here, once, rather than
# defended against at each of the dozens of places that read them.
_GOALS = {"fat_loss", "muscle_gain", "endurance", "strength", "general_fitness"}
_GOAL_ALIASES = {"weight_loss": "fat_loss", "lose_weight": "fat_loss", "toning": "fat_loss",
                 "bulk": "muscle_gain", "hypertrophy": "muscle_gain", "fitness": "general_fitness"}
_LEVELS = {"beginner", "intermediate", "advanced"}
_STRENGTH_LEVELS = {"untrained", "beginner", "intermediate", "advanced"}
_FOCUSES = {"full_body", "upper", "lower", "core", "back"}
_STYLES = {"strength", "hypertrophy", "endurance", "circuit"}


def _as_int(value, default, lo, hi):
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _as_list_of_str(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    try:
        return [str(v) for v in value if v not in (None, "")]
    except TypeError:
        return []


def _normalise_inputs(user_profile, gym_prefs) -> tuple:
    profile = dict(user_profile or {})
    prefs = dict(gym_prefs or {})

    level = str(profile.get("fitness_level") or "").strip().lower()
    profile["fitness_level"] = level if level in _LEVELS else "beginner"
    try:
        age = int(float(profile.get("age")))
        profile["age"] = age if 5 <= age <= 120 else None
    except (TypeError, ValueError):
        profile["age"] = None
    gender = profile.get("gender")
    profile["gender"] = str(gender).strip().lower() if isinstance(gender, str) and gender.strip() else None
    dosha = str(profile.get("dominant_dosha") or "").strip().lower()
    dosha = re.split(r"[^a-z]", dosha)[0] if dosha else ""
    profile["dominant_dosha"] = dosha if dosha in ("vata", "pitta", "kapha") else "vata"
    for key in ("medical_history", "allergies", "injuries_or_limitations"):
        profile[key] = _as_list_of_str(profile.get(key))
    pregnant = profile.get("pregnancy_or_nursing")
    profile["pregnancy_or_nursing"] = (pregnant is True or str(pregnant).strip().lower()
                                       in ("true", "yes", "1"))
    if isinstance(profile.get("bmi_category"), str):
        profile["bmi_category"] = profile["bmi_category"].strip().lower()

    goal = str(prefs.get("gym_goal") or "").strip().lower()
    goal = _GOAL_ALIASES.get(goal, goal)
    prefs["gym_goal"] = goal if goal in _GOALS else "general_fitness"
    prefs["workout_days_per_week"] = _as_int(prefs.get("workout_days_per_week"), 4, 2, 7)
    prefs["workout_duration_minutes"] = _as_int(prefs.get("workout_duration_minutes"), 45, 20, 90)
    prefs["available_equipment"] = _as_list_of_str(prefs.get("available_equipment")) or ["bodyweight"]
    strength = str(prefs.get("strength_level") or "").strip().lower()
    prefs["strength_level"] = (strength if strength in _STRENGTH_LEVELS
                               else profile["fitness_level"])
    cardio = str(prefs.get("cardio_preference") or "").strip().lower()
    prefs["cardio_preference"] = cardio if cardio in _CONDITIONING_SHARE else _DEFAULT_CARDIO_PREFERENCE
    focus = str(prefs.get("target_muscle_focus") or "").strip().lower()
    prefs["target_muscle_focus"] = focus if focus in _FOCUSES else "full_body"
    style = str(prefs.get("training_style") or "").strip().lower()
    prefs["training_style"] = style if style in _STYLES else None
    prefs["injuries"] = _as_list_of_str(prefs.get("injuries"))
    known = prefs.get("known_lifts")
    prefs["known_lifts"] = known if isinstance(known, dict) else None
    detail = prefs.get("injury_detail")
    prefs["injury_detail"] = detail if isinstance(detail, str) else None
    liked = prefs.get("exercise_preferences")
    if not isinstance(liked, dict):
        liked = {}
    # A typed string is kept whole: `_preference_terms` splits "swimming, cycling"
    # itself, and wrapping it in a list first would make it one term.
    prefs["exercise_preferences"] = {
        k: (liked.get(k) if isinstance(liked.get(k), str) else _as_list_of_str(liked.get(k)))
        for k in ("likes", "dislikes")}
    return profile, prefs


def _next_block(previous_block) -> int:
    """A block the practitioner mostly did is built on; one they mostly did not
    is repeated, and keeps its number."""
    if not previous_block:
        return 1
    n = int(previous_block.get("block") or 1)
    return n + 1 if previous_block.get("progress") else n


def _block_notice(previous_block, logged_lifts) -> str | None:
    """What this block was built from. Without it, a plan that read the log and
    one that did not look identical."""
    measured = len(logged_lifts or {})
    if not previous_block:
        if measured:
            return (f"Loads for {measured} exercise{'s' if measured != 1 else ''} come from "
                    "sets you logged recently.")
        return None
    done, planned = previous_block.get("sessions_logged", 0), previous_block.get("sessions_planned", 0)
    if previous_block.get("progress"):
        lead = (f"Block {_next_block(previous_block)}. You logged {done} of {planned} sessions "
                "last block, so this one builds on it")
    else:
        lead = (f"You logged {done} of {planned} sessions last block, so this one repeats its "
                "structure rather than adding to it — finish more of it and the next block "
                "will build")
    loads = (f"; loads for {measured} exercise{'s' if measured != 1 else ''} come from your "
             "logged sets" if measured else "")
    moved = previous_block.get("progressed") or []
    gains = ("" if not moved else " Biggest gains: " + ", ".join(
        f"{m['exercise']} +{m['change_percent']}%" for m in moved[:3]) + ".")
    return f"{lead}{loads}.{gains}"


def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None, extra_avoid_tags=None,
                      logged_lifts=None, previous_block=None):
    """`logged_lifts` is {exercise_id: {one_rm, source}} from the practitioner's
    own logged sets (`services.workout_log.logged_lifts`); `previous_block` is the
    block they are continuing from, if any."""
    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    user_profile, gym_prefs = _normalise_inputs(user_profile, gym_prefs)
    _gender = user_profile.get("gender") or "unspecified"
    gym_prefs["_load_calibration"] = _load_calibration(
        gym_prefs.get("known_lifts"), logged_lifts,
        strength_level=gym_prefs["strength_level"], gender=_gender,
        bodyweight=_bodyweight_of(user_profile, "female" if _gender == "female" else "male"),
        age=user_profile.get("age"))
    # Every gate below reads `injuries_or_limitations`, so it is resolved once
    # here — the profile's list, the form's ticks and the typed detail, in the
    # library's own tokens — rather than taught to each of them.
    injuries, unmatched_injuries = _resolve_injuries(user_profile, gym_prefs)
    user_profile = {**user_profile, "injuries_or_limitations": injuries}
    preference_report: dict = {}
    filtered = filter_exercises(user_profile, gym_prefs, ge, extra_avoid_tags=extra_avoid_tags,
                                preference_report=preference_report)
    # A barbell lift whose working load is lighter than the empty bar cannot be
    # performed as written. A 14-year-old was given a 13-18 kg bench press and an
    # 11-year-old a 6-8 kg one; the bar alone is 20. Where the practitioner has
    # dumbbells or a machine to train the same pattern with, the bar waits until
    # they have outgrown it. Where the bar is all they have, it stays, and the
    # load text says so.
    available_eq = _normalise_equipment(gym_prefs.get("available_equipment"))
    if available_eq & {"dumbbell", "machine", "kettlebell", "cable"}:
        # Priced at the support tier's reps: a barbell lift is as often the
        # second press of a day as its first, and at 6-8 a 50 kg woman's squat
        # came out at 17 kg under a 20 kg bar.
        # And at the deload week's load, which is the lightest the block asks
        # for — a deadlift that clears the bar in week one and drops under it in
        # week four is the same defect three weeks later.
        bar_scheme = _resolve_scheme(gym_prefs.get("gym_goal", "general_fitness"),
                                     gym_prefs.get("training_style"), user_profile)
        heaviest_reps = _get_goal_prescription(
            bar_scheme, 1, user_profile.get("fitness_level") or "beginner",
            user_profile.get("activity_level"))["reps"]
        heaviest_reps = _TIER_REPS.get(heaviest_reps, (heaviest_reps,))[0]
        gender_of = user_profile.get("gender") or "unspecified"
        load_kw = dict(
            strength_level=gym_prefs.get("strength_level",
                                         user_profile.get("fitness_level") or "beginner"),
            gender=gender_of,
            bodyweight=_bodyweight_of(user_profile, "female" if str(gender_of).lower()
                                      in ("female", "f", "woman") else "male"),
            reps=heaviest_reps, age=user_profile.get("age"),
            week_factor=min(_WEEK_LOAD_FACTOR.get(bar_scheme, (1.0,))),
            calibration=gym_prefs.get("_load_calibration"))
        filtered = [ex for ex in filtered if not _below_the_bar(ex, **load_kw)]
    muscle_split = split_by_muscle_group(filtered)
    # Conditioning reaches a session through the finisher and nowhere else, so
    # `cardio_preference` is the only thing that decides how much of it there is.
    # It used to also arrive through the `core_cardio` day's own pool, which meant
    # someone who ticked "None" still got a stair climber on Saturday — the field
    # was not merely ignored, it was contradicted.
    conditioning_pool = muscle_split.pop("cardio", [])
    muscle_split["cardio"] = []

    likes = _preference_terms((gym_prefs.get("exercise_preferences") or {}).get("likes"))
    preferred_ids = {ex["id"] for ex in filtered if _matches_preference(ex, likes)}
    # A lift the practitioner logged comes back in the next block. Progressive
    # overload needs the same movement, and its load is now a measurement.
    preferred_ids |= {ex["id"] for ex in filtered if ex["id"] in (logged_lifts or {})}

    workout_days = gym_prefs.get("workout_days_per_week", 4)
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}
    fitness_level = user_profile.get("fitness_level", "beginner") or "beginner"
    strength_level = gym_prefs.get("strength_level", fitness_level)
    gender = user_profile.get("gender") or "unspecified"
    bodyweight = _bodyweight_of(
        user_profile, "female" if str(gender).lower() in ("female", "f", "woman") else "male")

    muscle_focus = gym_prefs.get("target_muscle_focus") or "full_body"
    requested_days = workout_days
    is_youth = _age_group(user_profile.get("age")) == "youth"
    split_level = fitness_level
    if is_youth:
        workout_days = min(workout_days, _youth_day_cap(user_profile.get("age"), fitness_level))
        # Whole-body sessions on alternate days is the youth structure whatever
        # the training age; a split is for a fourth day, which only a trained
        # older teenager is given.
        if workout_days <= _YOUTH_MAX_DAYS:
            split_level = "beginner"
    schedule_focus = _build_weekly_schedule(
        workout_days, is_bodyweight_only, split_level, muscle_focus,
        goal=gym_prefs.get("gym_goal"))
    # The split is chosen before the library is consulted, so it can name days the
    # practitioner's own safety gating has emptied.
    schedule_focus, substitutions = _resolve_untrainable_days(schedule_focus, muscle_split)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    goal = gym_prefs.get("gym_goal", "general_fitness")
    scheme = _resolve_scheme(goal, gym_prefs.get("training_style"), user_profile)

    # Which days end with conditioning, decided once for the week rather than per
    # day, so "light" means two days out of six and not a coin flip six times.
    cardio_preference = _cardio_preference(gym_prefs)
    training_days = [i for i, focus in enumerate(schedule_focus) if focus != "rest"]
    bmi_group = _bmi_group(user_profile.get("bmi_category"))
    finisher_count = _conditioning_days(len(training_days), goal, cardio_preference, bmi_group)
    # A conditioning day carries its own aerobic block (see `build_day_plan`), so
    # it counts toward the share rather than on top of it: a strength block
    # asking for light cardio was conditioning four days in six.
    conditioning_days = [i for i in training_days if schedule_focus[i] == "core_cardio"]
    if cardio_preference == "none":
        conditioning_days = []
    lifting_days = [i for i in training_days if i not in conditioning_days]
    finisher_count = max(0, finisher_count - len(conditioning_days))
    finisher_days = {lifting_days[i] for i in _spread(finisher_count, len(lifting_days))}

    # How many earlier days this week already trained the same region. The second
    # leg day of a lower-body block should not be the first one again.
    emphasis_seen: dict = collections.Counter()
    day_variant = []
    for focus in schedule_focus:
        headline = _focus_headline(focus)
        day_variant.append(emphasis_seen[headline])
        if focus != "rest":
            emphasis_seen[headline] += 1

    four_week_plan = []
    for week in range(1, 5):
        week_days = [
            build_day_plan(
                i + 1, days_of_week[i], focus, muscle_split, gym_prefs, user_profile,
                week=week, user_id=user_id, strength_level=strength_level,
                gender=gender, dosha=dominant_dosha, bodyweight=bodyweight,
                with_finisher=i in finisher_days, conditioning_pool=conditioning_pool,
                preferred_ids=preferred_ids, variant=day_variant[i],
                loadable_first=not is_bodyweight_only,
                extra_avoid_tags=extra_avoid_tags or (),
            )
            for i, focus in enumerate(schedule_focus)
        ]
        # The header used the intermediate prescription whoever was reading it, so
        # two thirds of plans announced a set count no exercise underneath them
        # used — a beginner was told three sets above a page of twos. It is now
        # the practitioner's own, and it names what it describes: the main lift.
        # The supporting roles are published alongside it rather than left for the
        # reader to infer from the exercise rows.
        base_rx = _get_goal_prescription(scheme, week, fitness_level,
                                         user_profile.get("activity_level"))
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
            "pregnancy at your level, so this plan repeats some of them across the week. "
            "It is not a prenatal training programme — for that, work with a "
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
            "training_style": gym_prefs.get("training_style") or _GOAL_SCHEME.get(goal),
            "set_scheme": scheme,
            "workout_days": workout_days,
            "requested_workout_days": requested_days,
            "duration_per_session": gym_prefs.get("workout_duration_minutes", 45),
            # Resolved from the profile and the gym form together, so the
            # coaching written around the plan knows what the gates knew.
            "injuries": injuries,
            "block": _next_block(previous_block),
        },
        "weekly_schedule": four_week_plan[0]["days"],
        "four_week_plan": four_week_plan,
        "ayurvedic_tips": _screen_tips(get_ayurvedic_tips(
            dominant_dosha,
            set(user_profile.get("medical_history") or [])
            | set(user_profile.get("injuries_or_limitations") or []),
            is_pregnant), user_profile),
        "vyayama_shakti": _vyayama_shakti(dominant_dosha, user_profile.get("age"), strength_level),
        # The block's progression, as facts. The four weeks each carry a theme, a
        # prescription and the rule that moves it, and the main lifts they are
        # about — which is everything a coaching note needs to be true rather than
        # plausible. The enricher attaches `coach_note` to each entry; the numbers
        # here are the engine's and are never overwritten by it.
        "progression": _progression_spine(four_week_plan, scheme),
        # Kept because the plan card renders it, and because it is the progression
        # in one line per week for anything that only wants that.
        "progressive_overload_guide": {
            "week_1": _GOAL_WEEKS[scheme][0]["note"] if scheme in _GOAL_WEEKS else "",
            "week_2": _GOAL_WEEKS[scheme][1]["note"] if scheme in _GOAL_WEEKS else "",
            "week_3": _GOAL_WEEKS[scheme][2]["note"] if scheme in _GOAL_WEEKS else "",
            "week_4": _GOAL_WEEKS[scheme][3]["note"] if scheme in _GOAL_WEEKS else "",
        },
        "disclaimer": disclaimer,
        "pool_notice": pool_notice,
        "schedule_notice": _schedule_notice(workout_days, schedule_focus),
        "age_notice": (_youth_notice(requested_days,
                                     sum(1 for f in schedule_focus if f != "rest"))
                       if is_youth else None),
        "focus_notice": _focus_notice(muscle_focus, workout_days, is_bodyweight_only,
                                      fitness_level),
        "cardio_notice": _cardio_notice(goal, cardio_preference, finisher_count,
                                        len(training_days)),
        "preference_notice": _preference_notice(preference_report),
        "adaptation_notice": _adaptation_notice(bmi_group, user_profile.get("activity_level")),
        "substitution_notice": _substitution_notice(substitutions),
        "injury_notice": _injury_notice(unmatched_injuries),
        "intensity_notice": _intensity_notice(goal, gym_prefs.get("training_style"),
                                              user_profile),
        "block_notice": _block_notice(previous_block, logged_lifts),
        "previous_block": previous_block,
        # What a practitioner with a condition needs to know before the session,
        # where no movement is the problem — hypoglycaemia, an asthma attack, a
        # seizure. See `services/gym_condition_guidance.py`.
        "condition_guidance": guidance_for(
            _conditions_and_injuries(user_profile)
            + (["pregnancy"] if user_profile.get("pregnancy_or_nursing") else [])),
    }
