import json
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSES_PATH = BASE_DIR / "data" / "knowledge_base" / "yoga_poses.json"
PRANAYAMA_PATH = BASE_DIR / "data" / "knowledge_base" / "pranayama.json"
PROTOCOLS_PATH = BASE_DIR / "data" / "knowledge_base" / "condition_protocols.json"

yoga_poses = []
if POSES_PATH.exists():
    with open(POSES_PATH, "r", encoding="utf-8") as f:
        yoga_poses = json.load(f)

pranayama_list = []
if PRANAYAMA_PATH.exists():
    with open(PRANAYAMA_PATH, "r", encoding="utf-8") as f:
        pranayama_list = json.load(f)

_condition_protocols: list[dict] = []
if PROTOCOLS_PATH.exists():
    with open(PROTOCOLS_PATH, "r", encoding="utf-8") as f:
        _condition_protocols = json.load(f)

# Build lookup: condition_key → protocol (later entries override earlier for same key)
_PROTOCOL_MAP: dict[str, dict] = {}
for _p in _condition_protocols:
    for _cond in [_p["condition"]] + _p.get("alternate_conditions", []):
        _PROTOCOL_MAP[_cond.lower()] = _p


# ── Surya Namaskar (Sun Salutation) ──────────────────────────────────────────
# Classical 12-step sequence with pose IDs, Sanskrit names, and teaching cues.
# Injected as a dedicated flow block in morning practice sessions.

_SURYA_NAMASKAR_STEPS = [
    {
        "step": 1,
        "sanskrit": "Pranamasana",
        "english": "Prayer Pose",
        "pose_id": "mountain_pose",
        "cue": "Stand at the top of your mat. Bring palms together at the heart. Close the eyes. Set your intention for the practice.",
        "breath": "Natural",
    },
    {
        "step": 2,
        "sanskrit": "Hasta Uttanasana",
        "english": "Raised Arms Pose",
        "pose_id": "upward_salute",
        "cue": "Inhale — sweep the arms overhead, biceps by the ears. Gently arch back, lifting the chest toward the sky. Gaze up.",
        "breath": "Inhale",
    },
    {
        "step": 3,
        "sanskrit": "Padahastasana",
        "english": "Standing Forward Fold",
        "pose_id": "gorilla_pose",
        "cue": "Exhale — hinge at the hips and fold forward. Place hands beside the feet (bend knees if needed). Let the crown hang heavy.",
        "breath": "Exhale",
        "modification": "Hypertension: keep knees deeply bent; do not let head drop below the heart for more than 3 seconds.",
    },
    {
        "step": 4,
        "sanskrit": "Ashwa Sanchalanasana",
        "english": "Equestrian Pose (Right Leg Back)",
        "pose_id": "equestrian_pose",
        "cue": "Inhale — step the right foot back into a low lunge. Left knee over left ankle. Lift the chest, gaze forward.",
        "breath": "Inhale",
        "side": "right_leg_back",
    },
    {
        "step": 5,
        "sanskrit": "Phalakasana",
        "english": "Plank Pose",
        "pose_id": "plank",
        "cue": "Exhale — step the left foot back to meet the right. Full plank: hands under shoulders, body a straight line from crown to heels. Hold 1 breath.",
        "breath": "Exhale",
        "modification": "Wrist issues or beginners: drop to forearm plank or lower knees to the mat.",
    },
    {
        "step": 6,
        "sanskrit": "Ashtanga Namaskara",
        "english": "Eight-Limb Salute",
        "pose_id": "four_limbed_staff_pose",
        "cue": "Exhale — lower to the floor touching 8 points: toes, knees, chest, chin, hands. Elbows hug the ribs. This is the classical transition, not a push-up.",
        "breath": "Exhale",
        "modification": "Beginners: from Plank, simply lower all the way to the floor (lie prone). Skip this step if you have wrist or shoulder injuries.",
    },
    {
        "step": 7,
        "sanskrit": "Bhujangasana",
        "english": "Cobra Pose",
        "pose_id": "cobra_pose",
        "cue": "Inhale — press the tops of the feet down, untuck the toes, and lift the chest using the back muscles (not the arms). Elbows remain soft. Gaze forward.",
        "breath": "Inhale",
        "modification": "Back pain: use Sphinx (forearms on floor) instead of full Cobra.",
    },
    {
        "step": 8,
        "sanskrit": "Adho Mukha Svanasana",
        "english": "Downward-Facing Dog",
        "pose_id": "downward_facing_dog",
        "cue": "Exhale — tuck the toes, press through the hands, and lift the hips high. Press the chest toward the thighs. Pedal the heels gently. Hold 3-5 breaths.",
        "breath": "Exhale — hold 3-5 breaths",
    },
    {
        "step": 9,
        "sanskrit": "Ashwa Sanchalanasana",
        "english": "Equestrian Pose (Left Leg Forward)",
        "pose_id": "low_lunge_pose",
        "cue": "Inhale — step the left foot forward between the hands. Right knee may lower to the mat. Lift the chest, gaze forward.",
        "breath": "Inhale",
        "side": "left_leg_forward",
    },
    {
        "step": 10,
        "sanskrit": "Padahastasana",
        "english": "Standing Forward Fold",
        "pose_id": "gorilla_pose",
        "cue": "Exhale — step the right foot forward to meet the left. Forward fold. Hands beside feet. Let the spine decompress with gravity.",
        "breath": "Exhale",
    },
    {
        "step": 11,
        "sanskrit": "Hasta Uttanasana",
        "english": "Raised Arms Pose",
        "pose_id": "upward_salute",
        "cue": "Inhale — sweep the arms overhead as you rise, bringing the palms together above the head. Light arch in the upper back.",
        "breath": "Inhale",
    },
    {
        "step": 12,
        "sanskrit": "Pranamasana",
        "english": "Prayer Pose",
        "pose_id": "mountain_pose",
        "cue": "Exhale — bring the palms back to Anjali Mudra (prayer) at the heart. Pause. Feel the warmth generated. One round complete.",
        "breath": "Exhale",
    },
]

# Contra-tags that block Surya Namaskar inclusion
_SNS_CONTRAINDICATION_TAGS = {
    "serious_back_injury", "herniated_disc", "serious_spinal_injury",
    "heart_disease", "glaucoma",
}
# Tags that trigger a modified version (chair-supported / wrist-safe)
_SNS_MODIFICATION_TAGS = {
    "wrist_injury", "rotator_cuff", "shoulder_injury",
    "high_blood_pressure", "hypertension",
    "lower_back_pain", "knee_injury",
}

# Dosha-based pacing.
#
# Rounds used to be the constitutional signal — Kapha did 8 where Vata did 2 —
# which made the block anywhere from 2 to 8 minutes long and left the session's
# opening a different length for everybody. Surya Namaskar is now a FIXED slot
# (`_SESSION_STRUCTURE`) and the dosha sets the *pace* instead, so the rounds
# fall out of how fast you move through the slot. Nothing constitutional is
# lost: Kapha still flows vigorously and covers more ground in the same five
# minutes, Vata still moves slowly and covers less. Experience shifts the pace
# by a second a step for the same reason.
_SNS_SECONDS_PER_STEP = {"slow": 6, "moderate": 5, "vigorous": 4}
_SNS_EXPERIENCE_PACE = {"beginner": 1, "intermediate": 0, "advanced": -1}

# Rest between rounds, which the practitioner spends in Downward Dog.
_SNS_INTER_ROUND_SECONDS = 15

_SNS_DOSHA_CONFIG = {
    "vata":  {"pace": "slow",  "pace_note": "Move slowly and mindfully — 1 breath per movement. Prioritise steadiness over speed to ground Vata energy."},
    "pitta": {"pace": "moderate", "pace_note": "Moderate pace — avoid overheating. Rest in Downward Dog for 5 breaths between rounds. Never compete with yourself."},
    "kapha": {"pace": "vigorous", "pace_note": "Vigorous, continuous flow. Build heat with purpose — Kapha benefits most from dynamic sequences that activate metabolic fire."},
}


