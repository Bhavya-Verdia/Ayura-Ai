import json
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSES_PATH = BASE_DIR / "data" / "knowledge_base" / "yoga_poses.json"
PRANAYAMA_PATH = BASE_DIR / "data" / "knowledge_base" / "pranayama.json"

yoga_poses = []
if POSES_PATH.exists():
    with open(POSES_PATH, "r", encoding="utf-8") as f:
        yoga_poses = json.load(f)

pranayama_list = []
if PRANAYAMA_PATH.exists():
    with open(PRANAYAMA_PATH, "r", encoding="utf-8") as f:
        pranayama_list = json.load(f)


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


def _get_modification(pose: dict, experience: str) -> str:
    cat = pose.get("category", "standing")
    mods = _MODIFICATIONS.get(cat, _DEFAULT_MOD)
    return mods.get(experience, _DEFAULT_MOD.get(experience, "Use props as needed."))


# ── 4-week progressive structure ──────────────────────────────────────────────

_WEEK_CONFIG = {
    1: {"theme": "Foundation",  "hold_mult": 1.0,  "note": "Focus on alignment and finding the pose. Use props freely. Quality over depth."},
    2: {"theme": "Deepen",      "hold_mult": 1.25, "note": "Extend hold times by 25%. Notice where the body resists — breathe into those areas."},
    3: {"theme": "Challenge",   "hold_mult": 1.5,  "note": "Peak week — longer holds and fuller range. Try the advanced modification on one pose per session."},
    4: {"theme": "Integration", "hold_mult": 1.1,  "note": "Consolidate. Practice flows smoothly with confident breath. Add 10% hold time, reduce mental effort."},
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

def filter_poses(user_profile, yoga_prefs, poses):
    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"
    allowed_levels = level_map.get(user_exp, ["beginner"])

    is_pregnant = user_profile.get("pregnancy_or_nursing", False)

    user_injuries = set(user_profile.get("injuries_or_limitations") or [])
    mapped = set()
    for inj in user_injuries:
        i = inj.lower()
        if "bad_knee" in i or "knee" in i:              mapped.update(["knee_injury", "knee_replacement"])
        if "lower_back" in i or "back" in i:             mapped.update(["lower_back_pain", "herniated_disc", "serious_back_injury"])
        if "shoulder" in i:                               mapped.update(["shoulder_injury", "rotator_cuff"])
        if "neck" in i:                                   mapped.update(["neck_injury", "cervical_spondylosis", "serious_neck_injury"])
        if "hypertension" in i or "blood_pressure" in i: mapped.update(["high_blood_pressure", "hypertension"])
        if "heart" in i:                                  mapped.update(["heart_disease"])
        if "glaucoma" in i:                               mapped.update(["glaucoma"])
        if "ankle" in i:                                  mapped.update(["ankle_injury"])
        if "groin" in i:                                  mapped.update(["groin_injury"])

    # Use Vikriti for scoring (what needs correcting now), fall back to Prakriti
    vikriti = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha", "vata")
    yoga_goal = yoga_prefs.get("yoga_goal", "flexibility")

    scored = []
    for pose in poses:
        if pose.get("level", "intermediate") not in allowed_levels:
            continue
        if is_pregnant and not pose.get("pregnancy_safe", True):
            continue
        if mapped.intersection(set(pose.get("contraindications", []))):
            continue

        score = 0
        d_val = pose.get("dosha_balance", {}).get(vikriti, "neutral")
        if d_val == "balances":    score += 3
        elif d_val == "neutral":   score += 1
        elif d_val == "aggravates": score -= 2

        if yoga_goal in pose.get("goals", []):
            score += 2

        # Always keep Savasana / Corpse in pool
        name = pose.get("english_name", "").lower()
        if "corpse" in name or "savasana" in name:
            score += 50

        scored.append((score, pose))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:80]]


# ── Pranayama selection ───────────────────────────────────────────────────────

def select_pranayama(user_profile, yoga_prefs, pranayama_db, count=3):
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    user_exp = yoga_prefs.get("yoga_experience", "beginner")
    if user_exp == "none":
        user_exp = "beginner"

    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    allowed_levels = level_map.get(user_exp, ["beginner"])
    vikriti = user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha", "vata")
    yoga_goal = yoga_prefs.get("yoga_goal", "stress_relief")

    scored = []
    for pr in pranayama_db:
        if is_pregnant and not pr.get("pregnancy_safe", True):
            continue
        if pr.get("level", "beginner") not in allowed_levels:
            continue

        score = 0
        de = pr.get("dosha_effect", {}).get(vikriti, "neutral")
        if de == "balances":    score += 2
        elif de == "neutral":   score += 1
        elif de == "aggravates": score -= 2

        ptype = pr.get("type", "balancing")
        if yoga_goal == "stress_relief" and ptype in ["balancing", "grounding"]: score += 2
        if yoga_goal in ["energy", "strength"] and ptype == "energizing":        score += 2
        if yoga_goal == "healing" and ptype == "balancing":                       score += 2
        if yoga_goal == "flexibility" and ptype == "grounding":                   score += 1
        if yoga_goal == "spiritual" and ptype == "balancing":                     score += 2

        scored.append((score, pr))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:count]]


