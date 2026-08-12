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

# Dosha-based pacing: (rounds_beginner, rounds_intermediate, rounds_advanced, breaths_per_step)
_SNS_DOSHA_CONFIG = {
    "vata":  {"rounds": {"beginner": 2, "intermediate": 3, "advanced": 4},
               "pace": "slow",  "pace_note": "Move slowly and mindfully — 1 breath per movement. Prioritise steadiness over speed to ground Vata energy."},
    "pitta": {"rounds": {"beginner": 3, "intermediate": 5, "advanced": 6},
               "pace": "moderate", "pace_note": "Moderate pace — avoid overheating. Rest in Downward Dog for 5 breaths between rounds. Never compete with yourself."},
    "kapha": {"rounds": {"beginner": 4, "intermediate": 6, "advanced": 8},
               "pace": "vigorous", "pace_note": "Vigorous, continuous flow. Build heat with purpose — Kapha benefits most from dynamic sequences that activate metabolic fire."},
}


def _build_surya_namaskar_block(user_profile: dict, yoga_prefs: dict,
                                 contra_tags: set, age_group: str) -> dict | None:
    """Return a Surya Namaskar flow block or None if contraindicated."""
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
    rounds_map = dosha_cfg["rounds"]

    # Senior: 1 round, chair-supported
    if age_group == "senior":
        rounds = 1
        modification = "Chair-supported Surya Namaskar: perform Steps 1-3 and 10-12 standing. Replace Steps 4-9 with seated chair poses. Always keep one hand on the chair back."
    else:
        rounds = rounds_map.get(exp, rounds_map["beginner"])
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

    # Duration estimate: ~4-5 seconds per step × 12 steps × rounds + rest
    duration_minutes = round((rounds * 12 * 5) / 60 + (rounds - 1) * 0.25, 1)

    return {
        "rounds": rounds,
        "duration_minutes": duration_minutes,
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
    "sciatica":            {"serious_back_injury"},
    "herniated_disc":      {"herniated_disc", "serious_back_injury", "serious_spinal_injury"},
    "spinal_injury":       {"serious_spinal_injury", "spinal_injury"},
    "knee_injury":         {"knee_injury", "knee_replacement"},
    "knee_replacement":    {"knee_injury", "knee_replacement"},
    "ankle_injury":        {"ankle_injury"},
    "shoulder_injury":     {"shoulder_injury", "rotator_cuff"},
    "osteoporosis":        {"serious_spinal_injury"},
    "post_cardiac":        {"heart_disease", "high_blood_pressure"},
    "heart_surgery_recovery": {"heart_disease", "high_blood_pressure"},
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

    "osteoporosis":         {"spinal_flexion", "fall_risk"},
    "osteopenia":           {"spinal_flexion"},
    "compression_fracture": {"spinal_flexion"},

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
    "lower_back":      {"lower_back_pain", "herniated_disc", "serious_back_injury"},
    "back":            {"lower_back_pain", "herniated_disc", "serious_back_injury"},
    "shoulder":        {"shoulder_injury", "rotator_cuff"},
    "neck":            {"neck_injury", "cervical_spondylosis", "serious_neck_injury"},
    "hypertension":    {"high_blood_pressure", "hypertension"},
    "blood_pressure":  {"high_blood_pressure", "hypertension"},
    "heart":           {"heart_disease"},
    "glaucoma":        {"glaucoma"},
    "ankle":           {"ankle_injury"},
    "groin":           {"groin_injury"},
    "wrist":           {"wrist_injury"},
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

    # Age-based breath restrictions
    if age_group in ("senior", "youth"):
        protocol_avoid_ids.add("breath_retention")
    if age_group == "youth":
        protocol_avoid_ids.update({"root_lock_breath", "bellows_breath"})

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

        score = 0

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

# Fraction of the *asana* budget (what is left after the fixed blocks below) that
# each section receives.
_SECTION_SPLIT = {"warmup": 0.22, "main": 0.55, "cooldown": 0.23}

# Held final relaxation and seated meditation scale with session length rather
# than sitting at a fixed 5 and 7 minutes, which would eat a third of a short
# practice. (minutes_available_upper_bound, savasana_seconds, dharana_seconds)
_CLOSING_BUDGET = [
    (15,  120, 120),
    (20,  180, 180),
    (30,  240, 300),
    (45,  300, 420),
    (999, 420, 600),
]


# Surya Namaskar, pranayama, meditation and final relaxation together may not
# take more than this share of a session — the rest belongs to asana.
_MAX_FIXED_BLOCK_SHARE = 0.55


def _scale_surya_namaskar(sns: dict | None, scale: float) -> tuple[dict | None, int]:
    """Shrink a Surya Namaskar block to fit a short session, by dropping rounds."""
    if not sns or not sns.get("rounds"):
        return sns, 0
    rounds = max(1, int(sns["rounds"] * scale))
    if rounds == sns["rounds"]:
        return sns, int(sns.get("duration_minutes", 0) * 60)
    scaled = dict(sns)
    scaled["rounds"] = rounds
    scaled["duration_minutes"] = round((rounds * 12 * 5) / 60 + (rounds - 1) * 0.25, 1)
    return scaled, int(scaled["duration_minutes"] * 60)


def _closing_budget(mins: int) -> tuple[int, int]:
    for upper, sav, dharana in _CLOSING_BUDGET:
        if mins <= upper:
            return sav, dharana
    return _CLOSING_BUDGET[-1][1], _CLOSING_BUDGET[-1][2]


# No pose other than the closing relaxation is held longer than this. The week-3
# progression multiplier applied to an already-long restorative hold (Legs Up The
# Wall, Constructive Rest) produced six-minute single poses, which alone
# overran a 20-minute session.
_MAX_POSE_HOLD_SECONDS = 240


def pose_hold_seconds(pose: dict, experience: str, week: int, age_group: str = "adult") -> int:
    """Per-side hold for one pose, after week progression and age scaling.

    """
    durs = pose.get("duration_seconds", {})
    base = durs.get(experience, durs.get("beginner", 30))
    hold = _week_hold(base, week)
    if age_group == "senior":
        hold = int(hold * 0.75)
    return max(min(hold, _MAX_POSE_HOLD_SECONDS), 10)


def pose_total_seconds(pose: dict, experience: str, week: int, age_group: str = "adult") -> int:
    """Wall-clock cost of a pose in a sequence — both sides if it is unilateral.

    Unilateral poses were previously budgeted (and displayed) as a single hold,
    so Tree Pose counted 30 seconds for what is really 30 seconds *per side*.
    That understated every session and, practised as written, would have built
    left-right asymmetry.
    """
    return pose_hold_seconds(pose, experience, week, age_group) * pose_sides(pose)


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

# Below this many safe poses, a 4-week plan cannot avoid repeating heavily. The
# plan says so rather than presenting the repetition as the intended design.
_MIN_VARIED_POOL = 30

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
                    exclude_ids=None, min_poses=1, max_poses=14):
    """Take poses from a deterministically shuffled pool until the budget is met.

    Stops once adding another pose would overshoot by more than half its own
    length, so a section lands close to its budget from either side.
    """
    excl = set(exclude_ids or ())
    candidates = _det_shuffle([p for p in pool if p["id"] not in excl], seed_key)

    # A single pose must not be able to swallow the whole section. The long
    # restorative holds (Legs Up The Wall, Constructive Rest) run 4-5 minutes,
    # which is longer than the entire cooldown budget of a short session — so
    # prefer poses that fit, and fall back to the cheapest available rather than
    # to whatever the shuffle happened to put first.
    affordable = [p for p in candidates
                  if pose_total_seconds(p, exp, week, age_group) <= budget_seconds]
    if affordable:
        candidates = affordable
    else:
        candidates = sorted(candidates,
                            key=lambda p: pose_total_seconds(p, exp, week, age_group))

    chosen, used = [], 0
    for pose in candidates:
        if len(chosen) >= max_poses:
            break
        cost = pose_total_seconds(pose, exp, week, age_group)
        # Once the minimum is met, only overshoot when the pose lands closer to
        # the budget than stopping short would. Short sessions have little slack.
        if used + cost > budget_seconds and len(chosen) >= min_poses:
            if (used + cost) - budget_seconds > budget_seconds - used:
                break
        chosen.append(pose)
        used += cost
        if used >= budget_seconds and len(chosen) >= min_poses:
            break
    return chosen