def _sns_rounds_for_budget(seconds_per_step: int, target_seconds: int) -> tuple[int, int]:
    """Rounds that land closest to the slot, and the seconds they actually take.

    Twelve steps is indivisible, so the block cannot hit the target exactly —
    it lands on whichever whole number of rounds is nearest, which across the
    dosha × experience grid means 4.7 to 5.6 minutes against a 5-minute slot.
    """
    round_seconds = 12 * seconds_per_step
    step = round_seconds + _SNS_INTER_ROUND_SECONDS
    lower = max(1, int((target_seconds + _SNS_INTER_ROUND_SECONDS) // step))
    best = min(
        (lower, lower + 1),
        key=lambda r: abs(r * round_seconds + (r - 1) * _SNS_INTER_ROUND_SECONDS
                          - target_seconds),
    )
    return best, best * round_seconds + (best - 1) * _SNS_INTER_ROUND_SECONDS


def _build_surya_namaskar_block(user_profile: dict, yoga_prefs: dict,
                                 contra_tags: set, age_group: str,
                                 target_seconds: int) -> dict | None:
    """Return a Surya Namaskar flow block or None if contraindicated.

    `target_seconds` is the fixed slot the session reserves for it. The gates
    below still return None outright — a fixed slot is a statement about how
    long the practice opens for, never a reason to serve a contraindicated one.
    """
    time_of_day = (yoga_prefs.get("time_of_day_preference") or "morning").lower()

    # Surya Namaskar is a solar practice — morning only
    if time_of_day == "evening":
        return None

    # Pregnancy: skip entirely. Nursing does not rule out Surya Namaskar.
    if _pregnancy_state(user_profile)[0]:
        return None

    # Hard contraindications — for seniors use only user-specific medical contra tags
    # (age-appended tags like _AGE_SENIOR_CONTRA are handled via chair modification, not by blocking)
    sns_contra_check = _build_contra_set(user_profile, "adult") if age_group == "senior" else contra_tags
    if sns_contra_check.intersection(_SNS_CONTRAINDICATION_TAGS):
        return None

    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    dosha_cfg = _SNS_DOSHA_CONFIG.get(dosha, _SNS_DOSHA_CONFIG["vata"])
    seconds_per_step = max(3, _SNS_SECONDS_PER_STEP[dosha_cfg["pace"]]
                           + _SNS_EXPERIENCE_PACE.get(exp, 1))

    # Senior: 1 round, chair-supported. This is the one profile that does NOT
    # fill the slot — a chair-supported round is not something to repeat four
    # times to reach a number — and the minutes it gives back go to asana.
    if age_group == "senior":
        rounds = 1
        block_seconds = 12 * seconds_per_step
        modification = "Chair-supported Surya Namaskar: perform Steps 1-3 and 10-12 standing. Replace Steps 4-9 with seated chair poses. Always keep one hand on the chair back."
    else:
        rounds, block_seconds = _sns_rounds_for_budget(seconds_per_step, target_seconds)
        modification = None

    # Soft modifications for wrist/BP/back — don't skip, just note
    warnings = []
    if contra_tags.intersection({"wrist_injury", "shoulder_injury", "rotator_cuff"}):
        warnings.append("Wrist/shoulder: skip Chaturanga (Step 6) — lower directly to the floor from Plank.")
    if contra_tags.intersection({"high_blood_pressure", "hypertension"}):
        warnings.append("Blood pressure: bend knees in forward folds; avoid holding the breath between steps.")
    if contra_tags.intersection({"lower_back_pain"}):
        warnings.append("Lower back: replace Cobra (Step 7) with Sphinx Pose and keep knees bent in forward folds.")
    if contra_tags.intersection({"knee_injury"}):
        warnings.append("Knee injury: skip the Equestrian (Steps 4 & 9) or use a supported low lunge with the back knee on a blanket.")

    return {
        "rounds": rounds,
        "duration_minutes": round(block_seconds / 60, 1),
        "seconds_per_step": seconds_per_step,
        "pace": dosha_cfg["pace"],
        "pace_note": dosha_cfg["pace_note"],
        "senior_modification": modification,
        "safety_notes": warnings,
        "ayurvedic_note": (
            f"Surya Namaskar activates Surya Nadi (right solar channel) — the seat of Agni and Prana. "
            f"Classically prescribed at sunrise facing east. For {dosha.title()} predominance, "
            f"{rounds} rounds at {dosha_cfg['pace']} pace balances your constitution."
        ),
        "classical_reference": (
            "Hatha Yoga Pradipika 1.20 — 'Surya Namaskar should be done daily. It removes all diseases "
            "and gives Agni (digestive fire) and removes laziness.' "
            "Gheranda Samhita 2.1 — listed among the seven practices that purify the body."
        ),
        "steps": _SURYA_NAMASKAR_STEPS,
    }


# ── Pregnancy / nursing ───────────────────────────────────────────────────────
# `pregnancy_or_nursing` is one boolean covering two states whose restrictions
# have almost nothing in common: pregnancy rules out prone poses, supine holds,
# deep twists, inversions and abdominal work, while nursing rules out
# essentially nothing. Treating a nursing mother as pregnant costs her most of
# the library for no clinical reason.
#
# The refinement is opt-in. Where the user has not told us which they are, the
# boolean is still read as "pregnant" — the safe reading, and the behaviour
# every other engine in the codebase still relies on.

# Category exclusions by trimester. First trimester is comparatively
# unrestricted; from the second the growing uterus rules out lying prone, and
# extended supine holds risk vena cava compression.
_TRIMESTER_BLOCKED_CATEGORIES = {
    1: set(),
    2: {"prone"},
    3: {"prone", "supine", "inversion"},
}

# Mechanisms unsafe throughout pregnancy, plus what each trimester adds.
_TRIMESTER_RISK_TAGS = {
    1: {"abdominal_pressure"},
    2: {"abdominal_pressure", "intracranial_pressure"},
    3: {"abdominal_pressure", "intracranial_pressure", "fall_risk"},
}


def _pregnancy_state(user_profile: dict) -> tuple[bool, bool, int]:
    """Return (is_pregnant, is_nursing, trimester).

    Trimester defaults to 3 — the most restrictive — when the user says they are
    pregnant but not how far along. Guessing gently would be the wrong default
    for a safety gate.
    """
    flag = bool(user_profile.get("pregnancy_or_nursing"))
    status = (user_profile.get("pregnancy_status") or "").strip().lower()

    if status == "nursing":
        return False, True, 0
    if status == "pregnant":
        is_pregnant = True
    else:
        is_pregnant = flag  # unspecified: the boolean means pregnant

    if not is_pregnant:
        return False, False, 0

    try:
        trimester = int(user_profile.get("pregnancy_trimester") or 3)
    except (TypeError, ValueError):
        trimester = 3
    return True, False, min(max(trimester, 1), 3)


# ── Week-by-week progression from user feedback ───────────────────────────────
# A four-week plan generated up front has to guess how week 3 should go before
# the user has practised week 1. Weeks are now generated one at a time, each one
# shaped by what the user reported about the last.
#
# The mapping from feedback to plan change is DETERMINISTIC — the same answers
# always produce the same adjustment. Nothing here goes through an LLM, for the
# same reason plan authoring doesn't: a vaidya has to be able to audit why week 3
# got easier, and "the model decided" is not an answer.

_TOTAL_WEEKS = 4
DEFAULT_WEEKS_GENERATED = 1

# Per-answer effect. Multiplicative fields compose across weeks, additive ones sum.
#
# There is deliberately no per-pose "hold length" lever here. Section budgets are
# filled to the requested session length, so shortening base holds just makes the
# filler stretch them back or add poses — the knob reads as if it does something
# and measurably does not. The levers below all survive that: which poses are
# eligible, which categories are favoured, and how long the session runs.
_DIFFICULTY_EFFECT = {
    "too_easy":   {"level_shift": 1,  "duration_scale": 1.1},
    "just_right": {},
    "too_hard":   {"level_shift": -1, "duration_scale": 0.9, "restorative_bias": 3},
}
_LENGTH_EFFECT = {
    "too_short":  {"duration_scale": 1.2},
    "just_right": {},
    "too_long":   {"duration_scale": 0.8},
}
_ENERGY_EFFECT = {
    "energised":  {},
    "neutral":    {},
    # Feeling wrung out after practice is the clearest signal that the load is
    # wrong, regardless of what the difficulty answer said.
    "drained":    {"duration_scale": 0.9, "restorative_bias": 3},
}

# Bounds on the accumulated adjustment. Without these, four consecutive
# "too hard" answers would drive the practice to nothing.
_LEVEL_SHIFT_BOUNDS = (-2, 2)
_DURATION_SCALE_BOUNDS = (0.5, 1.5)
_RESTORATIVE_BIAS_MAX = 4


class WeekAdjustment:
    """How the next week differs from the default progression."""

    __slots__ = ("level_shift", "duration_scale",
                 "restorative_bias", "excluded_pose_ids", "reasons")

    def __init__(self, level_shift=0, duration_scale=1.0,
                 restorative_bias=0, excluded_pose_ids=(), reasons=()):
        self.level_shift = level_shift
        self.duration_scale = duration_scale
        self.restorative_bias = restorative_bias
        self.excluded_pose_ids = frozenset(excluded_pose_ids)
        self.reasons = tuple(reasons)

    def as_dict(self) -> dict:
        return {
            "level_shift": self.level_shift,
            "duration_scale": round(self.duration_scale, 2),
            "restorative_bias": self.restorative_bias,
            "excluded_pose_count": len(self.excluded_pose_ids),
            "reasons": list(self.reasons),
        }


def _clamp(value, bounds):
    low, high = bounds
    return max(low, min(value, high))


def build_week_adjustment(feedback_history) -> WeekAdjustment:
    """Fold every week of feedback so far into one adjustment.

    Reads the whole history rather than only the most recent week: someone who
    reports "too hard" three weeks running needs the practice to keep easing,
    not to reset to default the moment they stop saying it.
    """
    level_shift = 0
    duration_scale = 1.0
    restorative_bias = 0
    excluded: set[str] = set()

    for entry in (feedback_history or []):
        if not isinstance(entry, dict):
            continue
        effects = [
            _DIFFICULTY_EFFECT.get(entry.get("difficulty"), {}),
            _LENGTH_EFFECT.get(entry.get("session_length"), {}),
            _ENERGY_EFFECT.get(entry.get("energy_after"), {}),
        ]

        # Practising 3 days or fewer usually means the sessions did not fit the
        # week, not that the user gave up. Shorten them so they can be kept.
        days = entry.get("days_practised")
        if isinstance(days, int) and days <= 3:
            effects.append({"duration_scale": 0.8})

        for effect in effects:
            level_shift += effect.get("level_shift", 0)
            duration_scale *= effect.get("duration_scale", 1.0)
            restorative_bias += effect.get("restorative_bias", 0)

        dropped = entry.get("dropped_pose_ids") or []
        excluded.update(str(p) for p in dropped if p)

    level_shift = _clamp(level_shift, _LEVEL_SHIFT_BOUNDS)
    duration_scale = _clamp(duration_scale, _DURATION_SCALE_BOUNDS)
    restorative_bias = min(restorative_bias, _RESTORATIVE_BIAS_MAX)

    # Describe where the practice has NET landed, not every answer that got it
    # there. Listing per-answer reasons meant week 4 still read "you found last
    # week hard" three weeks after the user stopped saying so — and alongside
    # "last week was too easy", which contradicted it.
    reasons = []
    if level_shift < 0:
        reasons.append("Working at a gentler level than your stated experience.")
    elif level_shift > 0:
        reasons.append("Working a level above your stated experience.")
    if duration_scale < 0.97:
        reasons.append(f"Sessions are about {round((1 - duration_scale) * 100)}% shorter than your default.")
    elif duration_scale > 1.03:
        reasons.append(f"Sessions are about {round((duration_scale - 1) * 100)}% longer than your default.")
    if restorative_bias > 0:
        reasons.append("More restorative and grounding work in the mix.")
    if excluded:
        reasons.append(f"{len(excluded)} pose(s) you asked to drop are excluded.")

    return WeekAdjustment(
        level_shift=level_shift,
        duration_scale=duration_scale,
        restorative_bias=restorative_bias,
        excluded_pose_ids=excluded,
        reasons=reasons,
    )


_EXPERIENCE_LADDER = ["beginner", "intermediate", "advanced"]


def _shift_experience(experience: str, shift: int) -> str:
    """Move the practitioner a rung up or down the experience ladder."""
    try:
        idx = _EXPERIENCE_LADDER.index(experience)
    except ValueError:
        idx = 0
    return _EXPERIENCE_LADDER[_clamp(idx + shift, (0, len(_EXPERIENCE_LADDER) - 1))]


# ── Age group classification ───────────────────────────────────────────────────

def _get_age_group(age) -> str:
    if age is None:
        return "adult"
    try:
        a = int(age)
    except (TypeError, ValueError):
        return "adult"
    if a >= 60:
        return "senior"
    if a <= 17:
        return "youth"
    return "adult"

# Senior: block inversions, high-effort backbends, and anything with neck/blood pressure risk
_AGE_SENIOR_CONTRA = {"glaucoma", "high_blood_pressure", "heart_disease", "neck_injury", "serious_spinal_injury"}

# Gender-gated protocols — only surface for female users
_FEMALE_ONLY_PROTOCOLS = {"pcos", "menopause", "pms", "pregnancy", "premenstrual_syndrome",
                          "artava_dushti", "pmt", "pmdd"}


# ── Per-category modifications ────────────────────────────────────────────────

_MODIFICATIONS = {
    "standing": {
        "beginner":     "Stand near a wall for balance. Keep a slight bend in the knees. Reduce the range of motion.",
        "intermediate": "Use a block under the bottom hand if it doesn't reach the floor comfortably.",
        "advanced":     "Deepen the pose by lengthening the breath. Explore a bind or closed-eye variation.",
    },
    "balancing": {
        "beginner":     "Place fingertips on a wall or chair back. Fix your drishti (gaze) on a single still point.",
        "intermediate": "Use a block if balance is unstable. Draw the navel in to engage your core.",
        "advanced":     "Close the eyes to challenge proprioception. Try the full arm variation.",
    },
    "seated": {
        "beginner":     "Sit on a folded blanket to tilt the pelvis forward and reduce lower back strain.",
        "intermediate": "Use a strap around the feet if hamstrings are tight. Keep the spine long.",
        "advanced":     "Work the foot deeper into the hip crease. Explore the closed-eye, breath-focused variation.",
    },
    "forward_fold": {
        "beginner":     "Bend the knees generously. Place a bolster or block on your shins to rest on.",
        "intermediate": "Maintain a flat back for the first half of the fold before releasing the spine.",
        "advanced":     "Activate the quadriceps to allow the hamstrings to release more deeply.",
    },
    "twist": {
        "beginner":     "Keep the bottom leg straight. Use the exhale to deepen — never force the rotation.",
        "intermediate": "Work the bind only if the spine is fully erect first.",
        "advanced":     "Close eyes and use breath to explore the twist's full range without strain.",
    },
    "inversion": {
        "beginner":     "Practice near a wall. Do not attempt if you have neck, shoulder, or blood pressure issues.",
        "intermediate": "Work on core stability before moving away from the wall.",
        "advanced":     "Practice against a wall until you can hold for 60 seconds before attempting freestanding.",
    },
    "backbend": {
        "beginner":     "Focus on opening the chest rather than depth. Keep the lower back long, not compressed.",
        "intermediate": "Press firmly through the hands and feet to distribute the backbend evenly.",
        "advanced":     "Warm up the spine thoroughly before deep backbends. Use the exhale to avoid compression.",
    },
    "restorative": {
        "beginner":     "Use as many props as needed — bolsters, blankets, blocks. Comfort is the entire point.",
        "intermediate": "Reduce the number of props to deepen sensation, but only if completely comfortable.",
        "advanced":     "Extend the hold time rather than reducing support. Longer holds are the advancement.",
    },
    "supine": {
        "beginner":     "Place a blanket under the knees for lower back support. Keep movements slow.",
        "intermediate": "Draw the navel gently in to protect the lumbar spine during leg movements.",
        "advanced":     "Slow the breath to a 4:8 inhale-exhale ratio to deepen the parasympathetic response.",
    },
    "prone": {
        "beginner":     "Place a folded blanket under the hips to reduce lower back compression.",
        "intermediate": "Focus on lengthening the spine before lifting — lead with the crown, not the chin.",
        "advanced":     "Use the inhale to lift and the exhale to release further — never force the range.",
    },
}

_DEFAULT_MOD = {
    "beginner":     "Work within your comfortable range. Use props freely and reduce intensity as needed.",
    "intermediate": "Maintain alignment over depth. Use a prop if form is compromised.",
    "advanced":     "Explore the breath relationship within the pose. Longer holds are the next frontier.",
}

_SENIOR_MOD_SUFFIX = " Use a chair or wall for support. Reduce hold times by one-third."
_YOUTH_MOD_SUFFIX  = " Explore joyfully — rest any time you feel breathless or fatigued."


def _get_modification(pose: dict, experience: str, age_group: str = "adult") -> str:
    cat = pose.get("category", "standing")
    mods = _MODIFICATIONS.get(cat, _DEFAULT_MOD)
    base = mods.get(experience, _DEFAULT_MOD.get(experience, "Use props as needed."))
    if age_group == "senior":
        return base + _SENIOR_MOD_SUFFIX
    if age_group == "youth":
        return base + _YOUTH_MOD_SUFFIX
    return base


# ── 4-week progressive structure ──────────────────────────────────────────────

_WEEK_CONFIG = {
    1: {"theme": "Foundation",  "hold_mult": 1.0,  "note": "Focus on alignment and finding the pose. Use props freely. Quality over depth."},
    2: {"theme": "Deepen",      "hold_mult": 1.25, "note": "Extend hold times by 25%. Notice where the body resists — breathe into those areas."},
    3: {"theme": "Challenge",   "hold_mult": 1.5,  "note": "Peak week — longer holds and fuller range. Try the advanced modification on one pose per session."},
    4: {"theme": "Integration", "hold_mult": 1.1,  "note": "Consolidate. Practice flows smoothly with confident breath. Add 10% hold time, reduce mental effort."},
}

# Per-experience progressive level gates (unlocks intermediate in Week 3 for beginners)
_PROGRESSIVE_LEVELS = {
    "beginner":     {1: ["beginner"], 2: ["beginner"], 3: ["beginner", "intermediate"], 4: ["beginner"]},
    "intermediate": {1: ["beginner", "intermediate"], 2: ["beginner", "intermediate"],
                     3: ["beginner", "intermediate", "advanced"], 4: ["beginner", "intermediate"]},
    "advanced":     {1: ["beginner", "intermediate"], 2: ["beginner", "intermediate", "advanced"],
                     3: ["beginner", "intermediate", "advanced"], 4: ["beginner", "intermediate", "advanced"]},
}


def _week_hold(base_seconds: int, week: int) -> int:
    return int(base_seconds * _WEEK_CONFIG.get(week, _WEEK_CONFIG[1])["hold_mult"])


# ── Daily intensity arc ───────────────────────────────────────────────────────
# Seven sessions at one intensity is not a week of practice, it is one session
# seven times. Week 3 at 1.5x holds, repeated daily with no let-up, is how a
# plan produces the "drained" feedback it then has to correct for.
#
# There are still no rest days — Dinacharya prescribes daily sadhana — so the
# recovery day is a restorative session in the same slot rather than a gap. The
# streak survives; the load drops.
#
# What must NOT vary is duration. `asana_budget_seconds` is computed once per
# week by the caller and every day fills the same budget, because a practice
# survives by occupying a fixed slot in the day: a plan asking for 20 minutes on
# Monday and 45 on Thursday is a plan abandoned on Thursday. The arc changes
# which poses are allowed and how long they are held, and the budget machinery
# absorbs the difference in pose count.
#
# The arc only ever NARROWS what the week already permits. Making a "strong" day
# reach past `week_allowed_levels` would put a new safety surface behind a
# weekday index, so strong simply means the full week allowance.
_LEVEL_ORDER = ["beginner", "intermediate", "advanced"]

# Two strong days, never consecutive; three moderate; one gentle; one
# restorative. Monday is moderate rather than strong because a week that opens
# at its hardest is the other way most people quit.
_DAY_ARC = {
    1: {"key": "moderate",    "label": "Moderate",    "hold_mult": 1.0,
        "max_level": None,          "categories": None,
        "accent": ["standing", "seated"],
        "note": "A steady, foundational practice. Find your alignment before the week asks more."},
    2: {"key": "strong",      "label": "Strong",      "hold_mult": 1.0,
        "max_level": None,          "categories": None,
        "accent": ["backbend", "standing"],
        "note": "One of the week's two demanding days. Work to a firm edge, never past the breath."},
    3: {"key": "moderate",    "label": "Moderate",    "hold_mult": 1.0,
        "max_level": None,          "categories": None,
        "accent": ["twist", "prone"],
        "note": "Steady work with an emphasis on rotation — unwinding yesterday's extension."},
    4: {"key": "strong",      "label": "Strong",      "hold_mult": 1.0,
        "max_level": None,          "categories": None,
        "accent": ["balancing", "inversion"],
        "note": "The week's second demanding day. Balance work asks for a fresh, attentive mind."},
    5: {"key": "moderate",    "label": "Moderate",    "hold_mult": 1.0,
        "max_level": None,          "categories": None,
        "accent": ["forward_fold", "seated"],
        "note": "Moderate effort, turning inward. Forward folds cool the system after two strong days."},
    # The easy days keep the week's sequence. An earlier version capped their
    # level and categories, which dropped most of the core and left Saturday
    # sharing almost nothing with the rest of the week — a different class, not a
    # lighter one. Lightness is now carried by hold length, by which poses the
    # accent pulls in, and by `effort_cue`, which changes how every pose is
    # performed rather than which poses appear.
    #
    # Day 7 keeps two exclusions because they are about load, not difficulty:
    # doing an inversion or a deep backbend is contrary to the point of a
    # recovery day whatever your level.
    # `hold_mult` is deliberately 1.0 here. A 0.95 was measured and did nothing:
    # shortening holds frees budget, the filler spends it, and `_hold_multiplier`
    # stretches the rest straight back — the same reason the feedback loop has no
    # hold lever. The gentle day's difference is `ease_modifications`, which
    # shows every pose at one experience level easier (props, bent knees, reduced
    # range) and survives the budget because it changes nothing about timing.
    6: {"key": "gentle",      "label": "Gentle",      "hold_mult": 1.0,
        "ease_modifications": True,
        "accent": ["seated", "supine", "forward_fold"],
        "effort_cue": "Stay well inside your range today and take the supported "
                      "variation wherever one is offered.",
        "note": "A light day — the same sequence as the rest of the week, taken at "
                "an easier depth. Active recovery, not a lesser practice."},
    7: {"key": "restorative", "label": "Restorative", "hold_mult": 1.25,
        "ease_modifications": True,
        "exclude_categories": ["inversion", "backbend"],
        "widen_accent": ["restorative", "supine", "forward_fold", "seated"],
        "accent": ["restorative", "supine"],
        "effort_cue": "Let each pose be held rather than worked. Use props freely — "
                      "a bolster, a blanket, a wall — and let them carry the weight.",
        "note": "Your recovery day, in the same slot and largely the same sequence as "
                "every other. Longer, supported holds; nothing is pushed."},
}

# What a day softens to when the practitioner has been reporting that the
# practice is too much. Feedback already lowers the level, shortens the session
# and biases the scoring toward restorative work; the arc modulates WITHIN that
# rather than adding a second, independent reduction on top. Days already at or
# below "gentle" are absent because they have nowhere left to go.
_ARC_SOFTEN = {"strong": "moderate", "moderate": "gentle"}
_ARC_SOFTEN_THRESHOLD = 3


def _day_intensity(day_num: int, adjustment: "WeekAdjustment | None" = None) -> dict:
    """The intensity profile for one day of the week.

    Softened a step when accumulated feedback says the practice has been too
    much — a week that has already been pulled down by `restorative_bias` should
    not still be scheduling two strong days.
    """
    arc = dict(_DAY_ARC.get(((day_num - 1) % 7) + 1, _DAY_ARC[1]))
    bias = getattr(adjustment, "restorative_bias", 0) or 0
    softened_key = _ARC_SOFTEN.get(arc["key"]) if bias >= _ARC_SOFTEN_THRESHOLD else None
    if softened_key:
        source = next(d for d in _DAY_ARC.values() if d["key"] == softened_key)
        # Every shaping key is replaced, not merged — carrying the strong day's
        # absent `level_drop` over a softened one would leave the cap off.
        for key in ("key", "label", "hold_mult", "note", "effort_cue", "accent",
                    "max_level", "level_drop", "categories", "exclude_categories",
                    "widen_accent", "ease_modifications"):
            arc[key] = source.get(key)
        arc["softened"] = True
    return arc


def _arc_level_cap(arc: dict, week_levels: list | None) -> str | None:
    """The hardest pose level this day allows, or None for no arc-level cap."""
    absolute = arc.get("max_level")
    if absolute:
        return absolute
    drop = arc.get("level_drop")
    if not drop:
        return None
    unlocked = [lv for lv in _LEVEL_ORDER if lv in (week_levels or _LEVEL_ORDER)]
    if not unlocked:
        return None
    ceiling = _LEVEL_ORDER.index(unlocked[-1])
    return _LEVEL_ORDER[max(ceiling - drop, 0)]


def _arc_allows(pose: dict, arc: dict, week_levels: list | None) -> bool:
    """Whether the day's intensity permits this pose."""
    cat = pose.get("category")
    allowed = arc.get("categories")
    if allowed and cat not in allowed:
        return False
    if cat in (arc.get("exclude_categories") or ()):
        return False
    cap = _arc_level_cap(arc, week_levels)
    if cap:
        level = pose.get("level", "beginner")
        if level not in _LEVEL_ORDER:
            return True
        if _LEVEL_ORDER.index(level) > _LEVEL_ORDER.index(cap):
            return False
    return True


# ── Deterministic selection ───────────────────────────────────────────────────

def _det_shuffle(pool: list, seed_key: str) -> list:
    seed = int(hashlib.md5(seed_key.encode()).hexdigest(), 16) % (2 ** 31)
    rng = random.Random(seed)
    out = list(pool)
    rng.shuffle(out)
    return out


# ── Filtering ─────────────────────────────────────────────────────────────────

_MEDICAL_CONTRA_MAP = {
    "hypertension":        {"hypertension", "high_blood_pressure"},
    "high_blood_pressure": {"hypertension", "high_blood_pressure"},
    "heart_disease":       {"heart_disease"},
    "glaucoma":            {"glaucoma"},
    "cervical_spondylosis":{"neck_injury", "cervical_spondylosis", "serious_neck_injury"},
    "cervical_disc":       {"neck_injury", "cervical_spondylosis", "serious_neck_injury"},
    "sciatica":            {"serious_back_injury", "sciatica", "back_pain"},
    "herniated_disc":      {"herniated_disc", "serious_back_injury", "serious_spinal_injury"},
    "spinal_injury":       {"serious_spinal_injury", "spinal_injury"},
    "knee_injury":         {"knee_injury", "knee_replacement"},
    "knee_replacement":    {"knee_injury", "knee_replacement"},
    "ankle_injury":        {"ankle_injury"},
    "shoulder_injury":     {"shoulder_injury", "rotator_cuff"},
    "osteoporosis":        {"serious_spinal_injury"},
    "post_cardiac":        {"heart_disease", "high_blood_pressure"},
    "heart_surgery_recovery": {"heart_disease", "high_blood_pressure"},
    # ── Tokens the KB already used that no user input could reach ──
    # These maps are the only route from what a user reports to what a pose says about
    # itself, so a contraindication the maps never emit is data that cannot fire. Before
    # this, "arthritis" was listed on 41 poses and excluded 1; hip and hamstring injuries
    # were listed on 16 and 13 and excluded none. Only "rheumatoid_arthritis" was wired,
    # so the far more common osteoarthritis got no protection at all.
    # Substring matching means "arthritis" also catches "rheumatoid arthritis" and
    # "osteoarthritis", which is intended.
    "arthritis":           {"arthritis"},
    "back_pain":           {"back_pain", "lower_back_pain", "serious_back_injury"},
    "hip_injury":          {"hip_injury"},
    "hip_replacement":     {"hip_injury"},
    "hamstring_injury":    {"hamstring_injury"},
    "groin_injury":        {"groin_injury"},
    "asthma":              {"asthma"},
    "migraine":            {"migraine"},
}

# ── Condition → risk mechanism ───────────────────────────────────────────────
# Conditions used to be mapped onto whichever pose tag was vaguely nearby:
# hernia onto knee_injury, epilepsy onto heart_disease, migraine onto
# high_blood_pressure, wrist onto shoulder_injury. Those tags describe a
# different body part, so the poses that actually endanger those users were
# never the ones removed — blocking knee poses does nothing for a hernia.
#
# These map to what a pose *does* (`risk_tags` in the KB), so the exclusion
# matches the mechanism: abdominal pressure for hernia, intracranial pressure
# for glaucoma and retinal detachment, loaded spinal flexion for osteoporosis.
_CONDITION_RISK_TAGS: dict[str, set[str]] = {
    "hernia":               {"abdominal_pressure"},
    "inguinal_hernia":      {"abdominal_pressure"},
    "hiatal_hernia":        {"abdominal_pressure"},
    "abdominal_surgery":    {"abdominal_pressure", "wrist_weight_bearing"},
    "recent_surgery":       {"abdominal_pressure"},
    "ulcer":                {"abdominal_pressure"},
    "ibd":                  {"abdominal_pressure"},
    "diverticulitis":       {"abdominal_pressure"},

    "glaucoma":             {"intracranial_pressure"},
    "retinal_detachment":   {"intracranial_pressure"},
    "retinopathy":          {"intracranial_pressure"},
    "migraine":             {"intracranial_pressure"},
    "sinusitis":            {"intracranial_pressure"},
    "stroke":               {"intracranial_pressure", "fall_risk"},

    "epilepsy":             {"seizure_risk", "intracranial_pressure", "fall_risk"},
    "seizure":              {"seizure_risk", "intracranial_pressure", "fall_risk"},

    "vertigo":              {"fall_risk", "neck_load", "intracranial_pressure"},
    "bppv":                 {"fall_risk", "neck_load", "intracranial_pressure"},
    "labyrinthitis":        {"fall_risk", "neck_load", "intracranial_pressure"},
    "vestibular":           {"fall_risk", "neck_load", "intracranial_pressure"},
    "parkinson":            {"fall_risk"},
    "multiple_sclerosis":   {"fall_risk"},
    "neuropathy":           {"fall_risk"},

    "osteoporosis":         {"spinal_flexion", "fall_risk", "spinal_extension"},
    "osteopenia":           {"spinal_flexion"},
    "compression_fracture": {"spinal_flexion", "spinal_extension"},

    # Spinal EXTENSION — backbending. The mechanism vocabulary covered flexion but
    # not its opposite, so an entire movement class (18 poses) had no mechanism at
    # all and could only be caught by a pose's hand-written contraindication list.
    #
    # Herniated disc is deliberately NOT mapped here. Extension is frequently the
    # therapeutic direction for a posterior disc herniation, and excluding backbends
    # for those users would be actively wrong — it is already covered by its own
    # contraindication tokens where individual poses call for it. These four are the
    # conditions where loading into extension is the recognised problem.
    "spondylolisthesis":    {"spinal_extension"},
    "spondylolysis":        {"spinal_extension"},
    "spinal_stenosis":      {"spinal_extension"},
    "facet":                {"spinal_extension"},

    "carpal_tunnel":        {"wrist_weight_bearing"},
    "wrist_injury":         {"wrist_weight_bearing"},
    "rheumatoid_arthritis": {"wrist_weight_bearing"},

    "cervical_spondylosis": {"neck_load"},
    "cervical_disc":        {"neck_load"},
    "neck_injury":          {"neck_load"},
    "whiplash":             {"neck_load"},
}

# Injury free-text → risk mechanism, for the same reason as above.
_INJURY_RISK_TAGS: dict[str, set[str]] = {
    "wrist":  {"wrist_weight_bearing"},
    "hand":   {"wrist_weight_bearing"},
    "neck":   {"neck_load"},
    "hernia": {"abdominal_pressure"},
    "balance": {"fall_risk"},
}

_INJURY_CONTRA_MAP = {
    "bad_knee":        {"knee_injury", "knee_replacement"},
    "knee":            {"knee_injury", "knee_replacement"},
    "lower_back":      {"lower_back_pain", "back_pain", "herniated_disc", "serious_back_injury"},
    "back":            {"lower_back_pain", "back_pain", "herniated_disc", "serious_back_injury"},
    "shoulder":        {"shoulder_injury", "rotator_cuff"},
    "neck":            {"neck_injury", "cervical_spondylosis", "serious_neck_injury"},
    "hypertension":    {"high_blood_pressure", "hypertension"},
    "blood_pressure":  {"high_blood_pressure", "hypertension"},
    "heart":           {"heart_disease"},
    "glaucoma":        {"glaucoma"},
    "ankle":           {"ankle_injury"},
    "groin":           {"groin_injury"},
    "wrist":           {"wrist_injury"},
    # See the note in _MEDICAL_CONTRA_MAP: hip and hamstring were named on 29 poses
    # between them and reachable from nothing a user could type.
    "hip":             {"hip_injury"},
    "hamstring":       {"hamstring_injury"},
    "arthritis":       {"arthritis"},
}

# Current symptom → category boost
_SYMPTOM_CATEGORY_BOOST: dict[str, list[str]] = {
    "fatigue":       ["restorative", "supine"],
    "joint_pain":    ["restorative", "supine"],
    "anxiety":       ["restorative", "forward_fold"],
    "stress":        ["restorative", "forward_fold"],
    "bloating":      ["twist", "forward_fold"],
    "constipation":  ["twist", "forward_fold"],
    "insomnia":      ["restorative", "supine"],
    "back_pain":     ["prone", "restorative"],
    "back pain":     ["prone", "restorative"],
    "headache":      ["restorative", "forward_fold"],
    "pain":          ["restorative"],
    "stiffness":     ["prone", "seated"],
    "breathlessness":["restorative", "supine"],
    "palpitation":   ["restorative", "supine"],
    "nausea":        ["restorative", "supine"],
    "depression":    ["standing", "backbend"],
    "low_energy":    ["standing", "backbend"],
    # Canonical Vikriti symptom clusters — unified vocabulary shared by onboarding,
    # the weekly check-in, and the dosha quiz (the lay terms above are kept for
    # backward-compat with any symptoms stored before unification).
    "anxiety_worry":          ["restorative", "forward_fold"],
    "trouble_sleeping":       ["restorative", "supine"],
    "bloating_gas":           ["twist", "forward_fold"],
    "dry_skin_constipation":  ["twist", "forward_fold"],
    "joint_stiffness":        ["restorative", "supine"],
    "heartburn_acidity":      ["forward_fold", "restorative"],
    "irritability":           ["restorative", "forward_fold"],
    "skin_rashes":            ["restorative", "forward_fold"],
    "weight_gain":            ["standing", "backbend"],
    "congestion":             ["standing", "backbend"],
    "brain_fog":              ["standing", "backbend"],
    "morning_heaviness":      ["standing", "backbend"],
    "coated_tongue_ama":      ["twist", "forward_fold"],
}


def _build_contra_set(user_profile: dict, age_group: str = "adult") -> set:
    contra = set()

    for inj in (user_profile.get("injuries_or_limitations") or []):
        key = inj.lower()
        for k, tags in _INJURY_CONTRA_MAP.items():
            if k in key:
                contra.update(tags)

    for cond in (user_profile.get("medical_history") or []):
        key = cond.lower()
        for k, tags in _MEDICAL_CONTRA_MAP.items():
            if k in key:
                contra.update(tags)

    # Senior: block inversions and high-risk categories
    if age_group == "senior":
        contra.update(_AGE_SENIOR_CONTRA)

    return contra


def _build_risk_set(user_profile: dict, age_group: str = "adult") -> set:
    """Pose mechanisms this user must avoid, derived from conditions and injuries."""
    risks: set[str] = set()

    for cond in (user_profile.get("medical_history") or []):
        key = str(cond).lower()
        for k, tags in _CONDITION_RISK_TAGS.items():
            if k in key:
                risks.update(tags)

    for inj in (user_profile.get("injuries_or_limitations") or []):
        key = str(inj).lower()
        for k, tags in _INJURY_RISK_TAGS.items():
            if k in key:
                risks.update(tags)

    # Falls are the dominant injury mechanism over 60, and bone density is
    # already declining — the two risks that most warrant a blanket exclusion.
    if age_group == "senior":
        risks.update({"fall_risk", "intracranial_pressure", "neck_load"})

    return risks


# ── Ritucharya seasonal yoga mode ────────────────────────────────────────────

_RITUCHARYA_YOGA = {
    "vasanta":  {"boost_cat": ["standing", "balancing", "inversion"], "boost_score": 2,
                 "note": "Spring / Kapha season — vigorous, warming, and stimulating sequences best."},
    "grishma":  {"boost_cat": ["restorative", "forward_fold", "supine"], "boost_score": 2,
                 "note": "Summer / Pitta season — cooling, surrendering poses; avoid backbends at peak heat."},
    "varsha":   {"boost_cat": ["standing", "balancing", "twist"], "boost_score": 2,
                 "note": "Monsoon / Vata season — grounding, stabilising sequences; avoid deep inversions."},
    "sharad":   {"boost_cat": ["forward_fold", "twist", "restorative"], "boost_score": 2,
                 "note": "Autumn / Pitta releasing season — cooling twists and forward folds."},
    "hemanta":  {"boost_cat": ["backbend", "standing", "prone"], "boost_score": 2,
                 "note": "Early winter / Kapha season — warming backbends and energising flows."},
    "shishira": {"boost_cat": ["backbend", "standing", "prone"], "boost_score": 2,
                 "note": "Late winter / Vata + Kapha season — warming, grounding, deeply nourishing."},
}


def _get_season_boost(season_str) -> dict:
    if not season_str:
        return {}
    s = str(season_str).lower()
    for key, val in _RITUCHARYA_YOGA.items():
        if key in s:
            return val
    return {}


# ── Main pose filter + scoring ────────────────────────────────────────────────

def _pool_narrowing_reasons(user_profile: dict, yoga_prefs: dict) -> list[str]:
    """Which of the practitioner's own facts actually shrank the pose pool.

    `filter_poses` narrows on four independent axes — conditions and injuries,
    age, pregnancy, and experience level — but the notice explaining a thin plan
    named health conditions unconditionally. A healthy 70-year-old was told the
    app had ruled poses out for their "health conditions" when their age did it,
    which is the same fault the pranayama exclusions carried until `b0232ef`
    gave age its own reason. Reported in the order the filter applies them.
    """
    reasons = []
    if user_profile.get("medical_history"):
        reasons.append("your health conditions")
    if user_profile.get("injuries_or_limitations"):
        reasons.append("the injuries you told us about")
    if _get_age_group(user_profile.get("age")) in ("senior", "youth"):
        reasons.append("your age")
    if _pregnancy_state(user_profile)[0]:
        reasons.append("pregnancy")
    # Level narrows every pool, so it is only worth naming when nothing else
    # did — otherwise it reads as a safety restriction rather than a starting
    # point, and unlike the others it resolves on its own as the weeks unlock.
    if not reasons:
        exp = yoga_prefs.get("yoga_experience", "beginner")
        reasons.append("the level you are practising at"
                       if exp in ("none", "beginner") else "your profile")
    return reasons


def _join_reasons(reasons: list[str]) -> str:
    if len(reasons) == 1:
        return reasons[0]
    return ", ".join(reasons[:-1]) + f" and {reasons[-1]}"


def filter_poses(user_profile, yoga_prefs, poses, max_allowed_levels=None, protocol_map=None,
                 adjustment: "WeekAdjustment | None" = None, recent_pose_ids=None):
    if protocol_map is None:
        protocol_map = _PROTOCOL_MAP
    adjustment = adjustment or WeekAdjustment()
    # Poses seen in the weeks already generated. Not excluded — with a filtered
    # pool there may be nothing else to give — just pushed down the ranking so a
    # four-week plan does not keep serving the same twelve poses.
    recent_pose_ids = set(recent_pose_ids or ())

    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"

    # Base allowed levels — may be expanded by max_allowed_levels for progressive week unlock
    base_levels = level_map.get(user_exp, ["beginner"])
    allowed_levels = max_allowed_levels if max_allowed_levels else base_levels

    age = user_profile.get("age")
    age_group = _get_age_group(age)

    # Senior: hard cap at beginner regardless
    if age_group == "senior":
        allowed_levels = ["beginner"]
    elif age_group == "youth":
        allowed_levels = [l for l in allowed_levels if l != "advanced"]

    is_pregnant, _is_nursing, trimester = _pregnancy_state(user_profile)
    contra_tags = _build_contra_set(user_profile, age_group)
    risk_tags = _build_risk_set(user_profile, age_group)
    if is_pregnant:
        risk_tags |= _TRIMESTER_RISK_TAGS[trimester]
    blocked_categories = _TRIMESTER_BLOCKED_CATEGORIES[trimester] if is_pregnant else set()
    user_conditions = set(c.lower() for c in (user_profile.get("medical_history") or []))

    # Gender — for filtering female-only protocol boosts
    gender = (user_profile.get("gender") or "").lower()

    # Vikriti scoring (what needs correcting now), fall back to Prakriti
    vikriti = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha", "vata")
    vikriti_sec = user_profile.get("vikriti_secondary")
    yoga_goal = yoga_prefs.get("yoga_goal", "flexibility")

    # Profile signal flags
    stress_level  = (user_profile.get("stress_level") or "").lower()
    sleep_quality = (user_profile.get("sleep_quality") or "").lower()
    agni_type     = (user_profile.get("agni_type") or "").lower()
    ama_indicator = (user_profile.get("ama_indicator") or "").lower()
    ojas_level    = (user_profile.get("ojas_level") or "").lower()
    bmi_category  = (user_profile.get("bmi_category") or "").lower()

    # Current symptoms → category boosts
    raw_symptoms = user_profile.get("current_symptoms") or []
    symptom_keys = set(s.lower() for s in raw_symptoms)

    # Seasonal boost config
    season_cfg = _get_season_boost(user_profile.get("current_season"))

    # Protocol priority + AVOID pose IDs for this user's conditions. avoid_pose_ids
    # comes from dynamic (LLM) protocols for rare conditions — validated to real
    # poses — giving rare diseases pose-level contraindication filtering, not just
    # the static tags. Avoid always wins over priority (safety).
    protocol_priority_ids: set[str] = set()
    protocol_avoid_ids: set[str] = set()
    for cond in user_conditions:
        if cond in _FEMALE_ONLY_PROTOCOLS and gender in ("male", "m"):
            continue
        proto = protocol_map.get(cond)
        if proto:
            protocol_priority_ids.update(proto.get("priority_pose_ids", []))
            protocol_avoid_ids.update(proto.get("avoid_pose_ids", []))
    protocol_priority_ids -= protocol_avoid_ids

    scored = []
    for pose in poses:
        if pose.get("level", "intermediate") not in allowed_levels:
            continue
        if is_pregnant:
            if not pose.get("pregnancy_safe", True):
                continue
            if pose.get("category") in blocked_categories:
                continue
            # 28 poses carry a `pregnancy_third_trimester` tag that nothing has
            # ever read — the engine only consulted the pregnancy_safe boolean.
            pose_preg_tags = set(pose.get("contraindications", []))
            if "pregnancy" in pose_preg_tags:
                continue
            if trimester == 3 and "pregnancy_third_trimester" in pose_preg_tags:
                continue
        # Condition-specific pose contraindication (dynamic protocol) — hard exclude.
        if pose.get("id", "") in protocol_avoid_ids:
            continue
        # Poses the user asked to drop after practising them. Their word on what
        # hurt outranks the engine's scoring.
        if pose.get("id", "") in adjustment.excluded_pose_ids:
            continue

        pose_contra = set(pose.get("contraindications", [])) | set(pose.get("medical_conditions_contraindicated", []))
        if contra_tags.intersection(pose_contra):
            continue
        # Mechanism-level exclusion: what this pose does to the body, against
        # what this user's conditions cannot tolerate.
        if risk_tags.intersection(pose.get("risk_tags", [])):
            continue

        score = 0
        cat = pose.get("category", "standing")
        pose_id = pose.get("id", "")

        # ── Dosha scoring (primary + secondary) ──
        d_val = pose.get("dosha_balance", {}).get(vikriti, "neutral")
        if d_val == "balances":    score += 3
        elif d_val == "neutral":   score += 1
        elif d_val == "aggravates": score -= 2

        if vikriti_sec and vikriti_sec != vikriti:
            d_sec = pose.get("dosha_balance", {}).get(vikriti_sec, "neutral")
            if d_sec == "balances":    score += 1
            elif d_sec == "aggravates": score -= 1

        # ── Goal alignment ──
        if yoga_goal in pose.get("goals", []):
            score += 2

        # ── Medical condition benefit boost ──
        pose_beneficial = set(pose.get("medical_conditions_beneficial", []))
        matching_conditions = user_conditions.intersection(pose_beneficial)
        score += len(matching_conditions) * 3

        # ── Protocol priority — SVYASA-validated for this condition ──
        if pose_id in protocol_priority_ids:
            score += 8

        # ── Seasonal Ritucharya boost ──
        if season_cfg and cat in season_cfg.get("boost_cat", []):
            score += season_cfg["boost_score"]

        # ── Stress level — boost calming categories ──
        if stress_level in ("high", "severe"):
            if cat in ("restorative", "forward_fold"):
                score += 2
            if stress_level == "severe" and cat == "restorative":
                score += 1

        # ── Sleep quality — boost insomnia-beneficial poses ──
        if sleep_quality in ("poor", "fair"):
            if "insomnia" in pose_beneficial:
                score += 2

        # ── Agni type — manda (sluggish): boost digestive stimulators ──
        if agni_type in ("manda", "sama_manda", "vishama"):
            if cat in ("twist", "forward_fold"):
                score += 2

        # ── Ama indicator — boost detox categories ──
        if ama_indicator in ("moderate", "high"):
            if cat in ("twist", "inversion"):
                score += 1

        # ── Ojas level — low ojas: prioritise restorative ──
        if ojas_level == "low":
            if cat in ("restorative", "supine"):
                score += 2

        # ── BMI / fitness level — boost standing for overweight; reduce prone backbends ──
        if bmi_category in ("obese", "overweight"):
            if cat == "standing":
                score += 1
            if cat == "prone" and pose.get("level") == "intermediate":
                score -= 1

        # ── Current symptoms → targeted category boosts ──
        for sym, boost_cats in _SYMPTOM_CATEGORY_BOOST.items():
            if sym in symptom_keys and cat in boost_cats:
                score += 1
                break  # only one boost per pose per symptom group

        # ── Age group — senior: boost gentle, seated; youth: boost energetic ──
        if age_group == "senior":
            if cat in ("restorative", "seated", "supine"):
                score += 1
        elif age_group == "youth":
            if cat in ("standing", "balancing"):
                score += 1

        # ── Feedback: bias toward restorative work when the practice has been
        # too hard or has been leaving the user drained ──
        if adjustment.restorative_bias and cat in ("restorative", "supine", "forward_fold"):
            score += adjustment.restorative_bias
        if adjustment.restorative_bias and cat in ("inversion", "backbend", "balancing"):
            score -= adjustment.restorative_bias

        # ── Variety: poses already used in this plan rank lower ──
        if pose_id in recent_pose_ids:
            score -= 3

        # Always keep Savasana / Corpse in pool
        name = pose.get("english_name", "").lower()
        if "corpse" in name or "savasana" in name:
            score += 50

        scored.append((score, pose))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:80]]