# ── Sequence builder ──────────────────────────────────────────────────────────

def build_sequence(filtered_poses, yoga_prefs, user_profile, day_num: int, week: int, user_id: str):
    mins = yoga_prefs.get("time_available_minutes", 30)
    if mins <= 15:   w_c, m_c, c_c = 2, 2, 1
    elif mins <= 20: w_c, m_c, c_c = 2, 3, 2
    elif mins <= 30: w_c, m_c, c_c = 3, 5, 2
    elif mins <= 45: w_c, m_c, c_c = 3, 8, 3
    else:            w_c, m_c, c_c = 4, 10, 4

    # Last cooldown slot reserved for Savasana
    other_c = max(c_c - 1, 0)

    warmup_pool   = [p for p in filtered_poses if p.get("sequence_role") == "warmup"
                     or (p.get("category") in ["standing", "seated"] and p.get("level") == "beginner")]
    cooldown_pool = [p for p in filtered_poses if p.get("sequence_role") == "cooldown"
                     or p.get("category") in ["supine", "forward_fold", "restorative"]]
    savasana_pool = [p for p in filtered_poses
                     if "corpse" in p.get("english_name", "").lower()
                     or "savasana" in p.get("sanskrit_name", "").lower()]
    main_pool     = [p for p in filtered_poses if p.get("sequence_role") == "main"]

    styles = yoga_prefs.get("yoga_style_preference") or ["hatha"]
    style = styles[0] if styles else "hatha"

    def style_ok(p):
        cat = p.get("category")
        if style == "hatha":        return True
        elif style == "vinyasa":    return cat in ["standing", "balancing"]
        elif style == "restorative": return cat in ["restorative", "supine", "forward_fold", "seated"]
        elif style == "yin":        return cat in ["forward_fold", "supine", "seated", "restorative"]
        elif style == "power":      return cat in ["standing", "inversion", "backbend", "balancing"]
        elif style == "ashtanga":   return cat in ["standing", "balancing", "inversion"]
        return True

    # For restorative/yin styles also pull from cooldown-category poses
    # (most restorative poses have sequence_role="cooldown" by convention)
    if style in ("restorative", "yin"):
        extended_pool = [p for p in filtered_poses if style_ok(p)]
        styled_main = extended_pool if len(extended_pool) >= m_c else main_pool
    else:
        styled_main = [p for p in main_pool if style_ok(p)] or main_pool

    def pick(pool, n, tag, exclude_ids=None):
        excl = exclude_ids or set()
        candidates = _det_shuffle([p for p in pool if p["id"] not in excl],
                                   f"{user_id}-{tag}-d{day_num}-w{week}")
        return candidates[:n]

    # Warmup — pin a grounding pose first
    grounding = [p for p in warmup_pool if p["english_name"] in ["Mountain Pose", "Easy Pose", "Child's Pose"]]
    warmup = grounding[:1]
    warmup_ids = {p["id"] for p in warmup}
    warmup += pick([p for p in warmup_pool if p["id"] not in warmup_ids], w_c - len(warmup), "warmup")
    all_used = {p["id"] for p in warmup}

    # Main
    main_seq = pick([p for p in styled_main if p["id"] not in all_used], m_c, "main")
    all_used.update(p["id"] for p in main_seq)

    # Cooldown (non-Savasana slots)
    non_sav = [p for p in cooldown_pool
               if p["id"] not in all_used
               and "corpse" not in p.get("english_name", "").lower()
               and "savasana" not in p.get("sanskrit_name", "").lower()]
    cooldown = pick(non_sav, other_c, "cooldown")
    all_used.update(p["id"] for p in cooldown)

    # Always end with Savasana
    sav_candidates = [p for p in savasana_pool if p["id"] not in all_used] or savasana_pool
    if sav_candidates:
        cooldown.append(sav_candidates[0])

    return {"warmup": warmup, "main": main_seq, "cooldown": cooldown}


