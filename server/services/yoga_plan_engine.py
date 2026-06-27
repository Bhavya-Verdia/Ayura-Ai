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

    # Pregnancy: skip entirely
    if user_profile.get("pregnancy_or_nursing"):
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
    "epilepsy":            {"heart_disease"},
    "osteoporosis":        {"serious_spinal_injury"},
    "hernia":              {"knee_injury"},
    "retinal_detachment":  {"glaucoma"},
    "migraine":            {"high_blood_pressure"},
    "post_cardiac":        {"heart_disease", "high_blood_pressure"},
    "heart_surgery_recovery": {"heart_disease", "high_blood_pressure"},
    "vertigo":             {"high_blood_pressure"},
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
    "wrist":           {"shoulder_injury"},
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

def filter_poses(user_profile, yoga_prefs, poses, max_allowed_levels=None, protocol_map=None):
    if protocol_map is None:
        protocol_map = _PROTOCOL_MAP

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

    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    contra_tags = _build_contra_set(user_profile, age_group)
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

    # Protocol priority pose IDs for this user's conditions
    protocol_priority_ids: set[str] = set()
    for cond in user_conditions:
        if cond in _FEMALE_ONLY_PROTOCOLS and gender in ("male", "m"):
            continue
        proto = protocol_map.get(cond)
        if proto:
            protocol_priority_ids.update(proto.get("priority_pose_ids", []))

    scored = []
    for pose in poses:
        if pose.get("level", "intermediate") not in allowed_levels:
            continue
        if is_pregnant and not pose.get("pregnancy_safe", True):
            continue

        pose_contra = set(pose.get("contraindications", [])) | set(pose.get("medical_conditions_contraindicated", []))
        if contra_tags.intersection(pose_contra):
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

    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
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


# ── Sequence builder ──────────────────────────────────────────────────────────

def build_sequence(filtered_poses, yoga_prefs, user_profile, day_num: int, week: int,
                   user_id: str, week_allowed_levels: list | None = None):
    mins = yoga_prefs.get("time_available_minutes", 30)
    if mins <= 15:   w_c, m_c, c_c = 2, 2, 1
    elif mins <= 20: w_c, m_c, c_c = 2, 3, 2
    elif mins <= 30: w_c, m_c, c_c = 3, 5, 2
    elif mins <= 45: w_c, m_c, c_c = 3, 8, 3
    else:            w_c, m_c, c_c = 4, 10, 4

    other_c = max(c_c - 1, 0)

    # Progressive week-level filtering
    pose_pool = filtered_poses
    if week_allowed_levels:
        pose_pool = [p for p in filtered_poses if p.get("level", "beginner") in week_allowed_levels]
        if len(pose_pool) < (w_c + m_c + c_c):
            pose_pool = filtered_poses  # fallback if too restrictive

    warmup_pool   = [p for p in pose_pool if p.get("sequence_role") == "warmup"
                     or (p.get("category") in ["standing", "seated", "restorative"] and p.get("level") == "beginner")]
    cooldown_pool = [p for p in pose_pool if p.get("sequence_role") == "cooldown"
                     or p.get("category") in ["supine", "forward_fold", "restorative"]]
    savasana_pool = [p for p in pose_pool
                     if "corpse" in p.get("english_name", "").lower()
                     or "savasana" in p.get("sanskrit_name", "").lower()]
    main_pool     = [p for p in pose_pool if p.get("sequence_role") == "main"]

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
        extended_pool = [p for p in pose_pool if style_ok(p)]
        styled_main = extended_pool if len(extended_pool) >= m_c else main_pool
    else:
        styled_main = [p for p in main_pool if style_ok(p)] or main_pool

    def pick(pool, n, tag, exclude_ids=None):
        excl = exclude_ids or set()
        candidates = _det_shuffle([p for p in pool if p["id"] not in excl],
                                   f"{user_id}-{tag}-d{day_num}-w{week}")
        return candidates[:n]

    grounding = [p for p in warmup_pool if p["english_name"] in ["Mountain Pose", "Easy Pose", "Child's Pose"]]
    warmup = grounding[:1]
    warmup_ids = {p["id"] for p in warmup}
    warmup += pick([p for p in warmup_pool if p["id"] not in warmup_ids], w_c - len(warmup), "warmup")
    all_used = {p["id"] for p in warmup}

    main_seq = pick([p for p in styled_main if p["id"] not in all_used], m_c, "main")
    all_used.update(p["id"] for p in main_seq)

    non_sav = [p for p in cooldown_pool
               if p["id"] not in all_used
               and "corpse" not in p.get("english_name", "").lower()
               and "savasana" not in p.get("sanskrit_name", "").lower()]
    cooldown = pick(non_sav, other_c, "cooldown")
    all_used.update(p["id"] for p in cooldown)

    sav_candidates = [p for p in savasana_pool if p["id"] not in all_used] or savasana_pool
    if sav_candidates:
        cooldown.append(sav_candidates[0])

    return {"warmup": warmup, "main": main_seq, "cooldown": cooldown}


# ── Pose formatter ────────────────────────────────────────────────────────────