# ── Pranayama selection ───────────────────────────────────────────────────────

# Hard, condition-independent contraindication gate for forceful / breath-holding
# pranayama. This does NOT depend on protocol_map coverage or on the KB entry
# having its `contraindications` populated — it is defence-in-depth so a forceful
# breath (Kapalabhati / Bhastrika / Kumbhaka) can never reach a hypertensive,
# cardiac, epileptic, glaucoma, hernia, or pregnant user. Over-blocking here is
# acceptable; a missed block is not.
_FORCEFUL_PRANAYAMA_CONTRA: dict[str, set[str]] = {
    # Kapalabhati (skull shining) & Bhastrika (bellows) — rapid forceful exhalation
    "skull_shining":   {"hypertension", "high_blood_pressure", "heart", "cardiac",
                        "epilep", "seizure", "hernia", "glaucoma", "retina",
                        "vertigo", "pregnan", "ulcer", "recent_surgery", "stroke"},
    "bellows_breath":  {"hypertension", "high_blood_pressure", "heart", "cardiac",
                        "epilep", "seizure", "hernia", "glaucoma", "retina",
                        "vertigo", "pregnan", "ulcer", "recent_surgery", "stroke"},
    "fire_essence":    {"hypertension", "high_blood_pressure", "heart", "cardiac",
                        "epilep", "seizure", "hernia", "pregnan", "stroke"},
    # Surya Bhedana (right nostril) — strongly heating
    "right_nostril":   {"hypertension", "high_blood_pressure", "heart", "cardiac",
                        "epilep", "seizure", "pregnan"},
    # Kumbhaka (breath retention) & Bandha (locks)
    "breath_retention": {"hypertension", "high_blood_pressure", "heart", "cardiac",
                         "epilep", "seizure", "pregnan", "glaucoma", "retina", "stroke"},
    "root_lock_breath": {"hypertension", "high_blood_pressure", "heart", "cardiac",
                         "pregnan", "hernia"},
    "swooning_breath":  {"hypertension", "high_blood_pressure", "heart", "cardiac",
                         "epilep", "seizure", "pregnan", "vertigo", "glaucoma"},
    "unequal_breathing": {"hypertension", "high_blood_pressure", "heart", "cardiac"},
}