# ── Pose formatter ────────────────────────────────────────────────────────────

def format_pose(pose: dict, experience: str, week: int) -> dict:
    durs = pose.get("duration_seconds", {})
    base = durs.get(experience, durs.get("beginner", 30))
    return {
        "pose_id":           pose.get("id"),
        "pose_name":         pose.get("english_name"),
        "sanskrit_name":     pose.get("sanskrit_name"),
        "category":          pose.get("category"),
        "duration_seconds":  _week_hold(base, week),
        "instructions":      pose.get("instructions", []),           # array, not blob
        "primary_benefits":  pose.get("primary_benefits", []),
        "modification":      _get_modification(pose, experience),    # meaningful, per-category
        "pranayama_sync":    pose.get("pranayama_sync", "Breathe steadily"),
        "ayurvedic_rationale": pose.get("ayurvedic_rationale", ""),
        "image_url":         pose.get("image_url", ""),
        "body_parts":        pose.get("body_parts", []),
    }


# ── Day builder ───────────────────────────────────────────────────────────────

def build_yoga_day(sequence: dict, pranayama: list, yoga_prefs: dict,
                   user_profile: dict, week: int) -> dict:
    exp = yoga_prefs.get("yoga_experience", "beginner")
    if exp == "none":
        exp = "beginner"

    dosha = user_profile.get("dominant_dosha", "vata")
    goal = yoga_prefs.get("yoga_goal", "flexibility").replace("_", " ")
    if dosha == "vata":    theme = f"Grounding & Warming {goal.title()} Practice"
    elif dosha == "pitta": theme = f"Cooling & Calming {goal.title()} Flow"
    else:                  theme = f"Energising & Invigorating {goal.title()} Sequence"

    warmup_fmt   = [format_pose(p, exp, week) for p in sequence["warmup"]]
    main_fmt     = [format_pose(p, exp, week) for p in sequence["main"]]
    cooldown_fmt = [format_pose(p, exp, week) for p in sequence["cooldown"]]

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

    total_secs = sum(p["duration_seconds"] for p in warmup_fmt + main_fmt + cooldown_fmt)
    total_prana = sum(p["duration_minutes"] * 60 for p in pranayama_section)

    return {
        "warmup":            warmup_fmt,
        "main_sequence":     main_fmt,
        "cooldown":          cooldown_fmt,
        "pranayama_section": pranayama_section,
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

def generate_yoga_plan(user_profile, yoga_prefs, yoga_poses_db=None, pranayama_list_db=None):
    yp = yoga_poses_db if yoga_poses_db is not None else yoga_poses
    pl = pranayama_list_db if pranayama_list_db is not None else pranayama_list

    filtered_poses = filter_poses(user_profile, yoga_prefs, yp)
    pranayamas = select_pranayama(user_profile, yoga_prefs, pl, count=3)

    time_of_day = yoga_prefs.get("time_of_day_preference", "morning")
    if time_of_day == "morning":   rest_days = {3, 7}
    elif time_of_day == "evening": rest_days = {4, 7}
    else:                          rest_days = {7}

    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    four_week_plan = []
    for week in range(1, 5):
        cfg = _WEEK_CONFIG[week]
        week_days = []
        for i in range(1, 8):
            day_name = days_of_week[i - 1]
            if i in rest_days:
                week_days.append({"day": i, "day_name": day_name, "session": None, "rest": True})
            else:
                seq = build_sequence(filtered_poses, yoga_prefs, user_profile,
                                     day_num=i, week=week, user_id=user_id)
                # Rotate pranayama deterministically per day
                if pranayamas:
                    seed = int(hashlib.md5(f"{user_id}-prana-d{i}-w{week}".encode()).hexdigest(), 16)
                    day_prana = [pranayamas[seed % len(pranayamas)]]
                else:
                    day_prana = []
                day_plan = build_yoga_day(seq, day_prana, yoga_prefs, user_profile, week)
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
            "dominant_dosha":   dominant_dosha,
            "yoga_goal":        yoga_prefs.get("yoga_goal", "flexibility"),
            "experience":       yoga_prefs.get("yoga_experience", "beginner"),
            "style_preference": yoga_prefs.get("yoga_style_preference", ["hatha"]),
            "time_available":   yoga_prefs.get("time_available_minutes", 30),
            "time_of_day":      time_of_day,
        },
        "weekly_schedule": four_week_plan[0]["days"],  # backwards compat
        "four_week_plan":  four_week_plan,
        "ayurvedic_tips":  get_ayurvedic_tips(dominant_dosha),
        "disclaimer":      disclaimer,
        "enriched":        False,
    }