def format_pose(pose: dict, experience: str, week: int, age_group: str = "adult") -> dict:
    durs = pose.get("duration_seconds", {})
    base = durs.get(experience, durs.get("beginner", 30))
    hold = _week_hold(base, week)
    # Senior: reduce hold times by 25%
    if age_group == "senior":
        hold = int(hold * 0.75)
    return {
        "pose_id":             pose.get("id"),
        "pose_name":           pose.get("english_name"),
        "sanskrit_name":       pose.get("sanskrit_name"),
        "category":            pose.get("category"),
        "duration_seconds":    hold,
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
                   contra_tags: set | None = None) -> dict:
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    dosha = user_profile.get("dominant_dosha", "vata")
    goal = yoga_prefs.get("yoga_goal", "flexibility").replace("_", " ")
    if dosha == "vata":    theme = f"Grounding & Warming {goal.title()} Practice"
    elif dosha == "pitta": theme = f"Cooling & Calming {goal.title()} Flow"
    else:                  theme = f"Energising & Invigorating {goal.title()} Sequence"

    warmup_fmt   = [format_pose(p, exp, week, age_group) for p in sequence["warmup"]]
    main_fmt     = [format_pose(p, exp, week, age_group) for p in sequence["main"]]
    cooldown_fmt = [format_pose(p, exp, week, age_group) for p in sequence["cooldown"]]

    pranayama_section = []
    for pr in pranayama:
        durs = pr.get("duration_minutes", {})
        pranayama_section.append({
            "technique_id":    pr.get("id"),
            "technique_name":  pr.get("english_name"),
            "sanskrit_name":   pr.get("sanskrit_name"),
            "duration_minutes": durs.get(exp, durs.get("beginner", 3)),
            "instructions":    pr.get("instructions", []),
            "dosha_note":      f"Balances {dosha.title()} — {pr.get('type', 'balancing')} pranayama.",
        })

    # Surya Namaskar block — morning sessions only
    sns = _build_surya_namaskar_block(user_profile, yoga_prefs, contra_tags or set(), age_group)

    # Dharana/meditation slot — dosha-matched
    dharana = dict(_DHARANA.get(dosha, _DHARANA["vata"]))

    total_secs = sum(p["duration_seconds"] for p in warmup_fmt + main_fmt + cooldown_fmt)
    total_prana = sum(p["duration_minutes"] * 60 for p in pranayama_section)

    return {
        "surya_namaskar":    sns,
        "warmup":            warmup_fmt,
        "main_sequence":     main_fmt,
        "cooldown":          cooldown_fmt,
        "pranayama_section": pranayama_section,
        "dharana_section":   dharana,
        "total_duration_minutes":         yoga_prefs.get("time_available_minutes", 30),
        "estimated_pose_time_minutes":    round((total_secs + total_prana) / 60, 1),
        "sequence_type":     yoga_prefs.get("time_of_day_preference", "morning"),
        "dosha_theme":       theme,
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
                       extra_protocols=None):
    yp = yoga_poses_db if yoga_poses_db is not None else yoga_poses
    pl = pranayama_list_db if pranayama_list_db is not None else pranayama_list

    # Thread-safe local protocol map (merge base + any dynamic protocols for unknown conditions)
    effective_proto_map = dict(_PROTOCOL_MAP)
    if extra_protocols:
        effective_proto_map.update(extra_protocols)

    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"

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
                                  protocol_map=effective_proto_map)

    # Select top 3 pranayamas for this user
    pranayamas = select_pranayama(user_profile, yoga_prefs, pl, count=3,
                                  protocol_map=effective_proto_map)

    # Safety transparency: which forceful/retention pranayama were excluded for this
    # user's conditions — surfaced in the UI so the exclusion is visible, not silent.
    _prana_exclusions = []
    _uc = set(c.lower() for c in (user_profile.get("medical_history") or []))
    _is_preg_x = user_profile.get("pregnancy_or_nursing", False)
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
                    "reason": "Pregnancy / nursing" if _preg_block else "Contraindicated for your health conditions",
                })

    time_of_day = yoga_prefs.get("time_of_day_preference", "morning")
    if time_of_day == "morning":   rest_days = {3, 7}
    elif time_of_day == "evening": rest_days = {4, 7}
    else:                          rest_days = {7}

    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
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

    four_week_plan = []
    for week in range(1, 5):
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
                                     week_allowed_levels=week_levels)
                # Rotate through all 3 pranayamas deterministically per day (variety)
                if pranayamas:
                    day_prana = [pranayamas[(i - 1) % len(pranayamas)]]
                else:
                    day_prana = []

                day_plan = build_yoga_day(seq, day_prana, yoga_prefs, user_profile,
                                          week, age_group=age_group,
                                          contra_tags=user_contra_tags)
                week_days.append({"day": i, "day_name": day_name, "session": day_plan, "rest": False})

        four_week_plan.append({
            "week":  week,
            "theme": cfg["theme"],
            "note":  cfg["note"],
            "days":  week_days,
        })

    disclaimer = (
        "PREGNANCY WARNING: Several poses have been removed for pregnancy safety. "
        "Please consult your doctor and a qualified yoga instructor before practice."
        if is_pregnant else
        "This plan is for general wellness guidance only. Consult a physician before beginning any new practice."
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
        "ayurvedic_tips":     get_ayurvedic_tips(dominant_dosha),
        "seasonal_note":      season_cfg.get("note") if season_cfg else None,
        "condition_protocols": active_protocols or None,
        "pranayama_safety_exclusions": _prana_exclusions or None,
        "disclaimer":         disclaimer,
        "enriched":           False,
    }