# Defence-in-depth gate for cooling / sedating pranayama (Sitali, Sitkari,
# Chandra Bhedana, Sheetali Kumbhaka). These are calming and Pitta-reducing but
# are classically contraindicated in low blood pressure (further drops it),
# asthma / respiratory congestion (cold air aggravates), and cold/Kapha
# conditions. Like the forceful map above, this is independent of whether the KB
# entry's `contraindications` field is populated — over-blocking is acceptable.
_COOLING_PRANAYAMA_CONTRA: dict[str, set[str]] = {
    "cooling_breath":   {"low_blood_pressure", "hypotension", "low_bp",
                        "asthma", "respiratory", "chronic_cough"},
    "hissing_breath":   {"low_blood_pressure", "hypotension", "low_bp",
                        "asthma", "respiratory", "chronic_cough"},
    # Chandra Bhedana — lunar/sedating: also avoid in clinical depression
    "left_nostril":     {"low_blood_pressure", "hypotension", "low_bp",
                        "asthma", "respiratory", "depression"},
    # Sheetali Kumbhaka — cooling PLUS breath retention + chin lock, so it also
    # carries the Kumbhaka cardiac/intracranial-pressure contraindications.
    "extended_cooling": {"low_blood_pressure", "hypotension", "low_bp",
                        "asthma", "respiratory", "chronic_cough",
                        "hypertension", "high_blood_pressure", "heart", "cardiac",
                        "glaucoma", "retina", "epilep", "seizure", "pregnan"},
}


def _pranayama_hard_blocked(pr: dict, user_conditions: set[str]) -> bool:
    """True if this pranayama is contraindicated for any of the user's conditions.

    Checks BOTH the KB entry's own `contraindications` field AND the hardcoded
    forceful- and cooling-pranayama safety maps. Matching is substring-based in
    both directions so 'high_blood_pressure' matches 'hypertension'-style tags
    and vice versa.
    """
    if not user_conditions:
        return False
    pr_id = pr.get("id", "")
    contra_tokens: set[str] = set(_FORCEFUL_PRANAYAMA_CONTRA.get(pr_id, set()))
    contra_tokens |= set(_COOLING_PRANAYAMA_CONTRA.get(pr_id, set()))
    for c in (pr.get("contraindications") or []) + (pr.get("medical_conditions_contraindicated") or []):
        contra_tokens.add(str(c).lower())
    if not contra_tokens:
        return False
    for tok in contra_tokens:
        if not tok:
            continue
        for uc in user_conditions:
            if tok in uc or uc in tok:
                return True
    return False


# The two techniques the practice is built around. Anulom Vilom is the spine of
# any pranayama practice — no contraindications, safe in pregnancy, good at any
# hour — so it is boosted hard enough to be near-certain.
#
# Kapalabhati is boosted the same way but is a genuinely different proposition:
# it is a forceful cleansing kriya, morning-only, unsafe in pregnancy, and
# contraindicated for hypertension, heart disease, glaucoma, epilepsy, hernia,
# peptic ulcer and recent surgery. The boost is applied strictly AFTER every
# gate below, so it changes the ORDER of safe techniques and never the set. A
# preference must not be able to promote a technique past a contraindication —
# and when it is filtered out the plan says so rather than quietly substituting.
_EMPHASIS_PRANAYAMA = {"alternate_nostril": 10, "skull_shining": 9}


def _pranayama_gates(user_profile, yoga_prefs, protocol_map=None):
    """Everything that can rule a technique out, as one reusable predicate.

    Extracted so the prescribed daily stack and the scorer cannot drift apart:
    a technique that is unsafe for this practitioner has to be unsafe on both
    paths, and the prescription must not become a way around a gate.
    """
    if protocol_map is None:
        protocol_map = _PROTOCOL_MAP

    is_pregnant = _pregnancy_state(user_profile)[0]
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"
    age_group = _get_age_group(user_profile.get("age"))
    gender = (user_profile.get("gender") or "").lower()
    time_of_day = (yoga_prefs.get("time_of_day_preference") or "morning").lower()
    user_conditions = set(c.lower() for c in (user_profile.get("medical_history") or []))

    allowed_levels = {
        "beginner":     {"beginner"},
        "intermediate": {"beginner", "intermediate"},
        "advanced":     {"beginner", "intermediate", "advanced"},
    }.get(user_exp, {"beginner"})

    # Priorities are ORDERED — a protocol lists its recommendations best-first,
    # and the third slot takes the first one that is not already prescribed, so
    # losing the order would mean picking an arbitrary member of the set.
    avoid_ids: set[str] = set()
    priority_ids: list[str] = []
    for cond in sorted(user_conditions):
        if cond in _FEMALE_ONLY_PROTOCOLS and gender in ("male", "m"):
            continue
        proto = protocol_map.get(cond)
        if proto:
            for pid in proto.get("priority_pranayama_ids", []):
                if pid not in priority_ids:
                    priority_ids.append(pid)
            avoid_ids.update(proto.get("avoid_pranayama_ids", []))

    # See the note in select_pranayama: contraindications, KB level and age are
    # three independent axes.
    # Bhastrika belongs with its siblings here, not one line down. It was
    # excluded for youth only, so a 70-year-old with chronic fatigue was
    # prescribed it — while Kapalabhati, a *less* forceful practice, was
    # correctly withheld from the same profile. Bellows breath is rapid forced
    # inhalation AND exhalation; the reason given below for the other two
    # applies to it word for word.
    #
    # Age exclusions are kept in their OWN set. Folding them into `avoid_ids`
    # left the reason to be guessed from whether the practitioner happened to
    # have any condition at all — so a 70-year-old with chronic fatigue was told
    # Bhastrika was "contraindicated for your health conditions" when their age
    # was what withheld it. Three independent axes, three independent answers.
    age_avoid_ids = set()
    if age_group in ("senior", "youth"):
        age_avoid_ids.update({"breath_retention", "skull_shining",
                              "fire_essence", "bellows_breath"})
    if age_group == "youth":
        age_avoid_ids.add("root_lock_breath")

    def allowed(pr: dict) -> str | None:
        """None if the technique may be used, else a short reason it may not."""
        if is_pregnant and not pr.get("pregnancy_safe", True):
            return "pregnancy"
        if _pranayama_hard_blocked(pr, user_conditions):
            return "condition"
        if pr.get("id", "") in age_avoid_ids:
            return "age"
        if pr.get("id", "") in avoid_ids:
            return "condition"
        if pr.get("level", "beginner") not in allowed_levels:
            return "level"
        if time_of_day == "evening" and pr.get("best_time") == "anytime":
            return None
        if time_of_day == "evening" and pr.get("best_time") == "morning":
            return "time_of_day"
        return None

    return allowed, priority_ids, avoid_ids | age_avoid_ids


def select_pranayama(user_profile, yoga_prefs, pranayama_db, count=3, protocol_map=None):
    if protocol_map is None:
        protocol_map = _PROTOCOL_MAP

    is_pregnant = _pregnancy_state(user_profile)[0]
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"

    age_group = _get_age_group(user_profile.get("age"))
    gender = (user_profile.get("gender") or "").lower()
    time_of_day = (yoga_prefs.get("time_of_day_preference") or "morning").lower()

    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    allowed_levels = level_map.get(user_exp, ["beginner"])
    vikriti = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha", "vata")
    yoga_goal = yoga_prefs.get("yoga_goal", "stress_relief")
    user_conditions = set(c.lower() for c in (user_profile.get("medical_history") or []))

    # Profile signals for pranayama targeting
    stress_level  = (user_profile.get("stress_level") or "").lower()
    sleep_quality = (user_profile.get("sleep_quality") or "").lower()
    agni_type     = (user_profile.get("agni_type") or "").lower()
    ojas_level    = (user_profile.get("ojas_level") or "").lower()

    # Build protocol pranayama priorities and hard avoids
    protocol_priority_ids: set[str] = set()
    protocol_avoid_ids: set[str] = set()
    for cond in user_conditions:
        if cond in _FEMALE_ONLY_PROTOCOLS and gender in ("male", "m"):
            continue
        proto = protocol_map.get(cond)
        if proto:
            protocol_priority_ids.update(proto.get("priority_pranayama_ids", []))
            protocol_avoid_ids.update(proto.get("avoid_pranayama_ids", []))

    # Age-based breath restrictions.
    #
    # The forceful kriyas are listed explicitly for 60+ and under-18 rather than
    # relying on their KB `level`. Kapalabhati used to be level:intermediate,
    # which shielded beginners of every age by accident — but an *experienced*
    # 70-year-old was already being served it, and when the level was lowered to
    # beginner (2026-08-14, user decision) that gap widened to everyone. Rapid
    # abdominal pumping raises intra-abdominal and intra-thoracic pressure, which
    # is the wrong thing to do unsupervised at either end of the age range.
    # Contraindications and level are different axes; age is a third.
    # Bhastrika sits with them for the same reason — see `_pranayama_gates`.
    if age_group in ("senior", "youth"):
        protocol_avoid_ids.update({"breath_retention", "skull_shining",
                                   "fire_essence", "bellows_breath"})
    if age_group == "youth":
        protocol_avoid_ids.update({"root_lock_breath"})

    scored = []
    for pr in pranayama_db:
        if is_pregnant and not pr.get("pregnancy_safe", True):
            continue
        # Hard medical contraindication gate (defence-in-depth, condition-independent)
        if _pranayama_hard_blocked(pr, user_conditions):
            continue
        if pr.get("level", "beginner") not in allowed_levels:
            continue

        pr_id = pr.get("id", "")

        # Hard avoid
        if pr_id in protocol_avoid_ids:
            continue

        # Time-of-day filter: skip morning-only energising pranayama for evening sessions
        best_time = pr.get("best_time", "anytime")
        if time_of_day == "evening" and best_time == "morning":
            continue

        # Every safety gate above has already run. This only reorders survivors.
        score = _EMPHASIS_PRANAYAMA.get(pr_id, 0)

        # Protocol priority
        if pr_id in protocol_priority_ids:
            score += 8

        # Dosha effect
        de = pr.get("dosha_effect", {}).get(vikriti, "neutral")
        if de == "balances":    score += 2
        elif de == "neutral":   score += 1
        elif de == "aggravates": score -= 2

        # Goal alignment
        ptype = pr.get("type", "balancing")
        if yoga_goal == "stress_relief" and ptype in ("balancing", "grounding"): score += 2
        if yoga_goal in ("energy", "strength") and ptype == "energizing":        score += 2
        if yoga_goal == "healing" and ptype == "balancing":                       score += 2
        if yoga_goal == "flexibility" and ptype == "grounding":                   score += 1
        if yoga_goal == "spiritual" and ptype == "balancing":                     score += 2

        # Profile signal boosts for pranayama
        if stress_level in ("high", "severe") and ptype in ("balancing", "grounding"):
            score += 2
        if sleep_quality in ("poor", "fair") and pr_id in ("left_nostril", "humming_bee", "three_part_breath"):
            score += 2
        if agni_type in ("manda", "vishama") and pr_id in ("skull_shining", "bellows_breath", "right_nostril"):
            score += 2
        if ojas_level == "low" and pr_id in ("humming_bee", "three_part_breath", "alternate_nostril"):
            score += 2

        scored.append((score, pr))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:count]]


# ── Session time budget ───────────────────────────────────────────────────────
# A session used to be a fixed pose count regardless of the time asked for, and
# the counts were far too low: a 30-minute request produced 3+5+2 poses at ~30
# seconds each — under 9 minutes of content against a 30-minute promise. Sections
# are now filled against a real second-by-second budget derived from the
# requested duration, so the plan delivers the practice length the user chose.

# ── Fixed session structure (user decision 2026-08-15) ───────────────────────
# Surya Namaskar, the warm-up, the cool-down and savasana are now FIXED slots,
# not shares of whatever is left over. The practitioner asked for a session with
# a shape they can recognise from one day to the next: five minutes of sun
# salutations, five of warm-up, the asana practice, a short cool-down, two
# minutes of savasana. Everything not listed here — the main sequence — takes
# the remainder, so lengthening the session lengthens the practice rather than
# inflating its bookends.
#
# The thirty-minute tier is scaled to 3/3/3, not held at 5/5/6. At half an hour
# the prescribed breathwork already takes twelve minutes; a full-size opening
# and closing on top would have left six minutes of asana in a yoga session.
#
# (seconds) — keys are the upper bound of the tier they describe.
_SESSION_STRUCTURE = [
    # Savasana is 60s at this tier, not the 120 the longer two get (user decision
    # 2026-08-17). A half-hour session cannot spend a fifteenth of itself lying
    # still and still deliver a practice; the minute goes to asana.
    (30, {"surya_namaskar": 180, "warmup": 180, "cooldown": 180, "savasana": 60}),
    (45, {"surya_namaskar": 300, "warmup": 300, "cooldown": 300, "savasana": 120}),
    (999, {"surya_namaskar": 300, "warmup": 300, "cooldown": 360, "savasana": 120}),
]


def session_structure(mins: int) -> dict:
    """Fixed slot lengths, in seconds, for a session of `mins` minutes.

    Preferences stored before the three-tier UI landed can still be anything
    from 15 to 90 (`preferences_schema`), so anything below the 30-minute tier
    is scaled down proportionally rather than being served a structure that
    does not fit inside it.
    """
    for upper, slots in _SESSION_STRUCTURE:
        if mins <= upper:
            if mins >= 30:
                return dict(slots)
            # Savasana is a floor, not a share: one minute of stillness is the
            # shortest that is worth lying down for, and the 30-minute tier is
            # already at that floor, so a shorter legacy session keeps it whole.
            scale = mins / 30
            return {k: (v if k == "savasana" else max(60, int(v * scale)))
                    for k, v in slots.items()}
    return dict(_SESSION_STRUCTURE[-1][1])


# How the *remaining* asana budget divides between the main sequence and any
# cool-down time the fixed slot above could not absorb. The warm-up and cooldown
# no longer draw shares — they are priced by `session_structure` — so this is
# only consulted where a legacy caller passes no structure at all.
_SECTION_SPLIT = {"warmup": 0.22, "main": 0.55, "cooldown": 0.23}

# Share of EACH section's budget that stays the same all week; the rest rotates
# per day. This is the consistency dial for the whole plan.
#
# At 0.65, and with warmup and cooldown still shuffled daily, roughly half of
# every session changed overnight — 44-46 distinct poses across a week and only
# about six shared by Monday through Friday. That is a different class every
# day, not a practice. A practice is the same sequence you get better at, with
# an occasional new pose; the point of repetition is that the poses stop needing
# to be read. Raising this to 0.85 and applying it to all three sections leaves
# one or two poses moving per day.
#
# Lower it for more variety, raise it toward 1.0 for a fixed week.
_CORE_SHARE = 0.92

# How far past its budget a section may land to avoid stopping short.
_MAX_SECTION_OVERSHOOT = 0.12

# Seated meditation scales with session length rather than sitting at a fixed
# 7 minutes, which would eat a third of a short practice. The savasana column is
# HISTORICAL — savasana is now a flat 2 minutes from `session_structure`, and
# this records what it scaled to before that. `_closing_budget` reads only the
# dharana column, which still needs its scaling if `_INCLUDE_DHARANA` is ever
# turned back on.
# (minutes_available_upper_bound, savasana_seconds, dharana_seconds)
_CLOSING_BUDGET = [
    (15,  120, 120),
    (20,  180, 180),
    (30,  240, 300),
    (45,  300, 420),
    (999, 420, 600),
]


# Surya Namaskar, pranayama, meditation and final relaxation together may not
# take more than this share of a session — the rest belongs to asana.
#
# Raised from 0.55 to 0.60 when the slots became fixed. At the 30-minute tier
# the intended structure is 3 + 12 + 2 = 17 of 30 minutes, which is 0.567: the
# old ceiling trimmed a structure that was deliberate rather than an overrun,
# and because rounds are whole numbers a 10% trim cost Surya Namaskar half its
# slot (3.0 minutes down to 1.4). It still binds where it was meant to — a
# legacy 15-minute preference wants 0.63 — so a short session cannot become
# breathwork with a token asana practice attached.
_MAX_FIXED_BLOCK_SHARE = 0.60

# ── Pranayama policy ──────────────────────────────────────────────────────────
# Every session gets real breathwork: at least five minutes, at most ten.
#
# `pranayama.json` rates every technique 3/5/10 minutes by experience, which left
# a beginner on three — enough to name the technique, not enough to practise it,
# and pranayama is the part of the practice that carries over into the rest of
# the day. The floor is a policy about the session, not a claim about the
# technique, so it lives here rather than being edited into the KB.
#
# The share ceiling keeps the floor from swallowing a short session: at the 30 /
# 45 / 60 tiers it never binds, but a legacy 15-minute preference would otherwise
# spend a third of itself breathing.
_PRANAYAMA_MIN_MINUTES = 5
_PRANAYAMA_MAX_MINUTES = 10
_PRANAYAMA_MAX_SHARE = 0.25

# ── The prescribed daily stack ────────────────────────────────────────────────
# The same three techniques every day, in this order (user decision 2026-08-14).
# This replaced both the three-technique rotation and the two-days-a-week focus
# arrangement — every day now carries more breathwork than the old focus days
# did, so a separate focus day had nothing left to add.
#
# Bhramari is `required`: it is the one the practitioner asked for
# unconditionally, so it is filled first and never trimmed away. The other two
# were asked for "if possible", which is the rule the budget actually needs —
# see `_PRESCRIPTION_MAX_SHARE`.
#
# The third entry is a SLOT, not a technique. It is the only one that moves, and
# it is filled in this order:
#
#   1. the top-ranked breath a condition protocol recommends, when the
#      practitioner has a condition and that recommendation is not already one
#      of the two prescribed above it;
#   2. otherwise the dosha default below.
#
# Protocol beats dosha because a diagnosed condition is more specific than a
# constitutional tendency, which is how the rest of the engine already resolves
# the two. This costs less than it sounds: Bhramari and Anulom Vilom already head
# the priority list of most of the thirty protocols that carry one, so the base
# prescription IS the clinical recommendation for most people. What this mostly
# fixes is the practitioner whose protocol rules Kapalabhati out — hypertension,
# insomnia, migraine, PTSD and a dozen more — who until now simply lost the third
# slot. It becomes the breath their condition actually calls for.
_DAILY_PRANAYAMA = [
    {"id": "humming_bee",       "required": True},
    {"id": "alternate_nostril"},
    {"slot": "third"},
]

# Minutes each slot asks for, by session tier (user decision 2026-08-15). The
# hour has room for more breathwork than the three-quarter hour, and the growth
# goes to Bhramari and Anulom Vilom — NOT to the third slot.
#
# The third slot is usually Kapalabhati, and `pranayama.json` rates it 3/5/10 by
# experience. A pumping kriya held past its rating is a different practice, which
# is the whole reason `_FORCEFUL_PRANAYAMA` is exempt from the minutes floor; it
# would be incoherent to exempt it from a floor and then push it past its
# ceiling. Bhramari and Anulom Vilom are calming, rated 10 at advanced, and have
# no such limit — so they are where an hour's extra five minutes belong.
#
# The 30-minute tier asks for 2/4/3 = 9 minutes (user decision 2026-08-17). It
# used to ask 5/5/5 and let the `_PRESCRIPTION_MAX_SHARE` budget trim it to
# 5/4/3, but twelve minutes of breath in a half-hour session left the main
# sequence at seven — thinner than the warm-up and Surya Namaskar together. The
# three minutes come off Bhramari, which is the slot with the most to give: it
# asks for eight at the hour, so two is a real dose at the short tier rather
# than a token one. The freed minutes go to asana, not to the other breaths.
_PRESCRIPTION_MINUTES = [
    (30,  {"humming_bee": 2, "alternate_nostril": 4, "third": 3}),
    (45,  {"humming_bee": 5, "alternate_nostril": 5, "third": 5}),
    (999, {"humming_bee": 8, "alternate_nostril": 7, "third": 5}),
]