def _hold_multiplier(poses, budget_seconds, exp, week, age_group, cap: float) -> float:
    """How much to lengthen holds so a section reaches its time budget.

    Returns 1.0 when the poses already fill the budget. Capped, because a hold
    stretched indefinitely stops being the same pose.
    """
    used = sum(pose_total_seconds(p, exp, week, age_group) for p in poses)
    if used <= 0 or used >= budget_seconds:
        return 1.0
    return round(min(budget_seconds / used, cap), 2)


def build_sequence(filtered_poses, yoga_prefs, user_profile, day_num: int, week: int,
                   user_id: str, week_allowed_levels: list | None = None,
                   asana_budget_seconds: int | None = None,
                   savasana_seconds: int | None = None,
                   age_group: str = "adult"):
    mins = yoga_prefs.get("time_available_minutes", 30)
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    if asana_budget_seconds is None:
        sav_s, dharana_s = _closing_budget(mins)
        asana_budget_seconds = max(mins * 60 - sav_s - dharana_s, 300)
        savasana_seconds = sav_s
    savasana_seconds = savasana_seconds or _closing_budget(mins)[0]

    # Progressive week-level filtering
    pose_pool = filtered_poses
    if week_allowed_levels:
        narrowed = [p for p in filtered_poses if p.get("level", "beginner") in week_allowed_levels]
        # Only honour the week gate if it still leaves enough material to fill a
        # session; otherwise fall back rather than silently shipping a short one.
        if sum(pose_total_seconds(p, exp, week, age_group) for p in narrowed) >= asana_budget_seconds:
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
    pool_limited = False
    if not styled_main:
        styled_main = [p for p in pose_pool if selectable(p)
                       and p.get("sequence_role") != "warmup"]
        pool_limited = True
    if not styled_main:
        styled_main = [p for p in pose_pool if selectable(p)]
        pool_limited = True

    # Savasana is already priced out of the asana budget by the caller, so the
    # cooldown share must not subtract it a second time.
    main_budget     = int(asana_budget_seconds * _SECTION_SPLIT["main"])
    warmup_budget   = int(asana_budget_seconds * _SECTION_SPLIT["warmup"])
    cooldown_budget = int(asana_budget_seconds * _SECTION_SPLIT["cooldown"])

    # The main sequence claims the pool first. Filling warmup first meant that on
    # a heavily restricted profile the handful of safe poses were spent on the
    # warm-up and the main sequence came out empty.
    # A very short session cannot afford a three-pose minimum without blowing
    # past the time the user actually has.
    # A minimum of two poses is meaningless if two poses do not fit — an advanced
    # practitioner holds for 60-90s a side, so a 15-minute session can only
    # afford one main pose once the fixed blocks are paid for.
    cheapest = sorted(pose_total_seconds(p, exp, week, age_group) for p in styled_main)[:2]
    main_min = 1 if sum(cheapest) > main_budget else max(2, min(3, main_budget // 90))
    # Pose counts scale with the time available. A fixed cap meant a 45-minute
    # session ran out of poses long before it ran out of budget and landed short.
    main_seq = _fill_to_budget(styled_main, main_budget, exp, week, age_group,
                               f"{user_id}-main-d{day_num}-w{week}",
                               min_poses=main_min,
                               max_poses=max(4, min(18, main_budget // 45)))
    main_seq = _arc_sort(main_seq)
    all_used = {p["id"] for p in main_seq}

    # Opening pose rotates across the 28 sessions instead of being Child's Pose
    # in every one of them.
    openers = [p for p in warmup_pool
               if p["english_name"] in _GROUNDING_OPENERS and p["id"] not in all_used]
    warmup = []
    if openers:
        ordered = _det_shuffle(openers, f"{user_id}-opener-w{week}")
        warmup = [ordered[(day_num - 1) % len(ordered)]]
    all_used.update(p["id"] for p in warmup)
    used_warm = sum(pose_total_seconds(p, exp, week, age_group) for p in warmup)
    warmup += _fill_to_budget(warmup_pool, warmup_budget - used_warm, exp, week, age_group,
                              f"{user_id}-warmup-d{day_num}-w{week}",
                              exclude_ids=all_used, min_poses=1,
                              max_poses=max(2, min(6, warmup_budget // 45)))
    warmup = _arc_sort(warmup)
    all_used.update(p["id"] for p in warmup)

    cooldown = _fill_to_budget(cooldown_pool, cooldown_budget, exp, week, age_group,
                               f"{user_id}-cooldown-d{day_num}-w{week}",
                               exclude_ids=all_used, min_poses=1,
                               max_poses=max(2, min(6, cooldown_budget // 45)))
    cooldown = _arc_sort(cooldown)
    all_used.update(p["id"] for p in cooldown)

    # Counterposing is judged across the whole practice, not the main sequence
    # alone — the cooldown usually already resolves the peak. Only when nothing
    # after the last backbend or inversion neutralises it do we add one.
    cooldown = _add_counterpose(main_seq, cooldown, cooldown_pool, exp, week, age_group,
                                f"{user_id}-counter-d{day_num}-w{week}", all_used)
    all_used.update(p["id"] for p in cooldown)

    # Falling short of the minimum means the pool ran dry — not merely that the
    # session was short, which is a legitimate outcome of a 15-minute request.
    if len(main_seq) < main_min:
        pool_limited = True

    # Where the pool runs out before the budget does, hold longer rather than
    # shipping a short session. This is what a teacher does with a small safe
    # repertoire, and it is why a 45-minute beginner practice is not 40 poses.
    holds = {
        "warmup":   _hold_multiplier(warmup, warmup_budget, exp, week, age_group, 1.6),
        "main":     _hold_multiplier(main_seq, main_budget, exp, week, age_group, 2.0),
        "cooldown": _hold_multiplier(cooldown, cooldown_budget, exp, week, age_group, 2.5),
    }

    if savasana_pool:
        cooldown.append(savasana_pool[0])

    return {"warmup": warmup, "main": main_seq, "cooldown": cooldown,
            "savasana_seconds": savasana_seconds, "pool_limited": pool_limited,
            "hold_multipliers": holds}


# ── Pose formatter ────────────────────────────────────────────────────────────

def format_pose(pose: dict, experience: str, week: int, age_group: str = "adult",
                hold_override: int | None = None) -> dict:
    hold = hold_override if hold_override is not None else \
        pose_hold_seconds(pose, experience, week, age_group)
    sides = pose_sides(pose)
    return {
        "pose_id":             pose.get("id"),
        "pose_name":           pose.get("english_name"),
        "sanskrit_name":       pose.get("sanskrit_name"),
        "category":            pose.get("category"),
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
        "modification":        _get_modification(pose, experience, age_group),
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

    def _hold(pose, section):
        # The cap has to be re-applied after the section multiplier, or a pose
        # already at the ceiling gets stretched straight past it.
        stretched = pose_hold_seconds(pose, exp, week, age_group) * mult.get(section, 1.0)
        return int(min(stretched, _MAX_POSE_HOLD_SECONDS))

    warmup_fmt = [format_pose(p, exp, week, age_group, hold_override=_hold(p, "warmup"))
                  for p in sequence["warmup"]]
    main_fmt   = [format_pose(p, exp, week, age_group, hold_override=_hold(p, "main"))
                  for p in sequence["main"]]
    # The closing relaxation is held for the session's budgeted savasana time,
    # not the pose's own default.
    sav_seconds  = sequence.get("savasana_seconds")
    cooldown_fmt = [
        format_pose(p, exp, week, age_group,
                    hold_override=sav_seconds if p.get("final_relaxation")
                    else _hold(p, "cooldown"))
        for p in sequence["cooldown"]
    ]

    pranayama_section = []
    for pr in pranayama:
        durs = pr.get("duration_minutes", {})
        pr_minutes = durs.get(exp, durs.get("beginner", 3))
        # The KB duration is what the technique deserves in a full practice. In a
        # short session it has to fit the budget — an advanced Alternate Nostril
        # is 10 minutes, which is most of a 15-minute session on its own.
        if pranayama_seconds:
            pr_minutes = min(pr_minutes, max(round(pranayama_seconds / 60), 2))
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
        sns = _build_surya_namaskar_block(user_profile, yoga_prefs, contra_tags or set(), age_group)

    # Dharana/meditation slot — dosha-matched, scaled to the session length
    dharana = dict(_DHARANA.get(dosha, _DHARANA["vata"]))
    if dharana_seconds:
        dharana["duration_minutes"] = max(round(dharana_seconds / 60), 2)

    # Every block that costs the practitioner wall-clock time counts toward the
    # estimate. Surya Namaskar (2-8 min) and Dharana (2-10 min) used to be left
    # out, so the figure shown did not even match the session's own content.
    asana_secs  = sum(p["total_duration_seconds"] for p in warmup_fmt + main_fmt + cooldown_fmt)
    prana_secs  = sum(p["duration_minutes"] * 60 for p in pranayama_section)
    sns_secs    = int((sns or {}).get("duration_minutes", 0) * 60)
    dharana_sec = int(dharana.get("duration_minutes", 0) * 60)
    total_secs  = asana_secs + prana_secs + sns_secs + dharana_sec

    return {
        "surya_namaskar":    sns,
        "warmup":            warmup_fmt,
        "main_sequence":     main_fmt,
        "cooldown":          cooldown_fmt,
        "pranayama_section": pranayama_section,
        "dharana_section":   dharana,
        "total_duration_minutes":         yoga_prefs.get("time_available_minutes", 30),
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

    # Select top 3 pranayamas for this user
    pranayamas = select_pranayama(user_profile, yoga_prefs, pl, count=3,
                                  protocol_map=effective_proto_map)

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
    # classical Dinacharya prescribes sadhana every day, and the week-to-week
    # feedback loop is what protects against overload now: "too hard" or
    # "drained" pulls the following week's intensity down automatically.
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
    savasana_seconds, dharana_seconds = _closing_budget(session_minutes)
    sns_block = _build_surya_namaskar_block(user_profile, yoga_prefs,
                                           user_contra_tags, age_group)
    sns_seconds = int((sns_block or {}).get("duration_minutes", 0) * 60)
    # Days rotate through the selected pranayamas and they are not all the same
    # length, so the budget has to price the longest one — otherwise the days
    # that draw a longer technique overshoot the session the user asked for.
    prana_seconds = 0
    for _pr in pranayamas:
        _pd = _pr.get("duration_minutes", {})
        prana_seconds = max(prana_seconds,
                            int(_pd.get(user_exp, _pd.get("beginner", 3)) * 60))
    # The fixed blocks can exceed the whole session — an advanced practitioner
    # asking for 15 minutes draws 4 rounds of Surya Namaskar and a long
    # pranayama, which together with the closing already overruns the request.
    # Trim them to fit rather than flooring the asana budget and overshooting,
    # so a 15-minute session is 15 minutes of practice.
    session_seconds = session_minutes * 60
    fixed_seconds = sns_seconds + prana_seconds + savasana_seconds + dharana_seconds
    max_fixed = int(session_seconds * _MAX_FIXED_BLOCK_SHARE)
    if fixed_seconds > max_fixed:
        scale = max_fixed / fixed_seconds
        prana_seconds = max(int(prana_seconds * scale), 60)
        dharana_seconds = max(int(dharana_seconds * scale), 90)
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
                seq = build_sequence(filtered_poses, yoga_prefs, user_profile,
                                     day_num=i, week=week, user_id=user_id,
                                     week_allowed_levels=week_levels,
                                     asana_budget_seconds=asana_budget,
                                     savasana_seconds=savasana_seconds,
                                     age_group=age_group)
                # Rotate through all 3 pranayamas deterministically per day (variety)
                if pranayamas:
                    day_prana = [pranayamas[(i - 1) % len(pranayamas)]]
                else:
                    day_prana = []

                day_plan = build_yoga_day(seq, day_prana, yoga_prefs, user_profile,
                                          week, age_group=age_group,
                                          contra_tags=user_contra_tags,
                                          dharana_seconds=dharana_seconds,
                                          sns=sns_block,
                                          pranayama_seconds=prana_seconds)
                week_days.append({"day": i, "day_name": day_name, "session": day_plan, "rest": False})

        four_week_plan.append({
            "week":  week,
            "theme": cfg["theme"],
            "note":  cfg["note"],
            "days":  week_days,
        })

    # If safety filtering left too little material to build a full practice from,
    # say so plainly. The alternative — silently shipping a short session — reads
    # as a thin product rather than as the safety decision it actually is.
    pool_notice = None
    if len(filtered_poses) < _MIN_VARIED_POOL or any(
            d["session"] and d["session"].get("pool_limited")
            for w in four_week_plan for d in w["days"]):
        pool_notice = (
            "Your health conditions rule out a large part of the pose library, so this "
            "plan is built from the smaller set that is safe for you. Sessions are "
            "shorter and repeat more often than usual by design. A qualified yoga "
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
        "disclaimer":         disclaimer,
        "enriched":           False,
    }