# The same tier totals, redivided when a Pitta earns a cooling chaser (see
# `_cooling_chaser_id`). The chaser is paid for out of the tier's own breath
# budget rather than added to it — 15 and 20 minutes are the tier's decision and
# a fourth breath is not a reason to spend longer breathing. 30 is None: nine
# minutes split four ways is under three minutes each, which is below what any
# of them is rated for, so the short tier serves the disease breath alone.
_PRESCRIPTION_MINUTES_WITH_CHASER = [
    (30,  None),
    (45,  {"humming_bee": 4, "alternate_nostril": 4, "third": 4, "cooling_chaser": 3}),
    (999, {"humming_bee": 7, "alternate_nostril": 5, "third": 5, "cooling_chaser": 3}),
]


def _prescription_minutes(session_minutes: int, with_chaser: bool = False) -> dict | None:
    table = _PRESCRIPTION_MINUTES_WITH_CHASER if with_chaser else _PRESCRIPTION_MINUTES
    for upper, asks in table:
        if session_minutes <= upper:
            return asks
    return table[-1][1]


def _slot_key(entry: dict) -> str:
    return entry.get("id") or entry.get("slot")

# Dosha default for the third slot, used when no protocol names one. Pitta gets
# cooling breaths instead of Kapalabhati, which is heating; both are prescribed,
# so they alternate by day rather than splitting the slot — two and a half
# minutes each is too short for either to do anything.
_THIRD_SLOT_BY_DOSHA = {
    "pitta": ["cooling_breath", "hissing_breath"],   # Sitali / Sitkari
    "_default": ["skull_shining"],                   # Kapalabhati
}

# Last resort for the third slot. Dirgha is beginner-level, has no
# contraindications and is safe in pregnancy, so it is the one breath almost
# nobody is gated out of.
_THIRD_SLOT_FALLBACK = ["three_part_breath"]

# The stack may not take more than this share of a session. At 45 and 60 minutes
# all fifteen minutes fit comfortably; at 30 they do not, and something has to
# give — the alternative is a half-hour practice with nine minutes of asana in
# it. Bhramari is protected, so what gives is the tail of the stack.
_PRESCRIPTION_MAX_SHARE = 0.40
_PRESCRIPTION_MIN_TECHNIQUE_MINUTES = 3


# Forceful practices, exempt from the minimum-minutes floor. Kapalabhati is a
# pumping kriya, not a breath to settle into: its KB dose is 3 minutes for a
# beginner and stretching that to five to satisfy a session-level policy pushes
# a technique past what it is rated for. The floor is about how much breathwork
# a SESSION contains, so a short forceful practice is topped up with a calming
# partner instead — which is also how it is taught, Kapalabhati followed by
# Anulom Vilom rather than done alone.
_FORCEFUL_PRANAYAMA = {"skull_shining", "bellows_breath", "fire_essence"}

# Heating breaths, refused for a Pitta constitution (user decision 2026-08-17).
# Pitta's dosha default is already the cooling pair, but a condition protocol
# outranks the constitution, and three protocols — diabetes, obesity, IBS — put
# Kapalabhati in the third slot of a practitioner whose whole plan is built to
# cool them down. Protocol precedence is right in general and is NOT reversed
# here: only the heating breaths are refused, so a Pitta asthmatic still gets
# the Ujjayi their protocol names, and hypertension still gets Chandra Bhedana
# (itself cooling). What they fall through to is Sitali/Sitkari.
#
# It is the forceful set plus Surya Bhedana: the right-nostril breath is the
# solar channel and heating by design, though it is not a pumping kriya.
_HEATING_PRANAYAMA = _FORCEFUL_PRANAYAMA | {"right_nostril"}


def _cooling_chaser_id(user_profile: dict, third: dict | None, day_num: int) -> str | None:
    """The cooling breath that follows a heating one, for a Pitta. Else None.

    A condition protocol outranks the constitution, so the third slot is never
    refused for being heating — three protocols (diabetes, obesity, depression)
    name nothing BUT heating breaths, and blocking them left a Pitta with no
    breath aimed at their disease at all. The constitution is answered by adding
    a breath rather than by withholding one: Kapalabhati followed by Sitali is
    how a heating kriya is classically taught anyway, and it is the only
    arrangement in which both the disease and the constitution are served.

    Vata and Kapha get no chaser — heat is what their prescription is for.
    """
    dosha = (user_profile.get("vikriti_dominant")
             or user_profile.get("dominant_dosha") or "").lower()
    if dosha != "pitta" or not third:
        return None
    if third.get("id") not in _HEATING_PRANAYAMA:
        return None
    cooling = _THIRD_SLOT_BY_DOSHA["pitta"]
    return cooling[(day_num - 1) % len(cooling)]


def pranayama_minutes(technique: dict, experience: str, session_minutes: int,
                      apply_floor: bool = True) -> int:
    """Minutes of breathwork for one technique, after the 5-10 minute policy."""
    durs = technique.get("duration_minutes", {})
    base = durs.get(experience, durs.get("beginner", 3))
    ceiling = max(1, int(session_minutes * _PRANAYAMA_MAX_SHARE))
    capped = min(base, _PRANAYAMA_MAX_MINUTES, ceiling)
    if not apply_floor or technique.get("id") in _FORCEFUL_PRANAYAMA:
        return int(capped)
    return int(max(min(_PRANAYAMA_MIN_MINUTES, ceiling), capped))


def _dosha_third_slot(user_profile: dict) -> list[str]:
    dosha = (user_profile.get("vikriti_dominant")
             or user_profile.get("dominant_dosha") or "vata").lower()
    return _THIRD_SLOT_BY_DOSHA.get(dosha, _THIRD_SLOT_BY_DOSHA["_default"])


def _third_slot_ids(user_profile: dict, priority_ids, already: set,
                    day_num: int) -> tuple[list, bool]:
    """Ordered candidates for the third slot, and whether a protocol led.

    A protocol recommendation the practitioner is already doing is no
    recommendation at all, so anything in `already` is skipped rather than
    counting as the protocol's answer.
    """
    from_protocol = [pid for pid in (priority_ids or []) if pid not in already]

    # Only the dosha default rotates, and only where a dosha names two. A
    # protocol names one breath, which then runs every day; and the fallback
    # must stay out of the rotation entirely — folding it in had Vata
    # alternating between Kapalabhati and Dirgha on odd and even days.
    default = _dosha_third_slot(user_profile)
    rotated = [default[(day_num - 1) % len(default)]] + default if default else []

    # Dirgha trails everything: beginner-level, no contraindications, safe in
    # pregnancy, so it is what stands between a heavily gated practitioner and a
    # two-breath session. A 70-year-old with obesity got nothing here — their
    # protocol wants Kapalabhati and their age forbids it.
    return from_protocol + rotated + _THIRD_SLOT_FALLBACK, bool(from_protocol)


def pranayama_day_plan(pranayama_db, user_profile, yoga_prefs, day_num: int,
                       session_minutes: int, protocol_map=None):
    """The prescribed stack for one day.

    Returns `([(technique, minutes)], [dropped], protocol_led_id_or_None)`.

    Filled in prescription order until the session's share is spent. Everything
    here still passes `_pranayama_gates`, so the prescription cannot serve a
    technique the practitioner's conditions, age or level rule out — it decides
    WHICH safe techniques run, never whether a gate applies.
    """
    by_id = {p.get("id"): p for p in pranayama_db}
    allowed, priority_ids, _avoid = _pranayama_gates(user_profile, yoga_prefs, protocol_map)
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    budget = max(_PRANAYAMA_MIN_MINUTES,
                 int(session_minutes * _PRESCRIPTION_MAX_SHARE))
    dropped = []

    # Resolve each slot to a safe technique first, so the time is shared out
    # only among the techniques that will actually be practised.
    resolved, protocol_led = [], None
    for entry in _DAILY_PRANAYAMA:
        if "slot" in entry:
            taken = {t.get("id") for _e, t in resolved}
            candidates, _from_protocol = _third_slot_ids(
                user_profile, priority_ids, taken, day_num)
        else:
            candidates = [entry["id"]]

        # Every candidate a gate turned down before the slot resolved is
        # reported, not just the ones that leave the slot empty. A succeeding
        # fallback is exactly the case where the substitution goes unmentioned:
        # a senior whose protocol asks for Bhastrika simply received Surya
        # Bhedana, with no word that the breath their condition names first had
        # been withheld. The same reasoning already applies to the dosha default
        # below; this extends it to the protocol's own ranking.
        chosen, blocked = None, []
        for pid in candidates:
            technique = by_id.get(pid)
            if technique is None:
                continue
            why = allowed(technique)
            if why is None:
                chosen = technique
                break
            blocked.append({"id": pid, "reason": why})
        # A slot that resolves reports what outranked the winner. A slot that
        # fails entirely reports only its first choice — the practitioner needs
        # one reason they lost the breath, not the whole rejected list.
        dropped.extend(blocked if chosen is not None else blocked[:1])
        if chosen is None:
            continue
        resolved.append((entry, chosen))
        if "slot" in entry:
            if chosen.get("id") in (priority_ids or []):
                protocol_led = chosen.get("id")
            # The practitioner asked for Kapalabhati (or, for Pitta, the cooling
            # pair) daily. When the slot lands on something else BECAUSE that
            # breath is gated, say so — the fallback succeeding is exactly the
            # case where the substitution would otherwise be silent.
            for pid in _dosha_third_slot(user_profile):
                if pid == chosen.get("id"):
                    continue
                blocked = by_id.get(pid)
                why = allowed(blocked) if blocked else None
                if why:
                    dropped.append({"id": pid, "reason": why})

    # A Pitta prescribed a heating breath by their condition gets a cooling one
    # after it, where the tier has room to pay for it out of its own budget.
    # This is appended AFTER the three slots resolve, so it can never displace
    # the disease breath — it only ever follows it.
    chaser_asks = None
    third = next((t for e, t in resolved if "slot" in e), None)
    chaser_id = _cooling_chaser_id(user_profile, third, day_num)
    if chaser_id and _prescription_minutes(session_minutes, with_chaser=True):
        chaser = by_id.get(chaser_id)
        why = allowed(chaser) if chaser else "unavailable"
        if chaser is not None and why is None:
            resolved.append(({"slot": "cooling_chaser"}, chaser))
            chaser_asks = True
        elif chaser is not None:
            dropped.append({"id": chaser_id, "reason": why})

    # The required technique takes its full ask; the rest share what is left.
    # Shortening beats dropping — at 30 minutes all three still fit as 2/4/3,
    # and 3 minutes of Kapalabhati is its own rated beginner dose anyway.
    asks = _prescription_minutes(session_minutes, with_chaser=bool(chaser_asks))

    def ask(entry):
        return asks[_slot_key(entry)]

    required = [(e, t) for e, t in resolved if e.get("required")]
    optional = [(e, t) for e, t in resolved if not e.get("required")]
    spent = sum(ask(e) for e, _ in required)
    room = max(budget - spent, 0)

    while optional and room < len(optional) * _PRESCRIPTION_MIN_TECHNIQUE_MINUTES:
        entry, technique = optional.pop()
        dropped.append({"id": technique["id"], "reason": "session_length"})

    shares = {}
    if optional:
        asked = sum(ask(e) for e, _ in optional)
        if asked <= room:
            shares = {id(t): ask(e) for e, t in optional}
        else:
            base, extra = divmod(room, len(optional))
            for idx, (_e, t) in enumerate(optional):
                shares[id(t)] = base + (1 if idx < extra else 0)

    plan = []
    for entry, technique in resolved:
        if entry.get("required"):
            plan.append((technique, ask(entry)))
        elif id(technique) in shares:
            plan.append((technique, shares[id(technique)]))
    # Only report a protocol-led third slot if it survived the budget trim.
    kept = {t.get("id") for t, _m in plan}
    return plan, dropped, (protocol_led if protocol_led in kept else None)


def _scale_surya_namaskar(sns: dict | None, scale: float) -> tuple[dict | None, int]:
    """Shrink a Surya Namaskar block to fit a short session, by dropping rounds."""
    if not sns or not sns.get("rounds"):
        return sns, 0
    rounds = max(1, int(sns["rounds"] * scale))
    if rounds == sns["rounds"]:
        return sns, int(sns.get("duration_minutes", 0) * 60)
    scaled = dict(sns)
    scaled["rounds"] = rounds
    per_step = sns.get("seconds_per_step", 5)
    seconds = rounds * 12 * per_step + (rounds - 1) * _SNS_INTER_ROUND_SECONDS
    scaled["duration_minutes"] = round(seconds / 60, 1)
    return scaled, seconds


# The seated meditation slot was removed from the session (user decision
# 2026-08-14) and its time went to the prescribed breathwork stack. `_DHARANA`
# below is kept — the techniques, instructions and classical citations are real
# work and the decision is a preference, not a correction — so restoring it is
# this one flag plus the `_CLOSING_BUDGET` column, which is still populated.
_INCLUDE_DHARANA = False


def _closing_budget(mins: int) -> tuple[int, int]:
    """(savasana_seconds, dharana_seconds) for a session of `mins` minutes.

    Savasana no longer scales with experience — it is two minutes at the 45 and
    60 tiers and one at 30, the same for every level, so it comes from
    `session_structure`. The `_CLOSING_BUDGET` savasana column is
    kept only as the record of what it used to be; `dharana` still reads from
    it, since restoring the meditation slot means restoring its scaling too.
    """
    savasana = session_structure(mins)["savasana"]
    for upper, _sav, dharana in _CLOSING_BUDGET:
        if mins <= upper:
            return savasana, (dharana if _INCLUDE_DHARANA else 0)
    return savasana, (_CLOSING_BUDGET[-1][2] if _INCLUDE_DHARANA else 0)


# No pose other than the closing relaxation is held longer than this. The week-3
# progression multiplier applied to an already-long restorative hold (Legs Up The
# Wall, Constructive Rest) produced six-minute single poses, which alone
# overran a 20-minute session.
_MAX_POSE_HOLD_SECONDS = 240


def pose_hold_seconds(pose: dict, experience: str, week: int, age_group: str = "adult",
                      intensity_mult: float = 1.0) -> int:
    """Per-side hold for one pose, after week progression and age scaling.

    `intensity_mult` is the daily arc's contribution (see `_DAY_ARC`). It has to
    be applied here rather than at display time so that the budget arithmetic
    that fills a section prices poses at the length they will actually be held —
    otherwise a restorative day's long holds overrun the session.
    """
    durs = pose.get("duration_seconds", {})
    base = durs.get(experience, durs.get("beginner", 30))
    hold = _week_hold(base, week)
    if age_group == "senior":
        hold = int(hold * 0.75)
    if intensity_mult != 1.0:
        hold = int(hold * intensity_mult)
    return max(min(hold, _MAX_POSE_HOLD_SECONDS), 10)


def pose_total_seconds(pose: dict, experience: str, week: int, age_group: str = "adult",
                       intensity_mult: float = 1.0) -> int:
    """Wall-clock cost of a pose in a sequence — both sides if it is unilateral.

    Unilateral poses were previously budgeted (and displayed) as a single hold,
    so Tree Pose counted 30 seconds for what is really 30 seconds *per side*.
    That understated every session and, practised as written, would have built
    left-right asymmetry.
    """
    return pose_hold_seconds(pose, experience, week, age_group,
                             intensity_mult) * pose_sides(pose)


def pose_sides(pose: dict) -> int:
    return 2 if pose.get("bilateral") else 1


# ── Sequence builder ──────────────────────────────────────────────────────────

# Poses that may open a practice. Rotated per day so the opener is not the same
# pose in all 28 sessions.
_GROUNDING_OPENERS = ["Mountain Pose", "Easy Pose", "Child's Pose", "Staff Pose",
                      "Thunderbolt Pose", "Table Pose"]

# Order the main sequence follows. A practice has an arc — warm the body upright,
# balance while fresh, peak through backbends and inversions, then neutralise and
# descend toward the floor. The builder used to emit a plain shuffle, so a
# sequence could run standing balance → quadruped → prone → lunge with no
# through-line and no counterposing.
_CATEGORY_ARC = {
    "standing": 1, "balancing": 2, "prone": 3, "backbend": 4, "inversion": 5,
    "twist": 6, "seated": 7, "forward_fold": 8, "supine": 9, "restorative": 10,
}

# Categories that neutralise a backbend or an inversion. Classical sequencing
# never leaves a deep extension or an inversion unanswered.
_COUNTERPOSE_CATEGORIES = ("forward_fold", "twist", "supine")
_NEEDS_COUNTERPOSE = ("backbend", "inversion")

# Standalone practices that are a session in their own right. Yoga Nidra is the
# Dharana slot, not a cooldown pose to stack in front of Savasana.
_STANDALONE_PRACTICES = {"yoga_nidra_pose"}

# Lying rest poses. They belong in a cooldown, never as the opening of a practice.
_REST_POSES = {"reverse_corpse_pose", "constructive_rest"}

# A cool-down pose held this long or longer is a restorative practice in its own
# right, not the unwinding after one. Judged at the practitioner's experience
# level rather than the beginner column, because that is the length they will
# actually hold it for: Supta Virasana is two minutes for a beginner and four
# for an advanced practitioner, and only the second is a second savasana.
_LONG_RESTORATIVE_SECONDS = 150


def _is_long_restorative(pose: dict, exp: str) -> bool:
    durations = pose.get("duration_seconds") or {}
    if not isinstance(durations, dict):
        return (durations or 0) >= _LONG_RESTORATIVE_SECONDS
    base = durations.get(exp, durations.get("beginner", 0)) or 0
    return base >= _LONG_RESTORATIVE_SECONDS


# Time the recovery day sets aside for one supported restorative hold, taken
# out of that day's asana budget rather than out of the cool-down slot — the
# cool-down core has to stay day-independent or day 7 recomputes its own.
_RECOVERY_HOLD_SECONDS = 240


def _is_recovery_day(arc: dict) -> bool:
    """Day 7, or any day feedback has softened all the way to restorative."""
    return arc.get("key") == "restorative"

# Below this many safe poses, a 4-week plan cannot avoid repeating heavily. The
# plan says so rather than presenting the repetition as the intended design.
_MIN_VARIED_POOL = 30

# Spare accent poses, beyond what a day already uses, below which a week is not
# rotating in any sense the practitioner would recognise.
_MIN_ROTATION_SPARE = 1

# Categories too vigorous to open a practice cold, whatever their level.
_NON_WARMUP_CATEGORIES = {"inversion", "backbend", "balancing", "twist"}


def _arc_sort(poses: list) -> list:
    return sorted(poses, key=lambda p: _CATEGORY_ARC.get(p.get("category"), 5))


def _add_counterpose(main_seq: list, cooldown: list, pool: list, exp: str, week: int,
                     age_group: str, seed_key: str, used_ids: set) -> list:
    """Guarantee the practice resolves a backbend or inversion before it ends.

    Returns the cooldown, with a neutralising pose prepended if nothing already
    following the peak does that job.
    """
    whole = main_seq + cooldown
    peak_idx = max((i for i, p in enumerate(whole)
                    if p.get("category") in _NEEDS_COUNTERPOSE), default=None)
    if peak_idx is None:
        return cooldown
    if any(p.get("category") in _COUNTERPOSE_CATEGORIES for p in whole[peak_idx + 1:]):
        return cooldown
    candidates = [p for p in pool
                  if p.get("category") in _COUNTERPOSE_CATEGORIES
                  and p["id"] not in used_ids
                  and not p.get("final_relaxation")]
    if not candidates:
        return cooldown
    return [_det_shuffle(candidates, seed_key)[0]] + cooldown


def _fill_to_budget(pool, budget_seconds, exp, week, age_group, seed_key,
                    exclude_ids=None, min_poses=1, max_poses=14,
                    intensity_mult: float = 1.0, prefer_categories=None):
    """Take poses from a deterministically shuffled pool until the budget is met.

    Stops once adding another pose would overshoot by more than half its own
    length, so a section lands close to its budget from either side.

    `prefer_categories` puts a day's accent categories at the front of the
    shuffle without excluding anything else, so the accent shows up when the
    material exists and the section still fills when it does not.
    """
    excl = set(exclude_ids or ())
    candidates = _det_shuffle([p for p in pool if p["id"] not in excl], seed_key)

    if prefer_categories:
        preferred = set(prefer_categories)
        candidates = ([p for p in candidates if p.get("category") in preferred]
                      + [p for p in candidates if p.get("category") not in preferred])

    # A single pose must not be able to swallow the whole section. The long
    # restorative holds (Legs Up The Wall, Constructive Rest) run 4-5 minutes,
    # which is longer than the entire cooldown budget of a short session — so
    # prefer poses that fit, and fall back to the cheapest available rather than
    # to whatever the shuffle happened to put first.
    affordable = [p for p in candidates
                  if pose_total_seconds(p, exp, week, age_group, intensity_mult) <= budget_seconds]
    if affordable:
        candidates = affordable
    else:
        candidates = sorted(candidates,
                            key=lambda p: pose_total_seconds(p, exp, week, age_group,
                                                             intensity_mult))

    chosen, used = [], 0
    for pose in candidates:
        if len(chosen) >= max_poses:
            break
        cost = pose_total_seconds(pose, exp, week, age_group, intensity_mult)
        # The first pose is normally taken unconditionally: the affordability
        # pass above has already guaranteed it fits, or that nothing does and
        # this is the cheapest, and a section must never come back empty. The
        # exception is `min_poses == 0`, which is how a caller says "only if
        # there is room" — an accent topping up an already-full core.
        if used + cost > budget_seconds and (chosen or min_poses == 0):
            if len(chosen) < min_poses:
                # Still under the pose-count floor, but this pose does not fit.
                # The floor used to be satisfied at any cost, and because the
                # pool is shuffled rather than sorted that meant taking whatever
                # came first: three restorative holds, minutes each, put a
                # 20-minute Sunday four minutes over the slot the rest of the
                # week landed on. Skip it and look for one that fits — a count
                # is not worth breaking the session length for.
                continue
            # Would overshoot. Take it only if it lands closer to the budget than
            # stopping short would, and only if the overshoot is bounded in
            # absolute terms — the relative test alone waves an arbitrarily large
            # pose through a nearly empty budget.
            overshoot = (used + cost) - budget_seconds
            if (overshoot > budget_seconds - used
                    or overshoot > budget_seconds * _MAX_SECTION_OVERSHOOT):
                # Keep looking rather than ending the section here. This used to
                # `break`, so ONE oversized candidate early in the shuffle closed
                # the section: an advanced cooldown took a single pose against a
                # 293-second budget, its weekly core was that one pose, and the
                # other five slots were refilled from scratch every day.
                continue
        chosen.append(pose)
        used += cost
        if used >= budget_seconds and len(chosen) >= min_poses:
            break
    return chosen


def _day_section(week_core, day_pool, budget_seconds, exp, week, age_group,
                 section: str, user_id: str, day_num: int, arc: dict, week_levels,
                 exclude_ids=None, min_poses=1, max_poses=14,
                 intensity_mult: float = 1.0):
    """Build one day's section from the week's core plus a small daily accent.

    Returns `(poses, core_ids)`.

    `week_core` is chosen once for the whole week by the caller. A restricted
    day DROPS from it rather than replacing it — recomputing a core against the
    day's own pool gives a different core every day that narrows anything, which
    is precisely the "different class each morning" this exists to stop.
    """
    excl = set(exclude_ids or ())
    core_today = [p for p in week_core
                  if p["id"] not in excl and _arc_allows(p, arc, week_levels)]

    # A breathwork day has less asana time than the core was chosen against, so
    # it stops earlier in the SAME sequence. Trimming from the tail keeps the day
    # a strict prefix of an ordinary one — the practitioner does the first part
    # of the practice they already know, not a different shorter practice.
    def _cost(poses):
        return sum(pose_total_seconds(p, exp, week, age_group, intensity_mult)
                   for p in poses)

    while len(core_today) > 1 and _cost(core_today) > budget_seconds:
        core_today.pop()

    core_ids = {p["id"] for p in core_today}
    core_cost = _cost(core_today)

    accent = _fill_to_budget(day_pool, max(budget_seconds - core_cost, 0),
                             exp, week, age_group,
                             f"{user_id}-{section}-accent-d{day_num}-w{week}",
                             exclude_ids=excl | core_ids,
                             # Zero, not one. At a 92% core share the section is
                             # already full, and a floor of one accent pose put
                             # every session five to seven minutes over its slot.
                             # The accent is what is left over, not a quota.
                             min_poses=max(0, min_poses - len(core_today)),
                             max_poses=max(1, max_poses - len(core_today)),
                             intensity_mult=intensity_mult,
                             prefer_categories=arc.get("accent"))
    return core_today + accent, core_ids


def _hold_multiplier(poses, budget_seconds, exp, week, age_group, cap: float,
                     intensity_mult: float = 1.0) -> float:
    """How much to lengthen holds so a section reaches its time budget.

    Returns 1.0 when the poses already fill the budget. Capped, because a hold
    stretched indefinitely stops being the same pose.
    """
    used = sum(pose_total_seconds(p, exp, week, age_group, intensity_mult) for p in poses)
    if used <= 0 or used >= budget_seconds:
        return 1.0
    return round(min(budget_seconds / used, cap), 2)


def build_sequence(filtered_poses, yoga_prefs, user_profile, day_num: int, week: int,
                   user_id: str, week_allowed_levels: list | None = None,
                   asana_budget_seconds: int | None = None,
                   savasana_seconds: int | None = None,
                   age_group: str = "adult",
                   adjustment: "WeekAdjustment | None" = None,
                   core_budget_seconds: int | None = None):
    mins = yoga_prefs.get("time_available_minutes", 30)
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    arc = _day_intensity(day_num, adjustment)
    day_mult = arc["hold_mult"]

    if asana_budget_seconds is None:
        sav_s, dharana_s = _closing_budget(mins)
        asana_budget_seconds = max(mins * 60 - sav_s - dharana_s, 300)
        savasana_seconds = sav_s
    savasana_seconds = savasana_seconds or _closing_budget(mins)[0]

    # Progressive week-level filtering
    #
    # The gate used to be dropped entirely whenever the week's own levels did not
    # hold enough material to fill the asana budget — "fall back rather than
    # silently shipping a short one". It shipped something worse than a short
    # session, silently: a herniated-disc beginner asking for 60 minutes got
    # plank, side plank, dolphin, half moon and eagle in WEEK ONE, every one of
    # them `level: intermediate`. Their beginner-only pool is 1980s of material
    # and the 60-minute asana budget is about 1980s, so that tier tipped over and
    # the whole gate came off. Nothing said so: `pool_limited` stayed false and
    # no notice fired.
    #
    # Session length must not reach past the week's levels. It is the same
    # surface the daily arc is forbidden from opening — "putting extra levels
    # behind a weekday index would be a safety surface nobody would think to look
    # for" — only behind a duration setting instead of a weekday.
    #
    # A pool too small for the budget already has an answer, and it is the one a
    # teacher uses: hold the safe poses longer (`_hold_multiplier`), and say the
    # session came up short (`duration_notice`, `pool_limited`). That path is
    # tested and disclosed. This one was neither.
    pose_pool = filtered_poses
    level_pool_empty = False
    if week_allowed_levels:
        narrowed = [p for p in filtered_poses if p.get("level", "beginner") in week_allowed_levels]
        # An empty pool is the one case worth widening for: a plan with no
        # session is worse than one above the week's level, and it is disclosed.
        level_pool_empty = not narrowed
        if narrowed:
            pose_pool = narrowed

    # Savasana is the closing pose and nothing else. It used to qualify for the
    # warmup pool (restorative + beginner), so "Corpse" opened every session and
    # then appeared again at the end.
    def is_final_relaxation(p):
        return bool(p.get("final_relaxation"))

    def selectable(p):
        return not is_final_relaxation(p) and p["id"] not in _STANDALONE_PRACTICES

    warmup_pool   = [p for p in pose_pool if selectable(p)
                     and p.get("category") not in _NON_WARMUP_CATEGORIES
                     and p["id"] not in _REST_POSES
                     and (p.get("sequence_role") == "warmup"
                          or (p.get("category") in ["standing", "seated", "prone", "supine"]
                              and p.get("level") == "beginner"))]
    cooldown_pool = [p for p in pose_pool if selectable(p)
                     and (p.get("sequence_role") == "cooldown"
                          or p.get("category") in ["supine", "forward_fold", "restorative", "twist"])]
    # The cool-down pool is two populations wearing one label. Twenty-two of its
    # poses are 20-90 second unwinding work — forward folds, supine releases,
    # the twist, and Matsyasana, which is what neutralises Sarvangasana. The
    # other eight are 2.5-7 minute prop-supported restorative holds, and drawing
    # one into an ordinary Tuesday put Salamba Paschimottanasana at four minutes
    # immediately in front of savasana: a session ending in two savasanas.
    #
    # Long holds are therefore reserved for the recovery day, where the length
    # IS the practice. Everything else gets the short work every day.
    #
    # The widening is on the ACCENT only. The week's cool-down core is rebuilt
    # on every day from whatever pool it is handed, so a pool that grows on day
    # 7 would recompute a different core there and leave the recovery day
    # sharing nothing with the rest of the week — the same leak that made the
    # arc filter the core last time. `cooldown_core_pool` is day-independent by
    # construction; only `cooldown_pool` moves. Same shape as `widen_accent`.
    everyday_cooldown = [p for p in cooldown_pool if not _is_long_restorative(p, exp)]
    # Never let the filter empty the pool: a heavily restricted profile may have
    # nothing but restorative poses left, and a cool-down that exists is worth
    # more than one that matches the policy.
    cooldown_core_pool = everyday_cooldown or cooldown_pool
    if not _is_recovery_day(arc):
        cooldown_pool = cooldown_core_pool
    savasana_pool = [p for p in pose_pool if is_final_relaxation(p)]
    main_pool     = [p for p in pose_pool if selectable(p)
                     and p.get("sequence_role") == "main"]

    styles = yoga_prefs.get("yoga_style_preference") or ["hatha"]
    style = styles[0] if styles else "hatha"

    def style_ok(p):
        cat = p.get("category")
        if style == "hatha":         return True
        elif style == "vinyasa":     return cat in ["standing", "balancing"]
        elif style == "restorative": return cat in ["restorative", "supine", "forward_fold", "seated"]
        elif style == "yin":         return cat in ["forward_fold", "supine", "seated", "restorative"]
        elif style == "power":       return cat in ["standing", "inversion", "backbend", "balancing"]
        elif style == "ashtanga":    return cat in ["standing", "balancing", "inversion"]
        return True

    if style in ("restorative", "yin"):
        extended_pool = [p for p in pose_pool if style_ok(p) and selectable(p)]
        styled_main = extended_pool or main_pool
    else:
        styled_main = [p for p in main_pool if style_ok(p)] or main_pool

    # A heavily contraindicated profile can filter the main pool down to nothing
    # — a herniated disc used to yield an empty main sequence, silently. Fall
    # back to whatever the user CAN safely do, and record that we did, so the
    # plan can say so rather than shipping a short session with no explanation.
    # Set above where the week's level pool came out empty and had to be widened.
    pool_limited = level_pool_empty
    if not styled_main:
        styled_main = [p for p in pose_pool if selectable(p)
                       and p.get("sequence_role") != "warmup"]
        pool_limited = True
    if not styled_main:
        styled_main = [p for p in pose_pool if selectable(p)]
        pool_limited = True

    # Savasana is already priced out of the asana budget by the caller, so the
    # cooldown share must not subtract it a second time.
    #
    # The warm-up and cool-down are FIXED slots, so the main sequence — not the
    # bookends — absorbs whatever the session length gives it. Under the old
    # shares a sixty-minute practice spent seven minutes warming up and seven
    # cooling down; the length the practitioner added went mostly to the parts
    # either side of the practice.
    structure = session_structure(mins)
    warmup_budget   = min(structure["warmup"], asana_budget_seconds // 2)
    cooldown_budget = min(structure["cooldown"], asana_budget_seconds // 2)
    main_budget     = max(asana_budget_seconds - warmup_budget - cooldown_budget,
                          int(asana_budget_seconds * _SECTION_SPLIT["main"]))

    # The week's core is selected against the standard asana budget even on days
    # that have less of it — a breathwork day stops earlier in the same sequence
    # instead of building its own. The fixed slots do not vary by day, so only
    # the main sequence needs a separate reference budget.
    core_ref = core_budget_seconds or asana_budget_seconds
    core_main_budget     = max(core_ref - warmup_budget - cooldown_budget,
                               int(core_ref * _SECTION_SPLIT["main"]))
    core_warmup_budget   = warmup_budget
    core_cooldown_budget = cooldown_budget

    # The main sequence claims the pool first. Filling warmup first meant that on
    # a heavily restricted profile the handful of safe poses were spent on the
    # warm-up and the main sequence came out empty.
    # A very short session cannot afford a three-pose minimum without blowing
    # past the time the user actually has.
    # A minimum of two poses is meaningless if two poses do not fit — an advanced
    # practitioner holds for 60-90s a side, so a 15-minute session can only
    # afford one main pose once the fixed blocks are paid for.
    cheapest = sorted(pose_total_seconds(p, exp, week, age_group, day_mult)
                      for p in styled_main)[:2]
    main_min = 1 if sum(cheapest) > main_budget else max(2, min(3, main_budget // 90))
    max_main = max(4, min(18, main_budget // 45))

    # ── Core set and daily accent ────────────────────────────────────────────
    # Every section used to be a fresh shuffle each day, which reads as variety
    # and works as amnesia: nobody gets better at Trikonasana by meeting it once,
    # and half of every session changed overnight. Most of each section is now a
    # stable weekly core the practitioner actually learns, and a small remainder
    # rotates so Tuesday is not identical to Monday.
    #
    # The recovery day's ACCENT — not its core — reaches outside `main_pool`.
    # The KB's `main` sequence_role IS the active repertoire by construction:
    # restorative, supine and forward-fold poses are all marked `cooldown`, so
    # without this the restorative day's accent has no restorative poses to draw
    # on and the day loses its character entirely. Same widening the restorative
    # and yin *styles* already do a few lines above.
    #
    # Style preference is deliberately not applied: the point of the recovery day
    # is that one day a week is not power yoga.
    arc_source = styled_main
    widen = arc.get("widen_accent")
    if widen:
        widened = [p for p in pose_pool if selectable(p)
                   and p.get("category") in widen
                   and _arc_allows(p, arc, week_allowed_levels)]
        if widened:
            arc_source = styled_main + widened

    accent_pool = [p for p in arc_source if _arc_allows(p, arc, week_allowed_levels)]
    if not accent_pool:
        # The arc must never empty a sequence. A power-style practitioner whose
        # whole safe pool is standing and inversion work has nothing that passes
        # a restorative day, and a plan with no session is worse than one that
        # is less restful than intended.
        accent_pool = styled_main
        arc = {**arc, "narrowed": False}
    else:
        arc = {**arc, "narrowed": len(accent_pool) < len(styled_main)}

    # The practice opens on the same grounding pose all week — the entry into a
    # session is the most habitual part of it, and rotating it daily made every
    # session feel like a different class. It still varies across weeks.
    # Indexed by week rather than reshuffled per week: four independent shuffles
    # of a six-pose list picked the same opener twice, so a four-week plan opened
    # on only two distinct poses.
    openers = _det_shuffle([p for p in warmup_pool
                            if p["english_name"] in _GROUNDING_OPENERS],
                           f"{user_id}-openers")
    opener = [openers[(week - 1) % len(openers)]] if openers else []

    # ── The week's core, chosen ONCE and shared by all seven days ────────────
    # Every section's core must be day-INDEPENDENT, which means it cannot be
    # selected against anything that varies by day. Building them inline used to
    # exclude `all_used` — which by then held that day's main sequence — so the
    # warmup and cooldown cores were silently recomputed daily and the week went
    # back to being a different class each morning. They are picked up front, in
    # section order, each excluding only the cores already taken.
    #
    # Main claims the pool first: filling warmup first left a heavily restricted
    # profile with its handful of safe poses spent on the warm-up.
    warmup_core_budget = warmup_budget - sum(
        pose_total_seconds(p, exp, week, age_group) for p in opener)
    week_core, core_taken = {}, {p["id"] for p in opener}
    # Both the budgets AND the pose-count caps come off the reference budget.
    # Leaving the caps on the day's own budget made a breathwork day build a
    # SMALLER main core, which freed different poses for the warm-up core after
    # it — so the day gained core poses the standard days never had, instead of
    # being the same sequence stopped early.
    core_warmup_ref = core_warmup_budget - (warmup_budget - warmup_core_budget)
    for section, pool, budget, cap in (
            ("main",     styled_main,   core_main_budget,
             max(4, min(18, core_main_budget // 45))),
            ("warmup",   warmup_pool,   core_warmup_ref,
             max(2, min(6, core_warmup_budget // 45))),
            ("cooldown", cooldown_core_pool, core_cooldown_budget,
             max(2, min(6, core_cooldown_budget // 45)))):
        core_budget = int(budget * _CORE_SHARE)
        picked = _fill_to_budget(pool, core_budget, exp, week, age_group,
                                 f"{user_id}-{section}-core-w{week}",
                                 exclude_ids=core_taken, min_poses=1,
                                 max_poses=max(1, min(cap, core_budget // 40)))
        week_core[section] = picked
        core_taken |= {p["id"] for p in picked}

    # A section's daily accent must not take a pose another section is holding as
    # its weekly core. The pools overlap, so main's accent could draw the
    # warm-up's core pose, which then dropped out of the warm-up on that day
    # alone — one day's accent quietly destabilising a different section. Each
    # section is therefore blind to the others' reserved core.
    opener_ids = {p["id"] for p in opener}

    def _reserved(*sections):
        held = set(opener_ids)
        for name in sections:
            held |= {p["id"] for p in week_core[name]}
        return held

    main_seq, core_ids = _day_section(
        week_core["main"], accent_pool, main_budget, exp, week, age_group, "main",
        user_id, day_num, arc, week_allowed_levels,
        exclude_ids=_reserved("warmup", "cooldown"),
        min_poses=main_min, max_poses=max_main, intensity_mult=day_mult)
    main_seq = _arc_sort(main_seq)
    all_used = {p["id"] for p in main_seq}

    all_used |= opener_ids
    # The opener is fixed for the week, so it is core by definition.
    core_ids |= opener_ids
    warmup_rest, warmup_core = _day_section(
        week_core["warmup"], warmup_pool, warmup_core_budget, exp, week, age_group,
        "warmup", user_id, day_num, arc, week_allowed_levels,
        exclude_ids=all_used | _reserved("cooldown"), min_poses=1,
        max_poses=max(2, min(6, warmup_budget // 45)), intensity_mult=day_mult)
    warmup = _arc_sort(opener + warmup_rest)
    core_ids |= warmup_core
    all_used.update(p["id"] for p in warmup)

    cooldown, cooldown_core = _day_section(
        week_core["cooldown"], cooldown_pool, cooldown_budget, exp, week, age_group,
        "cooldown", user_id, day_num, arc, week_allowed_levels,
        exclude_ids=all_used, min_poses=1,
        max_poses=max(2, min(6, cooldown_budget // 45)), intensity_mult=day_mult)
    cooldown = _arc_sort(cooldown)
    core_ids |= cooldown_core
    all_used.update(p["id"] for p in cooldown)

    # Counterposing is judged across the whole practice, not the main sequence
    # alone — the cooldown usually already resolves the peak. Only when nothing
    # after the last backbend or inversion neutralises it do we add one.
    cooldown = _add_counterpose(main_seq, cooldown, cooldown_pool, exp, week, age_group,
                                f"{user_id}-counter-d{day_num}-w{week}", all_used)
    all_used.update(p["id"] for p in cooldown)

    # ── Can this week move at all? ───────────────────────────────────────────
    # The split only produces variety if material is left over once a session has
    # taken what it needs. Where nothing is left, every day draws the same poses
    # and the week is one practice repeated — the honest outcome, since inventing
    # rotation would mean serving poses the safety filter excluded, but it must
    # not be presented as a rotating week. Same reasoning as `pool_limited`.
    #
    # This measured `len(accent_pool) - len(main_seq)`: spare in the MAIN pool
    # alone. Two things were wrong with that.
    #
    # A session uses most of a beginner's main-role poses by construction, so the
    # spare sat at the threshold however large the library grew. The 13 poses
    # added on 2026-08-18 took the senior main sequence from 4 to 8 and halved the
    # median duration deviation, and left this flag at exactly 18 of 28 sessions —
    # still telling a beginner their safe poses "barely fill one session" while
    # their session ran thirteen poses long.
    #
    # And it only ever fired for beginners. Measured at 45 minutes: a beginner
    # week carries 36-38 distinct poses at 94% day-to-day carryover, an
    # intermediate week 23-37, an ADVANCED week 3 fifteen at 98% carryover — least
    # variety of the three, no notice, because a deep main pool leaves spare the
    # week never spends. The flag was describing pool shape rather than what the
    # practitioner receives.
    #
    # It now measures what it claims — everything eligible across all three
    # sections against everything one session spends — at every level, with the
    # threshold unchanged. A week whose whole safe library is one pose larger than
    # a single session cannot meaningfully move.
    session_ids = {p["id"] for p in warmup + main_seq + cooldown}
    week_material = {p["id"] for p in list(accent_pool) + list(warmup_pool) + list(cooldown_pool)}
    rotation_limited = len(week_material - session_ids) <= _MIN_ROTATION_SPARE

    # Falling short of the minimum means the pool ran dry — not merely that the
    # session was short, which is a legitimate outcome of a 15-minute request.
    if len(main_seq) < main_min:
        pool_limited = True

    # Where the pool runs out before the budget does, hold longer rather than
    # shipping a short session. This is what a teacher does with a small safe
    # repertoire, and it is why a 45-minute beginner practice is not 40 poses.
    holds = {
        "warmup":   _hold_multiplier(warmup, warmup_budget, exp, week, age_group, 1.6, day_mult),
        "main":     _hold_multiplier(main_seq, main_budget, exp, week, age_group, 2.0, day_mult),
        "cooldown": _hold_multiplier(cooldown, cooldown_budget, exp, week, age_group, 2.5, day_mult),
    }

    # ── The recovery day's one long hold ─────────────────────────────────────
    # Reserving the long restorative poses "for Sunday" delivered nothing on its
    # own: at a 92% core there is no accent room anywhere, so day 7 came out as
    # the same standing practice held a quarter longer. The hold is therefore
    # appended like savasana — outside the sections, priced out of the recovery
    # day's asana budget by the caller (`_RECOVERY_HOLD_SECONDS`) so the day is
    # the week's sequence stopped earlier, not a different one.
    #
    # It sits AFTER `_arc_sort`, which puts it last in the cool-down and so
    # immediately before savasana: the recovery day closes on a supported hold.
    recovery_hold = None
    if _is_recovery_day(arc):
        long_pool = [p for p in cooldown_pool
                     if _is_long_restorative(p, exp) and p["id"] not in all_used]
        picked = _fill_to_budget(long_pool, _RECOVERY_HOLD_SECONDS, exp, week,
                                 age_group, f"{user_id}-recovery-hold-w{week}",
                                 min_poses=1, max_poses=1)
        if picked:
            recovery_hold = picked[0]
            cooldown.append(recovery_hold)
            all_used.add(recovery_hold["id"])

    if savasana_pool:
        cooldown.append(savasana_pool[0])

    return {"warmup": warmup, "main": main_seq, "cooldown": cooldown,
            "savasana_seconds": savasana_seconds, "pool_limited": pool_limited,
            "hold_multipliers": holds,
            "intensity": arc,
            # Which of the main poses are the week's core, so the UI can mark
            # what recurs rather than presenting every pose as equally novel.
            "core_pose_ids": sorted(core_ids),
            "rotation_limited": rotation_limited}


# ── Pose formatter ────────────────────────────────────────────────────────────

def format_pose(pose: dict, experience: str, week: int, age_group: str = "adult",
                hold_override: int | None = None,
                modification_experience: str | None = None) -> dict:
    """`modification_experience` lets an easy day show the gentler variation of
    the same pose without pretending the practitioner is less experienced
    anywhere else — holds, level gating and progression all stay on `experience`.
    """
    hold = hold_override if hold_override is not None else \
        pose_hold_seconds(pose, experience, week, age_group)
    sides = pose_sides(pose)
    return {
        "pose_id":             pose.get("id"),
        "pose_name":           pose.get("english_name"),
        "sanskrit_name":       pose.get("sanskrit_name"),
        "category":            pose.get("category"),
        # Joint coordinates the client draws the pose from. Travels with the plan
        # rather than the bundle: only the ~19 poses in a session are ever sent,
        # and the frontend budget is untouched. Absent until a pose has been
        # drawn, which is the signal to fall back to the category schematic.
        "figure":              pose.get("figure"),
        # Lets the client place the closing relaxation last, after pranayama and
        # meditation, rather than in the middle of the cooldown.
        "final_relaxation":    bool(pose.get("final_relaxation")),
        # `duration_seconds` is the hold for ONE side; `total_duration_seconds`
        # is what the pose actually costs in the session.
        "duration_seconds":    hold,
        "sides":               sides,
        "bilateral":           sides == 2,
        "total_duration_seconds": hold * sides,
        "side_cue":            ("Hold the full time on the right, then repeat for the "
                                "same count on the left." if sides == 2 else None),
        "instructions":        pose.get("instructions", []),
        "primary_benefits":    pose.get("primary_benefits", []),
        "modification":        _get_modification(pose, modification_experience or experience,
                                                 age_group),
        "pranayama_sync":      pose.get("pranayama_sync", "Breathe steadily"),
        "ayurvedic_rationale": pose.get("ayurvedic_rationale", ""),
        "image_url":           pose.get("image_url", ""),
        "body_parts":          pose.get("body_parts", []),
    }


# ── Dharana (meditation) slot ─────────────────────────────────────────────────

_DHARANA = {
    "vata": {
        "technique":           "So-Hum Breath Awareness",
        "sanskrit_name":       "Ajapa Japa",
        "duration_minutes":    5,
        "instructions": [
            "Settle into Savasana or a comfortable seated position after your practice.",
            "Close the eyes and allow the breath to return to its natural rhythm without control.",
            "Silently synchronise the mantra: 'So' on the inhale, 'Hum' on the exhale.",
            "When the mind wanders, gently return to the breath and the mantra without judgement.",
            "Continue for 5 minutes, gradually releasing effort and surrendering to stillness.",
        ],
        "dosha_note":          "Grounds Vata's scattered mental energy through rhythmic, anchored awareness.",
        "classical_reference": "Hatha Yoga Pradipika 4.29 — Ajapa Japa (un-repeated repetition) dissolves the Chitta's fluctuations by synchronising breath and mantra.",
    },
    "pitta": {
        "technique":           "Trataka — Single-Point Concentration",
        "sanskrit_name":       "Trataka",
        "duration_minutes":    5,
        "instructions": [
            "Seat yourself comfortably 1-2 feet from a candle flame (or visualise one clearly).",
            "Gaze softly at the tip of the flame without blinking for 1-2 minutes.",
            "When the eyes water or strain, gently close them and visualise the flame at the centre of the forehead.",
            "Hold the inner image until it fades naturally, then reopen the eyes and repeat.",
            "After 5 minutes, rub the palms together briskly, cup them over the closed eyes, and slowly release.",
        ],
        "dosha_note":          "Directs Pitta's sharp, goal-oriented mind inward, channeling heat into focused inner awareness without striving.",
        "classical_reference": "Hatha Yoga Pradipika 2.31 — Trataka destroys all eye diseases, opens the Ajna Chakra, and is kept secret like gold.",
    },
    "kapha": {
        "technique":           "Yoga Nidra — Conscious Body Scan",
        "sanskrit_name":       "Yoga Nidra",
        "duration_minutes":    7,
        "instructions": [
            "Lie in Savasana with eyes closed, palms facing up, feet gently apart.",
            "Set a Sankalpa (short positive intention in Sanskrit or your native language): repeat it mentally 3 times with deep feeling.",
            "Rotate awareness systematically: right thumb, index finger, middle finger, ring finger, little finger, palm, back of hand, wrist, forearm, elbow, upper arm, shoulder, right side of chest, right side of abdomen, right thigh, knee, calf, ankle, heel, sole, right big toe. Repeat on the left side. Then the back, then the front.",
            "After the rotation, become aware of the sensation of heaviness throughout the body, then lightness.",
            "Repeat your Sankalpa 3 times with feeling, then slowly return awareness to the room around you.",
        ],
        "dosha_note":          "Activates Kapha's capacity for deep stillness into conscious awareness, preventing the practice from collapsing into inertia or sleep.",
        "classical_reference": "Mandukya Upanishad 1.7 — Yoga Nidra operates in the Prajna state between waking and deep sleep, where the deepest healing occurs.",
    },
}


# ── Day builder ───────────────────────────────────────────────────────────────

def build_yoga_day(sequence: dict, pranayama: list, yoga_prefs: dict,
                   user_profile: dict, week: int, age_group: str = "adult",
                   contra_tags: set | None = None,
                   dharana_seconds: int | None = None,
                   sns: dict | None = None,
                   pranayama_seconds: int | None = None) -> dict:
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    dosha = user_profile.get("dominant_dosha", "vata")
    goal = yoga_prefs.get("yoga_goal", "flexibility").replace("_", " ")
    if dosha == "vata":    theme = f"Grounding & Warming {goal.title()} Practice"
    elif dosha == "pitta": theme = f"Cooling & Calming {goal.title()} Flow"
    else:                  theme = f"Energising & Invigorating {goal.title()} Sequence"

    mult = sequence.get("hold_multipliers") or {}
    # The daily arc's multiplier priced the sequence when it was filled, so it
    # has to be applied here too or the session displays holds that do not add
    # up to the budget it was built against.
    arc = sequence.get("intensity") or {}
    day_mult = arc.get("hold_mult", 1.0)

    # An easy day keeps the week's sequence and shows the gentler variation of
    # each pose. This is the day's real difference: a hold multiplier would be
    # cancelled by the budget filler, and dropping poses would break the
    # consistency the core exists to provide.
    mod_exp = _shift_experience(exp, -1) if arc.get("ease_modifications") else exp

    def _hold(pose, section):
        # The cap has to be re-applied after the section multiplier, or a pose
        # already at the ceiling gets stretched straight past it.
        stretched = (pose_hold_seconds(pose, exp, week, age_group, day_mult)
                     * mult.get(section, 1.0))
        ceiling = _MAX_POSE_HOLD_SECONDS
        # Keeping long restorative POSES out of a weekday cool-down is only half
        # the rule — where the pool is thin the multiplier stretches whatever is
        # left, and a beginner's Supta Matsyendrasana came out at nearly three
        # minutes directly in front of savasana. One number governs both which
        # poses may appear and how long any of them may run.
        if section == "cooldown" and not _is_recovery_day(arc):
            ceiling = min(ceiling, _LONG_RESTORATIVE_SECONDS)
        return int(min(stretched, ceiling))

    warmup_fmt = [format_pose(p, exp, week, age_group, hold_override=_hold(p, "warmup"),
                              modification_experience=mod_exp)
                  for p in sequence["warmup"]]
    main_fmt   = [format_pose(p, exp, week, age_group, hold_override=_hold(p, "main"),
                              modification_experience=mod_exp)
                  for p in sequence["main"]]
    # The closing relaxation is held for the session's budgeted savasana time,
    # not the pose's own default.
    sav_seconds  = sequence.get("savasana_seconds")
    cooldown_fmt = [
        format_pose(p, exp, week, age_group,
                    hold_override=sav_seconds if p.get("final_relaxation")
                    else _hold(p, "cooldown"),
                    modification_experience=mod_exp)
        for p in sequence["cooldown"]
    ]

    # The caller resolves the prescribed stack and passes it as
    # [(technique, minutes), ...]; a direct caller may still pass plain techniques.
    day_plan_prana = [
        p if isinstance(p, tuple)
        else (p, pranayama_minutes(p, exp, yoga_prefs.get("time_available_minutes", 30)))
        for p in (pranayama or [])
    ]
    pranayama_section = []
    for pr, pr_minutes in day_plan_prana:
        pranayama_section.append({
            "technique_id":    pr.get("id"),
            "technique_name":  pr.get("english_name"),
            "sanskrit_name":   pr.get("sanskrit_name"),
            "duration_minutes": pr_minutes,
            "instructions":    pr.get("instructions", []),
            "dosha_note":      f"Balances {dosha.title()} — {pr.get('type', 'balancing')} pranayama.",
        })

    # Surya Namaskar block — morning sessions only. Built once per user by the
    # caller so its cost can be subtracted from the asana budget before the
    # sequence is filled; rebuilt here only when called directly.
    if sns is None:
        sns = _build_surya_namaskar_block(
            user_profile, yoga_prefs, contra_tags or set(), age_group,
            session_structure(yoga_prefs.get("time_available_minutes", 30))["surya_namaskar"])

    # Dharana/meditation slot — dosha-matched, scaled to the session length
    dharana = None
    if _INCLUDE_DHARANA:
        dharana = dict(_DHARANA.get(dosha, _DHARANA["vata"]))
        if dharana_seconds:
            dharana["duration_minutes"] = max(round(dharana_seconds / 60), 2)

    # Every block that costs the practitioner wall-clock time counts toward the
    # estimate. Surya Namaskar (2-8 min) and Dharana (2-10 min) used to be left
    # out, so the figure shown did not even match the session's own content.
    asana_secs  = sum(p["total_duration_seconds"] for p in warmup_fmt + main_fmt + cooldown_fmt)
    prana_secs  = sum(p["duration_minutes"] * 60 for p in pranayama_section)
    sns_secs    = int((sns or {}).get("duration_minutes", 0) * 60)
    dharana_sec = int((dharana or {}).get("duration_minutes", 0) * 60)
    total_secs  = asana_secs + prana_secs + sns_secs + dharana_sec

    # `total_duration_minutes` is what the UI badge renders, so it reports the session
    # that was BUILT, not the one that was asked for. It used to echo
    # time_available_minutes straight back: a 60-minute beginner vinyasa request
    # displayed "60 min" over 42 minutes of practice, which is the same defect as the
    # original fixed-pose-count builder — the number on the card and the practice
    # underneath it being different products — just moved into the label.
    # The request is kept as `requested_duration_minutes` because week-on-week
    # progression scales the *target*, and that has to stay legible.
    requested_minutes = yoga_prefs.get("time_available_minutes", 30)
    built_minutes = round(total_secs / 60)
    shortfall = requested_minutes - built_minutes

    # A gap this size is a real difference to the practitioner, not rounding. It happens
    # when the safe pool at this level runs out before the budget does — most visibly a
    # beginner asking for 60 minutes, where holds lengthen only up to _MAX_POSE_HOLD_SECONDS
    # and then the session simply is what it is. Say so rather than quietly serving short.
    duration_notice = None
    if requested_minutes and abs(shortfall) / requested_minutes > 0.10:
        if shortfall > 0:
            duration_notice = (
                f"This session runs about {built_minutes} minutes rather than the "
                f"{requested_minutes} you asked for. At your level the poses that are safe "
                f"for you do not fill that much time without holding each one longer than is "
                f"useful. Practise it unhurried, or repeat the main sequence to fill the hour."
            )
        else:
            duration_notice = (
                f"This session runs about {built_minutes} minutes, a little over the "
                f"{requested_minutes} you asked for, because the poses at your level are held "
                f"longer. Drop the final poses of the main sequence if you are short on time."
            )

    return {
        "surya_namaskar":    sns,
        "warmup":            warmup_fmt,
        "main_sequence":     main_fmt,
        "cooldown":          cooldown_fmt,
        "pranayama_section": pranayama_section,
        "dharana_section":   dharana,
        "total_duration_minutes":         built_minutes,
        "requested_duration_minutes":     requested_minutes,
        "duration_notice":                duration_notice,
        "estimated_pose_time_minutes":    round(total_secs / 60, 1),
        "time_breakdown_minutes": {
            "surya_namaskar": round(sns_secs / 60, 1),
            "asana":          round(asana_secs / 60, 1),
            "pranayama":      round(prana_secs / 60, 1),
            "dharana":        round(dharana_sec / 60, 1),
        },
        "sequence_type":     yoga_prefs.get("time_of_day_preference", "morning"),
        "dosha_theme":       theme,
        "pool_limited":      bool(sequence.get("pool_limited")),
        # The day's place in the weekly load arc. Surfaced so the practitioner
        # can see that Sunday being easy is the design rather than a thin plan,
        # and so they know which days are meant to be demanding.
        "intensity":         arc.get("key", "moderate"),
        "intensity_label":   arc.get("label", "Moderate"),
        "intensity_note":    arc.get("note"),
        # How to perform today's poses, as opposed to which poses they are. The
        # easy days keep the week's sequence, so this is what actually makes them
        # easier — without it a "Gentle" badge sits over an unchanged practice.
        "effort_cue":        arc.get("effort_cue"),
        "core_pose_ids":     sequence.get("core_pose_ids", []),
        "rotation_limited":  bool(sequence.get("rotation_limited")),
        "rotation_notice":   (
            "The poses that are safe for you at this level barely fill one session, "
            "so this week repeats the same sequence rather than rotating. That is the "
            "honest limit of your pose list, not a shortened plan — the variety opens "
            "up as the weeks unlock more poses."
            if sequence.get("rotation_limited") else None),
    }


# ── Ayurvedic tips ────────────────────────────────────────────────────────────

def get_ayurvedic_tips(dosha: str) -> dict:
    if dosha == "pitta":
        return {
            "best_time":      "Early morning 6–8am or evening after 6pm. Avoid midday practice.",
            "environment":    "Cool, well-ventilated space. Natural light preferred. Avoid heating the room.",
            "what_to_wear":   "Light, breathable fabric. Avoid synthetic materials that trap heat.",
            "after_practice": "Cool water or coconut water. Avoid hot shower immediately after.",
            "dosha_note":     "Pitta practitioners tend toward perfectionism and overheating. Prioritise cooling poses (forward folds, twists) and cultivate a non-competitive mindset.",
        }
    elif dosha == "kapha":
        return {
            "best_time":      "6–8am. Practice during Kapha time to counter morning heaviness.",
            "environment":    "Bright, well-lit, open space. Uplifting music if desired. Avoid dark, heavy rooms.",
            "what_to_wear":   "Fitted clothes that allow full range of movement.",
            "after_practice": "Kapalabhati pranayama for 2 min. Ginger or black pepper tea.",
            "dosha_note":     "Kapha practitioners benefit most from vigorous, warming, invigorating sequences. Sun Salutations and inversions are especially balancing.",
        }
    else:
        return {
            "best_time":      "10am–2pm or early evening. Avoid pre-dawn practice when Vata is highest.",
            "environment":    "Warm, quiet, dimly lit room. Use blankets and bolsters freely.",
            "what_to_wear":   "Warm, comfortable layers. Keep yourself warm throughout — especially feet.",
            "after_practice": "Rest in Savasana minimum 10 minutes. Warm herbal tea (Ashwagandha, Brahmi).",
            "dosha_note":     "Vata practitioners should avoid over-exertion, strong inversions, and fast-paced flows. Slow, grounding, repetitive sequences are most therapeutic.",
        }


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_yoga_plan(user_profile, yoga_prefs, yoga_poses_db=None, pranayama_list_db=None,
                       extra_protocols=None, weeks=None, feedback_history=None,
                       recent_pose_ids=None):
    """Build a yoga plan.

    `weeks` selects which week numbers to generate — by default just the first.
    Weeks are produced one at a time so each can be shaped by what the user
    reported about the last one; passing [1, 2, 3, 4] restores the old behaviour
    of generating the whole block up front.
    """
    yp = yoga_poses_db if yoga_poses_db is not None else yoga_poses
    pl = pranayama_list_db if pranayama_list_db is not None else pranayama_list

    weeks = sorted({int(w) for w in (weeks or [1]) if 1 <= int(w) <= _TOTAL_WEEKS})
    if not weeks:
        weeks = [1]
    adjustment = build_week_adjustment(feedback_history)

    # Thread-safe local protocol map (merge base + any dynamic protocols for unknown conditions)
    effective_proto_map = dict(_PROTOCOL_MAP)
    if extra_protocols:
        effective_proto_map.update(extra_protocols)

    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"

    # Feedback moves the practitioner up or down the experience ladder, which is
    # what actually changes which poses are eligible.
    effective_exp = _shift_experience(user_exp, adjustment.level_shift)
    if adjustment.duration_scale != 1.0:
        scaled_minutes = int(round(
            yoga_prefs.get("time_available_minutes", 30) * adjustment.duration_scale))
        yoga_prefs = {**yoga_prefs, "time_available_minutes": max(scaled_minutes, 10)}
    if effective_exp != user_exp:
        yoga_prefs = {**yoga_prefs, "yoga_experience": effective_exp}
    user_exp = effective_exp

    # Age group for adaptive modifications
    age_group = _get_age_group(user_profile.get("age"))

    # Max allowed levels across all 4 weeks (for filter_poses pool)
    prog_levels = _PROGRESSIVE_LEVELS.get(user_exp, _PROGRESSIVE_LEVELS["beginner"])
    all_levels = list({lv for ls in prog_levels.values() for lv in ls})

    # Senior: never go above beginner
    if age_group == "senior":
        all_levels = ["beginner"]
        prog_levels = {1: ["beginner"], 2: ["beginner"], 3: ["beginner"], 4: ["beginner"]}

    # Build contra set once (reused by Surya Namaskar checker)
    user_contra_tags = _build_contra_set(user_profile, age_group)

    # Filter and score the full pose pool once
    filtered_poses = filter_poses(user_profile, yoga_prefs, yp,
                                  max_allowed_levels=all_levels,
                                  protocol_map=effective_proto_map,
                                  adjustment=adjustment,
                                  recent_pose_ids=recent_pose_ids)

    # `select_pranayama` is no longer on this path. The daily stack is prescribed
    # (see `_DAILY_PRANAYAMA`), so the scorer has nothing left to choose. It is
    # kept rather than deleted because the SAFETY half of what it read still
    # runs — `_pranayama_gates` was extracted from it and enforces protocol
    # avoid-lists, contraindications, pregnancy, age and level on the
    # prescription too.
    #
    # What the prescription does give up is protocol *priorities*: a condition
    # that recommends a particular breath no longer promotes it. The avoid side
    # is unaffected, so this costs a therapeutic suggestion, never a safeguard.

    # Safety transparency: which forceful/retention pranayama were excluded for this
    # user's conditions — surfaced in the UI so the exclusion is visible, not silent.
    _prana_exclusions = []
    _uc = set(c.lower() for c in (user_profile.get("medical_history") or []))
    _is_preg_x = _pregnancy_state(user_profile)[0]
    if _uc or _is_preg_x:
        _PRANA_DISPLAY = {
            "skull_shining":   "Kapalabhati (Skull-Shining Breath)",
            "bellows_breath":  "Bhastrika (Bellows Breath)",
            "breath_retention": "Kumbhaka (Breath Retention)",
            "right_nostril":   "Surya Bhedana (Right-Nostril Breath)",
            "fire_essence":    "Agnisara (Fire Essence)",
            "swooning_breath": "Murccha (Swooning Breath)",
            "root_lock_breath": "Bandha Pranayama (with locks)",
        }
        for _pr in pl:
            _pid = _pr.get("id")
            if _pid not in _PRANA_DISPLAY:
                continue
            _preg_block = _is_preg_x and not _pr.get("pregnancy_safe", True)
            if _preg_block or _pranayama_hard_blocked(_pr, _uc):
                _prana_exclusions.append({
                    "name": _PRANA_DISPLAY[_pid],
                    "reason": "Pregnancy" if _preg_block else "Contraindicated for your health conditions",
                })

    time_of_day = yoga_prefs.get("time_of_day_preference", "morning")
    # No rest days. Unlike resistance training, yoga is a daily practice —
    # classical Dinacharya prescribes sadhana every day. Recovery is provided
    # within the week instead, by `_DAY_ARC`: day 6 is gentle and day 7 is
    # restorative, both in the same time slot as every other day. The
    # week-to-week feedback loop is the second protection against overload —
    # "too hard" or "drained" softens the following week's arc as well as
    # pulling its level and duration down.
    rest_days: set[int] = set()

    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant, is_nursing, trimester = _pregnancy_state(user_profile)
    user_conditions = [c for c in (user_profile.get("medical_history") or []) if c]
    gender = (user_profile.get("gender") or "").lower()
    season_cfg = _get_season_boost(user_profile.get("current_season"))

    # Active condition protocols with gender gate
    active_protocols = []
    seen_proto_ids = set()
    for cond in user_conditions:
        cond_lower = cond.lower()
        if cond_lower in _FEMALE_ONLY_PROTOCOLS and gender in ("male", "m"):
            continue
        proto = effective_proto_map.get(cond_lower)
        if proto and proto.get("id") not in seen_proto_ids:
            seen_proto_ids.add(proto.get("id"))
            active_protocols.append({
                "condition":           cond,
                "protocol_name":       proto.get("name"),
                "classical_reference": proto.get("classical_reference"),
                "research_note":       proto.get("research_note"),
                "sequence_note":       proto.get("sequence_note"),
                "lifestyle_note":      proto.get("lifestyle_note"),
                "is_dynamic":          proto.get("_dynamic", False),
            })

    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # ── Session time budget ──────────────────────────────────────────────────
    # Everything that costs wall-clock time is priced before the asana sections
    # are filled, so the sum of the parts lands on the duration the user asked
    # for rather than a third of it.
    session_minutes = yoga_prefs.get("time_available_minutes", 30)
    structure = session_structure(session_minutes)
    savasana_seconds, dharana_seconds = _closing_budget(session_minutes)
    sns_block = _build_surya_namaskar_block(user_profile, yoga_prefs,
                                           user_contra_tags, age_group,
                                           structure["surya_namaskar"])
    sns_seconds = int((sns_block or {}).get("duration_minutes", 0) * 60)
    # Every day runs the same prescribed stack, so the budget prices it once.
    # The cleansing slot alternates for Pitta, but both options are the same
    # length, so any day resolves to the same total.
    _day1_prana, _prana_dropped, _prana_protocol_id = pranayama_day_plan(
        pl, user_profile, yoga_prefs, day_num=1, session_minutes=session_minutes,
        protocol_map=effective_proto_map)
    prana_seconds = sum(m for _t, m in _day1_prana) * 60

    # Anything the prescription could not place says why. Silently serving two
    # techniques where three were prescribed is the failure mode here: the
    # practitioner asked for these by name, so an absence needs a reason, and
    # most of these reasons are recoverable.
    # Covers the prescribed three plus everything a protocol can put in the
    # third slot, so a protocol-led choice is never announced by its raw id.
    _PRESCRIBED_LABELS = {
        "humming_bee":         "Bhramari (Humming-Bee Breath)",
        "alternate_nostril":   "Anulom Vilom (Alternate-Nostril Breath)",
        "skull_shining":       "Kapalabhati (Skull-Shining Breath)",
        "cooling_breath":      "Sitali (Cooling Breath)",
        "hissing_breath":      "Sitkari (Hissing Breath)",
        "three_part_breath":   "Dirgha (Three-Part Breath)",
        "left_nostril":        "Chandra Bhedana (Left-Nostril Breath)",
        "right_nostril":       "Surya Bhedana (Right-Nostril Breath)",
        "ocean_breath":        "Ujjayi (Ocean Breath)",
        "box_equal_breathing": "Sama Vritti (Equal Breathing)",
        "unequal_breathing":   "Vishama Vritti (Unequal Breathing)",
        "bellows_breath":      "Bhastrika (Bellows Breath)",
        "fire_essence":        "Agnisara (Fire Essence)",
        "against_the_grain":   "Viloma (Against the Grain)",
        "extended_cooling":    "Sheetali Kumbhaka (Extended Cooling)",
        "root_lock_breath":    "Mula Bandha Pranayama",
    }
    _DROP_REASONS = {
        "pregnancy":  "Not practised during pregnancy",
        "condition":  "Contraindicated for your health conditions",
        "age":        "Held back at your age — it is a forceful practice, and the "
                      "pressure it builds is the wrong thing to do unsupervised",
        "level":      "Taught from a later level — it joins your plan as you progress",
        "time_of_day": "A morning practice — switch your sessions to mornings to include it",
        "session_length": "There is not room for it in a session this short — a longer "
                          "session fits all three prescribed breaths",
    }
    # When a condition decided the third breath, say so. Otherwise the plan
    # quietly serves a technique the practitioner never asked for next to two
    # they did, and the reason lives only in the code.
    _prana_protocol_note = None
    if _prana_protocol_id:
        _proto_names = [p["protocol_name"] for p in active_protocols if p.get("protocol_name")]
        _prana_protocol_note = (
            f"Your third breath is {_PRESCRIBED_LABELS.get(_prana_protocol_id, _prana_protocol_id)}, "
            f"chosen by your "
            + (f"{_proto_names[0]}" if _proto_names else "condition protocol")
            + " rather than by constitution — it is what your condition calls for."
        )

    _already = {e["name"] for e in _prana_exclusions}
    for _d in _prana_dropped:
        _label = _PRESCRIBED_LABELS.get(_d["id"])
        if not _label or _label in _already:
            continue
        _prana_exclusions.append({
            "name": _label,
            "reason": _DROP_REASONS.get(_d["reason"], "Not suitable for your profile"),
        })
        _already.add(_label)
    # The fixed blocks can exceed the whole session — an advanced practitioner
    # asking for 15 minutes draws 4 rounds of Surya Namaskar and a long
    # pranayama, which together with the closing already overruns the request.
    # Trim them to fit rather than flooring the asana budget and overshooting,
    # so a 15-minute session is 15 minutes of practice.
    session_seconds = session_minutes * 60
    fixed_seconds = sns_seconds + prana_seconds + savasana_seconds + dharana_seconds
    max_fixed = int(session_seconds * _MAX_FIXED_BLOCK_SHARE)
    if fixed_seconds > max_fixed:
        # Pranayama does NOT shrink here. It is a prescription that has already
        # been fitted to its own share of the session, and a practice that keeps
        # eight minutes of Surya Namaskar while cutting the breathwork has the
        # priorities backwards. The scale is therefore recomputed over only the
        # blocks that can give — otherwise a Kapha profile, which draws far more
        # Surya Namaskar, would pay for it out of the breath.
        shrinkable = sns_seconds + savasana_seconds + dharana_seconds
        scale = max(max_fixed - prana_seconds, 0) / shrinkable if shrinkable else 1.0
        dharana_seconds = max(int(dharana_seconds * scale), 90) if dharana_seconds else 0
        savasana_seconds = max(int(savasana_seconds * scale), 90)
        sns_block, sns_seconds = _scale_surya_namaskar(sns_block, scale)

    asana_budget = max(session_seconds - sns_seconds - prana_seconds
                       - savasana_seconds - dharana_seconds, 180)

    four_week_plan = []
    for week in weeks:
        cfg = _WEEK_CONFIG[week]
        week_levels = prog_levels[week]
        week_days = []
        for i in range(1, 8):
            day_name = days_of_week[i - 1]
            if i in rest_days:
                week_days.append({"day": i, "day_name": day_name, "session": None, "rest": True})
            else:
                # The recovery day pays for its one supported hold out of its own
                # asana budget, but its week core is still selected against the
                # standard one — so it is the same sequence stopped earlier, not
                # a sequence of its own. Same mechanism the breathwork focus day
                # used before the prescription replaced it.
                day_budget = asana_budget
                if _is_recovery_day(_day_intensity(i, adjustment)):
                    day_budget = max(asana_budget - _RECOVERY_HOLD_SECONDS, 180)
                seq = build_sequence(filtered_poses, yoga_prefs, user_profile,
                                     day_num=i, week=week, user_id=user_id,
                                     week_allowed_levels=week_levels,
                                     asana_budget_seconds=day_budget,
                                     savasana_seconds=savasana_seconds,
                                     age_group=age_group,
                                     adjustment=adjustment,
                                     core_budget_seconds=asana_budget)

                # The same prescribed stack every day. Only the cleansing slot
                # moves, and only for Pitta, where Sitali and Sitkari alternate.
                day_prana, _, _ = pranayama_day_plan(
                    pl, user_profile, yoga_prefs, day_num=i,
                    session_minutes=session_minutes,
                    protocol_map=effective_proto_map)

                day_plan = build_yoga_day(seq, day_prana, yoga_prefs, user_profile,
                                          week, age_group=age_group,
                                          contra_tags=user_contra_tags,
                                          dharana_seconds=dharana_seconds,
                                          sns=sns_block,
                                          pranayama_seconds=prana_seconds)
                week_days.append({"day": i, "day_name": day_name, "session": day_plan,
                                  "rest": False,
                                  "intensity": day_plan.get("intensity"),
                                  "intensity_label": day_plan.get("intensity_label")})

        four_week_plan.append({
            "week":  week,
            "theme": cfg["theme"],
            "note":  cfg["note"],
            "days":  week_days,
        })

    # A fourth breath nobody asked for needs a reason as much as a missing one
    # does. Read off the stack that was actually built, so it can never claim a
    # chaser the tier's budget declined to pay for.
    _prana_cooling_note = None
    _first_stack = next((d["session"].get("pranayama_section")
                         for w in four_week_plan for d in w["days"]
                         if d.get("session")), None) or []
    if len(_first_stack) == 4:
        _prana_cooling_note = (
            f"{_first_stack[2]['sanskrit_name']} is what your condition calls for, "
            f"and it is a heating practice — so it is followed by "
            f"{_first_stack[3]['sanskrit_name']}, which cools the system your Pitta "
            f"constitution already runs warm. Practise them in that order."
        )

    # If safety filtering left too little material to build a full practice from,
    # say so plainly. The alternative — silently shipping a short session — reads
    # as a thin product rather than as the safety decision it actually is.
    pool_notice = None
    if len(filtered_poses) < _MIN_VARIED_POOL or any(
            d["session"] and d["session"].get("pool_limited")
            for w in four_week_plan for d in w["days"]):
        # Passive, deliberately: the reasons are a variable-length list and any
        # active phrasing needs verb agreement that "your age" and "your health
        # conditions" do not share.
        pool_notice = (
            "A large part of the pose library is ruled out by "
            f"{_join_reasons(_pool_narrowing_reasons(user_profile, yoga_prefs))}, so "
            "this plan is built from the smaller set that is safe for you. Sessions "
            "are shorter and repeat more often than usual by design. A qualified yoga "
            "therapist can supervise poses that a self-guided plan has to exclude."
        )

    _TRIMESTER_NOTE = {
        1: "First trimester: poses that raise abdominal pressure are excluded. Stop "
           "if you feel light-headed, and skip practice entirely on days you are nauseous.",
        2: "Second trimester: lying prone is excluded as the bump grows, along with "
           "abdominal work and inversions. Widen your stance for balance.",
        3: "Third trimester: prone and supine poses are both excluded — extended time "
           "on your back can compress the vena cava — as are inversions and unsupported "
           "balances. Use a wall or chair for anything on one leg.",
    }
    if is_pregnant:
        disclaimer = (
            f"PREGNANCY — TRIMESTER {trimester}: This plan is filtered for pregnancy safety. "
            f"{_TRIMESTER_NOTE[trimester]} Please practise under the guidance of a prenatal "
            "yoga teacher and clear this plan with your doctor or midwife first."
        )
    elif is_nursing:
        disclaimer = (
            "Nursing: yoga carries no specific restrictions while breastfeeding. Practise "
            "after a feed for comfort, stay well hydrated, and rebuild abdominal and pelvic "
            "floor strength gradually if you gave birth recently. Consult a physician before "
            "beginning any new practice."
        )
    else:
        disclaimer = (
            "This plan is for general wellness guidance only. Consult a physician before "
            "beginning any new practice."
        )

    return {
        "plan_id":        f"yoga_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha":     dominant_dosha,
            "yoga_goal":          yoga_prefs.get("yoga_goal", "flexibility"),
            "experience":         user_exp,
            "style_preference":   yoga_prefs.get("yoga_style_preference", ["hatha"]),
            "time_available":     yoga_prefs.get("time_available_minutes", 30),
            "time_of_day":        time_of_day,
            "medical_conditions": user_conditions,
            "age_group":          age_group,
            "stress_level":       user_profile.get("stress_level"),
            "sleep_quality":      user_profile.get("sleep_quality"),
            "agni_type":          user_profile.get("agni_type"),
            "ojas_level":         user_profile.get("ojas_level"),
        },
        "weekly_schedule":    four_week_plan[0]["days"],
        "four_week_plan":     four_week_plan,
        # Progression state. The plan is built a week at a time, so the client
        # needs to know which weeks exist and whether another can be requested.
        "weeks_generated":    [w["week"] for w in four_week_plan],
        "total_weeks":        _TOTAL_WEEKS,
        "next_week":          (max(w["week"] for w in four_week_plan) + 1
                               if max(w["week"] for w in four_week_plan) < _TOTAL_WEEKS
                               else None),
        # What last week's feedback changed, in the user's terms. Empty on week 1.
        "progression_adjustment": adjustment.as_dict() if adjustment.reasons else None,
        "ayurvedic_tips":     get_ayurvedic_tips(dominant_dosha),
        "seasonal_note":      season_cfg.get("note") if season_cfg else None,
        "practice_pool_notice": pool_notice,
        "condition_protocols": active_protocols or None,
        "pranayama_safety_exclusions": _prana_exclusions or None,
        "pranayama_cooling_note": _prana_cooling_note,
        "pranayama_protocol_note": _prana_protocol_note,
        "disclaimer":         disclaimer,
        "enriched":           False,
    }
