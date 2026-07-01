from datetime import datetime, timezone
import json
import os
from core.kb_cache import kb_cache
from engine.condition_vocab import term_in_condition, normalize_condition


def _med_covers_condition(med: dict, user_cond: str) -> bool:
    """True if a medicine's `conditions` cover the user's condition — matching by
    exact string OR shared canonical vocabulary key (so 'diabetes_type2' matches a
    KB entry tagged 'diabetes')."""
    med_conds = [x.lower() for x in med.get("conditions", [])]
    if user_cond.lower() in med_conds:
        return True
    ucn = normalize_condition(user_cond)
    return any(normalize_condition(mc) == ucn for mc in med_conds)

# ── Medicines KB (loaded once at module import) ─────────────────────────────
_MEDICINES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base", "ayurvedic_medicines.json")
try:
    with open(_MEDICINES_PATH, "r") as _f:
        _MEDICINES_KB: list[dict] = json.load(_f)
except Exception:
    _MEDICINES_KB = []

# ── Home-remedies fallback (loaded once at module import) ────────────────────
# Remedies are normally served from Mongo (kb_ayurvedic_remedies, seeded by
# scripts/seed_remedies.py). Unlike the other features, the remedy engine had no
# offline fallback — so if that collection is unseeded, filter_remedies silently
# returned nothing. This bundled JSON (same shape, regenerated from the seed)
# keeps remedies working when kb_cache is empty. Mirrors the medicines KB above.
_REMEDIES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base", "home_remedies.json")
try:
    with open(_REMEDIES_PATH, "r") as _f:
        _REMEDIES_FALLBACK: list[dict] = json.load(_f)
except Exception:
    _REMEDIES_FALLBACK = []

# Onboarding symptom labels → remedy KB `symptom_id`. The onboarding picker uses
# plain-language values (acidity, cough, cold, hair_loss…) that don't exactly
# match the KB's clinical ids (acid_reflux, cough_wet, common_cold, hair_fall…),
# so ~half of selectable symptoms silently matched no remedy. This map bridges
# them; matching also falls through to the raw id, so KB-native ids still work.
_SYMPTOM_ALIASES: dict[str, str] = {
    "acidity": "acid_reflux",
    "acid": "acid_reflux",
    "heartburn": "acid_reflux",
    "skin_rash": "urticaria_hives",
    "rash": "urticaria_hives",
    "hives": "urticaria_hives",
    "weight_gain": "seasonal_detox",
    "hair_loss": "hair_fall",
    "hairfall": "hair_fall",
    "irregular_periods": "pcos_support",
    "irregular_menstruation": "pcos_support",
    "cough": "cough_wet",
    "wet_cough": "cough_wet",
    "cold": "common_cold",
    "common_cold_cough": "common_cold",
    "indigestion": "loss_of_appetite",
    "stress": "stress_burnout",
    "burnout": "stress_burnout",
}

# Condition aliases to normalise user profile conditions to KB ids
_CONDITION_ALIAS: dict[str, str] = {
    "insulin_resistance": "diabetes",
    "type2_diabetes": "diabetes",
    "pre_diabetes": "diabetes",
    "hypothyroidism": "hypothyroid",
    "hyperthyroidism": "hyperthyroid",
    "pcod": "pcos",
    "ibs": "inflammatory_bowel_disease",
    "gerd": "gerd",
    "acid_reflux": "hyperacidity",
    "chronic_constipation": "constipation",
    "chronic_fatigue": "chronic_fatigue_syndrome",
    "ra": "rheumatoid_arthritis",
    "depression": "depression",
    "migraine": "headache",
    "cervical": "cervical_spondylosis",
}

# Drug-herb interactions — herb key (partial match) → blocked medication categories
_DRUG_HERB_MAP: dict[str, list[str]] = {
    "ashwagandha": ["thyroid_medication", "immunosuppressants", "sedatives"],
    "guggulu":     ["blood_thinners", "thyroid_medication"],
    "triphala":    ["blood_thinners", "diabetes_medication"],
    "ginger":      ["blood_thinners", "diabetes_medication"],
    "shatavari":   ["estrogen", "hormone_therapy"],
    "guduchi":     ["immunosuppressants", "diabetes_medication"],
    "brahmi":      ["sedatives", "antiepileptics"],
    "kanchanara":  ["thyroid_medication", "blood_thinners"],
}

def filter_remedies(user_profile: dict, symptom_input: dict) -> list:
    filtered_results = []

    # Use `or <default>` (not the .get default) so a present-but-null field —
    # e.g. current_medications: None on a user who never set meds — coerces to an
    # empty collection instead of None, which would blow up the `for … in` loops
    # below with "'NoneType' object is not iterable".
    symptoms = symptom_input.get("symptoms") or []
    severity = symptom_input.get("severity") or {}
    duration = symptom_input.get("duration") or {}

    pregnancy_or_nursing = user_profile.get("pregnancy_or_nursing", False)
    current_meds = user_profile.get("current_medications") or []
    medical_history = user_profile.get("medical_history") or []
    allergies = user_profile.get("allergies") or []
    dominant_dosha = user_profile.get("dominant_dosha", "vata").lower()
    secondary_dosha = user_profile.get("secondary_dosha", "pitta").lower()

    all_remedies = kb_cache.ayurvedic_remedies or _REMEDIES_FALLBACK

    for sym_id in symptoms:
        sym_sev = severity.get(sym_id, "mild")
        sym_dur = duration.get(sym_id, "recent")

        # a) Severity gate
        if sym_sev == "severe":
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "see_doctor",
                "message": "This symptom requires immediate medical attention. Please consult a doctor."
            })
            continue

        # Find remedy in KB (resolve onboarding labels to KB ids; fall back to raw)
        _sid = _SYMPTOM_ALIASES.get(str(sym_id).lower(), str(sym_id).lower())
        remedy_kb = next((r for r in all_remedies if r.get("symptom_id") == _sid), None)
        if not remedy_kb:
            continue

        # b) Duration gate
        requires_practitioner = (sym_dur in ["chronic", "months"])

        # c) Pregnancy filter
        if pregnancy_or_nursing and not remedy_kb.get("pregnancy_safe", False):
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "consult_doctor",
                "message": "Safe remedy not available during pregnancy. Please consult your Ayurvedic practitioner."
            })
            continue

        # dosha selection helper
        def is_safe(cand_remedy):
            if not cand_remedy:
                return False, None

            # Extract text to search for ingredients
            ingredients_list = cand_remedy.get("ingredients") or []
            ingredients_text = " ".join([i.get("item", "").lower() for i in ingredients_list])

            # e) Medical contraindication
            blocks = {
                "diabetes": ["guggulu", "honey"],
                "hypertension": ["salt", "ajwain", "stimulant"],
                "thyroid": ["ashwagandha"],
                "ibs": ["pippali", "trikatu"]
            }

            for cond in medical_history:
                cond_l = cond.lower()
                for key, blocked_items in blocks.items():
                    if key in cond_l:
                        for item in blocked_items:
                            if item in ingredients_text:
                                if key == "thyroid" and item == "ashwagandha":
                                    cand_remedy["caution_note"] = "Use Ashwagandha with caution due to thyroid history."
                                else:
                                    return False, f"Contraindicated for {cond}"

            # d) Drug interaction
            drug_interaction_map = {
                "ashwagandha": ["thyroid_medication", "immunosuppressants"],
                "guggulu": ["blood_thinners", "thyroid_medication"],
                "triphala": ["blood_thinners", "diabetes_medication"],
                "ginger": ["blood_thinners", "diabetes_medication"],
                "neem": ["diabetes_medication", "immunosuppressants"],
                "fenugreek": ["diabetes_medication", "blood_thinners"],
                "aloe_vera": ["diabetes_medication", "blood_thinners"],
                "tulsi": ["blood_thinners"]
            }

            for med in current_meds:
                med_l = med.lower().replace(" ", "_")
                for herb, interactions in drug_interaction_map.items():
                    if herb in ingredients_text:
                        for interaction in interactions:
                            if interaction in med_l:
                                return False, {"interaction_found": True, "medication": med, "herb": herb}

            # f) Allergy filter
            for allergy in allergies:
                if allergy.lower() in ingredients_text:
                    return False, f"Allergen {allergy} found"

            return True, None

        selected_remedy = None
        dosha_used = dominant_dosha
        candidate = remedy_kb.get("remedies", {}).get(dominant_dosha)

        interaction_warning = None

        safe, reason = is_safe(candidate)
        if not safe:
            if isinstance(reason, dict) and reason.get("interaction_found"):
                interaction_warning = reason
            dosha_used = secondary_dosha
            candidate = remedy_kb.get("remedies", {}).get(secondary_dosha)
            safe, reason = is_safe(candidate)
            if not safe:
                if isinstance(reason, dict) and reason.get("interaction_found"):
                    interaction_warning = reason
                candidate = remedy_kb.get("universal_remedy")
                dosha_used = "universal"
                safe, reason = is_safe(candidate)
                if not safe:
                    msg = {"symptom_id": sym_id, "action": "consult_doctor", "message": "No safe remedy available due to interactions/allergies."}
                    if isinstance(reason, dict):
                        msg.update(reason)
                    elif interaction_warning:
                        msg.update(interaction_warning)
                    filtered_results.append(msg)
                    continue

        selected_remedy = candidate
        if not selected_remedy:
            continue

        # Build result for this symptom
        filtered_results.append({
            "symptom_id": sym_id,
            "symptom_display": remedy_kb.get("symptom_display", sym_id),
            "severity": sym_sev,
            "duration": sym_dur,
            "dosha_cause": remedy_kb.get("dosha_cause", {}).get(dosha_used, ""),
            "remedy": selected_remedy,
            "requires_practitioner": requires_practitioner,
            "drug_interaction_warning": interaction_warning,
            "source": remedy_kb.get("source", "Traditional"),
            "dosha_used": dosha_used
        })

    return filtered_results

def build_remedy_plan(filtered_remedies: list, user_profile: dict, symptom_input: dict) -> dict:
    plan_id = f"remedy_{user_profile.get('id', 'usr')}_{int(datetime.now(timezone.utc).timestamp())}"
    dominant_dosha = user_profile.get("dominant_dosha", "vata").lower()

    symptoms_addressed = []
    doctor_referrals = []

    for res in filtered_remedies:
        if res.get("action") in ["see_doctor", "consult_doctor"]:
            doctor_referrals.append(res)
        else:
            symptoms_addressed.append(res)

    guidelines = {}
    if dominant_dosha == "vata":
        guidelines = {
            "diet_during_recovery": "Warm, cooked, oily foods. Avoid cold, raw, dry foods during recovery.",
            "lifestyle_notes": "Rest adequately. Maintain regular meal and sleep times.",
            "what_to_avoid": ["cold drinks", "raw salads", "skipping meals", "late nights"]
        }
    elif dominant_dosha == "pitta":
        guidelines = {
            "diet_during_recovery": "Cooling foods — coconut water, cucumber, sweet fruits. Avoid spicy and fermented foods.",
            "lifestyle_notes": "Avoid overheating. Rest in cool environment.",
            "what_to_avoid": ["spicy food", "alcohol", "excess sun", "competitive stress"]
        }
    else:
        guidelines = {
            "diet_during_recovery": "Light, warm, spiced foods. Avoid heavy, sweet, oily foods.",
            "lifestyle_notes": "Stay active. Avoid daytime sleep.",
            "what_to_avoid": ["cold dairy", "fried food", "excess sugar", "sedentary behavior"]
        }

    return {
        "plan_id": plan_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_dosha": dominant_dosha,
        "symptoms_addressed": symptoms_addressed,
        "doctor_referrals": doctor_referrals,
        "general_guidelines": guidelines,
        "ayurvedic_context": "",
        "follow_up": "If symptoms persist beyond 7 days, consult an Ayurvedic practitioner",
        "disclaimer": "These are traditional home remedies for general wellness only. They are not a substitute for medical treatment. Consult a qualified healthcare provider for persistent, severe, or worsening symptoms.",
        "enriched": False
    }


# ── Medicines plan engine ────────────────────────────────────────────────────

# Extended condition alias map — normalises user profile strings to KB condition ids
_CONDITION_ALIAS.update({
    "type1_diabetes":           "diabetes",
    "madhumeha":                "diabetes",
    "prameha":                  "diabetes",
    "high_bp":                  "hypertension",
    "high_blood_pressure":      "hypertension",
    "blood_pressure":           "hypertension",
    "rakta_gata_vata":          "hypertension",
    "polycystic_ovarian":       "pcos",
    "polycystic_ovary_syndrome":"pcos",
    "artava_dushti":            "menstrual_disorders",
    "dysmenorrhea":             "menstrual_disorders",
    "amenorrhea":               "menstrual_disorders",
    "leukorrhea":               "leucorrhoea",
    "leucorrhea":               "leucorrhoea",
    "hyperthyroidism":          "hyperthyroid",
    "thyroidism":               "thyroid",
    "overweight":               "obesity",
    "sthoulya":                 "obesity",
    "high_cholesterol":         "dyslipidemia",
    "dyslipidaemia":            "dyslipidemia",
    "liver_disease":            "fatty_liver",
    "nafld":                    "fatty_liver",
    "yakrit_vikara":            "liver_disorders",
    "jaundice":                 "liver_disorders",
    "kamala":                   "liver_disorders",
    "ckd":                      "kidney_disease",
    "chronic_kidney_disease":   "kidney_disease",
    "kidney_failure":           "kidney_disease",
    "iron_deficiency":          "anemia",
    "iron_deficiency_anemia":   "anemia",
    "pandu":                    "anemia",
    "pandu_roga":               "anemia",
    "ibd":                      "inflammatory_bowel_disease",
    "crohns":                   "inflammatory_bowel_disease",
    "ulcerative_colitis":       "inflammatory_bowel_disease",
    "piles":                    "hemorrhoids",
    "arsha":                    "hemorrhoids",
    "haemorrhoids":             "hemorrhoids",
    "rheumatoid":               "rheumatoid_arthritis",
    "amavata":                  "rheumatoid_arthritis",
    "acid_reflux":              "hyperacidity",
    "gerd":                     "hyperacidity",
    "heartburn":                "hyperacidity",
    "amlapitta":                "hyperacidity",
    "skin_disease":             "skin_disorders",
    "eczema":                   "skin_disorders",
    "psoriasis":                "skin_disorders",
    "kushtha":                  "skin_disorders",
    "dermatitis":               "skin_disorders",
    "urticaria":                "allergic_skin",
    "hives":                    "allergic_skin",
    "hay_fever":                "allergic_rhinitis",
    "allergic_rhinitis":        "allergic_rhinitis",
    "pratishyaya":              "allergic_rhinitis",
    "heart_disease":            "cardiac_weakness",
    "coronary_artery_disease":  "cardiac_weakness",
    "angina":                   "cardiac_weakness",
    "hridaya_roga":             "cardiac_weakness",
    "gout":                     "vatarakta",
    "uric_acid":                "vatarakta",
    "erectile_dysfunction":     "male_reproductive",
    "infertility_male":         "male_reproductive",
    "oligospermia":             "male_reproductive",
    "vajikarana":               "male_reproductive",
    "hair_fall":                "hair_loss",
    "alopecia":                 "hair_loss",
    "keshya":                   "hair_loss",
    "eye_strain":               "eye_disorders",
    "vision_problems":          "eye_disorders",
    "chakshu_roga":             "eye_disorders",
    "worms":                    "intestinal_worms",
    "krimi":                    "intestinal_worms",
    "malabsorption":            "grahani",
    "sprue":                    "grahani",
    "bleeding_gums":            "bleeding_disorders",
    "nose_bleed":               "bleeding_disorders",
    "wound_healing":            "wounds",
    "memory_loss":              "cognitive_decline",
    "cognitive_impairment":     "cognitive_decline",
    "alzheimers":               "cognitive_decline",
    "dementia":                 "cognitive_decline",
    "medhya":                   "cognitive_decline",
    "panic_attacks":            "anxiety",
    "ocd":                      "anxiety",
    "ptsd":                     "anxiety",
    "adhd":                     "memory_impairment",
    "hypothyroid":              "hypothyroid",
    "postpartum":               "postpartum_weakness",
    "postpartum_depression":    "postpartum_weakness",
    "lymph_node_enlargement":   "lymph_enlargement",
    "lipoma":                   "lymph_enlargement",
    "bronchitis":               "respiratory_infections",
    "pneumonia":                "respiratory_infections",
    "sinusitis":                "allergic_rhinitis",
    "fever":                    "fever",
    "jwara":                    "fever",
    "burning_urination":        "uti",
    "urinary_tract_infection":  "uti",
    "kidney_stones":            "kidney_stones",
    "renal_calculi":            "kidney_stones",
    "ashmari":                  "kidney_stones",
    "bph":                      "prostate_issues",
    "paralysis":                "neurological_disorders",
    "hemiplegia":               "neurological_disorders",
    "sciatica":                 "sciatica",
    "cervical_pain":            "cervical_spondylosis",
    "spondylitis":              "cervical_spondylosis",
    "insomnia":                 "insomnia",
    "anidra":                   "insomnia",
    "stress":                   "stress",
    "burnout":                  "stress",
    "low_immunity":             "low_immunity",
    "frequent_infections":      "low_immunity",
})

# Extended drug-herb interaction map
_DRUG_HERB_MAP.update({
    "rauwolfia":       ["antihypertensives", "sedatives", "cardiac_glycosides", "antidepressants"],
    "sarpagandha":     ["antihypertensives", "sedatives", "cardiac_glycosides", "antidepressants"],
    "arjuna":          ["antihypertensives", "cardiac_glycosides", "anticoagulants"],
    "manjistha":       ["blood_thinners", "anticoagulants"],
    "haridra":         ["blood_thinners", "diabetes_medication", "nsaids"],
    "neem":            ["diabetes_medication", "immunosuppressants"],
    "fenugreek":       ["diabetes_medication", "blood_thinners", "anticoagulants"],
    "aloe":            ["diabetes_medication", "blood_thinners"],
    "shilajit":        ["diabetes_medication", "antihypertensives"],
    "pippali":         ["nsaids", "antibiotics"],
    "tulsi":           ["blood_thinners", "anticoagulants"],
    "vacha":           ["sedatives", "antiepileptics"],
    "jatamansi":       ["sedatives", "antidepressants", "antiepileptics"],
    "shankhapushpi":   ["sedatives", "antiepileptics", "antidepressants"],
    "punarnava":       ["diuretics", "antihypertensives"],
    "gokshura":        ["diuretics", "antihypertensives"],
})

# Agni-Virya compatibility: what virya preference to boost for each Agni type
# manda (slow) → prefer ushna virya to kindle; tikshna (sharp) → prefer sheeta to cool
# vishama (irregular) → prefer ushna to ground; sama → no preference
_AGNI_VIRYA_BOOST: dict[str, str] = {
    "manda":   "ushna",   # slow Agni needs warming medicines
    "tikshna": "sheeta",  # sharp Agni needs cooling medicines
    "vishama": "ushna",   # irregular Agni needs grounding warmth
    "sama":    None,      # balanced — no preference
}

# Ama-clearing karma terms — medicines with these Karma get Ama bonus
_AMA_KARMA = {"Deepana", "Pachana", "Ama Pachana", "Dipana", "Lekhana"}


def _score_medicine(
    med: dict,
    vikriti_dominant: str,
    vikriti_secondary: str,
    conditions: list[str],
    agni_type: str = "sama",
    ama_level: str = "low",
    current_season: str = "",
) -> int:
    """7-signal scoring. Higher score = better personalised match."""
    score = 0
    de = med.get("dosha_effects", {})
    karma_set = set(med.get("karma", []))

    # 1. Condition match — primary driver (+5 per match)
    med_conditions = [c.lower() for c in med.get("conditions", [])]
    matched_conditions = [c for c in conditions if c in med_conditions]
    score += len(matched_conditions) * 5

    # 2. Multi-condition synergy bonus (+3 if covers ≥2 of user's conditions)
    if len(matched_conditions) >= 2:
        score += 3

    # 3. Dominant Vikriti match (+3 — use vikriti, not prakriti)
    if de.get(vikriti_dominant, 0) < 0:
        score += 3

    # 4. Secondary Vikriti match (+1)
    if de.get(vikriti_secondary, 0) < 0:
        score += 1

    # 5. Agni-Virya compatibility (+2)
    preferred_virya = _AGNI_VIRYA_BOOST.get(agni_type)
    if preferred_virya and med.get("virya", "").lower() == preferred_virya:
        score += 2

    # 6. Ama Pachana bonus (+3 if user has high Ama and medicine clears it)
    if ama_level in ("high", "moderate") and karma_set.intersection(_AMA_KARMA):
        score += 3 if ama_level == "high" else 1

    # 7. Season penalty (−5 if medicine should be avoided in current season)
    if current_season and current_season.lower() in [s.lower() for s in med.get("season_avoid", [])]:
        score -= 5

    return score


def _check_medicine_safety(
    med: dict,
    is_pregnant: bool,
    current_meds: list[str],
    allergies: list[str],
    medical_history: list[str],
) -> tuple[bool, str | None]:
    """4-layer safety gate. Returns (is_safe, reason_if_blocked)."""
    if is_pregnant and not med.get("pregnancy_safe", False):
        return False, "Not safe during pregnancy"

    # Contraindications vs medical history — precise word/phrase matching
    # (naive substring matched 'heart' inside 'heartburn'; word-boundary does not).
    med_contraindications = med.get("contraindications", [])
    for hist in medical_history:
        for contra in med_contraindications:
            # bidirectional: contra may be broader OR narrower than the user's term
            if term_in_condition(hist, contra) or term_in_condition(contra, hist):
                return False, f"Contraindicated: {hist}"

    # Drug interactions — structured field + global herb map
    all_ingredients_text = " ".join(med.get("ingredients", [])).lower()
    med_drug_interactions = [d.lower() for d in med.get("drug_interactions", [])]
    for current_med in current_meds:
        cm = current_med.lower().replace(" ", "_")
        for interaction in med_drug_interactions:
            if interaction in cm or cm in interaction:
                return False, f"Interacts with {current_med}"
        for herb_key, blocked_cats in _DRUG_HERB_MAP.items():
            if herb_key in all_ingredients_text:
                for cat in blocked_cats:
                    if cat in cm or cm in cat:
                        return False, f"{herb_key.title()} interacts with {current_med}"

    # Allergy check
    for allergy in allergies:
        if allergy.lower() in all_ingredients_text:
            return False, f"Contains allergen: {allergy}"

    return True, None


def _select_anupana(med: dict, primary_condition: str, agni_type: str) -> str:
    """Return condition-optimised Anupana, falling back to Agni-adjusted default."""
    overrides = med.get("anupana_by_condition", {})
    if primary_condition and primary_condition in overrides:
        return overrides[primary_condition]
    # Agni fallback: manda → always warm; tikshna → prefer cool/water
    default = med.get("anupana", "warm water")
    if agni_type == "manda" and "warm" not in default.lower():
        return f"warm {default}"
    return default


def _build_treatment_protocol(
    formulations: list[dict],
    agni_type: str,
    conditions: list[str],
) -> dict:
    """Build a multi-week treatment protocol based on Agni and formulation durations."""
    if not formulations:
        return {}

    min_weeks = min((m.get("duration_min_weeks", 4) for m in formulations), default=4)
    max_weeks = max((m.get("duration_max_weeks", 8) for m in formulations), default=8)

    # Agni-adjusted initial dosing
    if agni_type == "manda":
        dose_note = "Start at half the standard dose for the first 2 weeks to avoid Ama aggravation as Agni is sluggish."
        week_1_2_suffix = " — start at HALF dose due to Manda Agni"
    elif agni_type == "tikshna":
        dose_note = "May begin at standard dose immediately; Tikshna Agni can handle full potency from day one."
        week_1_2_suffix = " — standard dose (Tikshna Agni tolerates full dose)"
    elif agni_type == "vishama":
        dose_note = "Take medicines at the same time each day to regularise Vishama Agni. Start at half dose and increase after Week 2."
        week_1_2_suffix = " — half dose; strict fixed timing essential for Vishama Agni"
    else:
        dose_note = "Standard dosage as prescribed; Sama Agni supports full therapeutic response."
        week_1_2_suffix = " — standard dose"

    condition_context = ", ".join(conditions[:3]) if conditions else "general wellness"

    return {
        "week_1_2": f"Introduce all formulations at prescribed dosage{week_1_2_suffix}. Focus on Ama clearance and Agni kindling. Monitor for any digestive sensitivity.",
        "week_3_4": "Progress to full standard dose (if started lower). Therapeutic action on target Dhatus begins. Primary symptoms should show first signs of improvement.",
        "week_5_plus": (
            f"Maintenance phase — continue for {min_weeks}–{max_weeks} weeks total. "
            f"For {condition_context}: reassess with a Vaidya at Week {min_weeks}. "
            "If full symptomatic relief, taper to once-daily for 2 weeks before stopping."
        ),
        "dose_note": dose_note,
        "total_duration": f"{min_weeks}–{max_weeks} weeks (condition-dependent)",
    }


def _build_dosage_schedule(formulations: list[dict], anupana_map: dict[str, str] | None = None) -> list[dict]:
    """Build a structured time-of-day schedule using condition-optimised Anupana."""
    anupana_map = anupana_map or {}
    slots: dict[str, list[str]] = {
        "morning": [], "before_meals": [], "after_meals": [],
        "twice_daily": [], "before_sleep": [], "night_application": [],
        "morning_and_night": [], "multiple_times_daily": [],
    }
    for med in formulations:
        timing = med.get("timing", "twice_daily")
        name = med["name"]
        dosage = med.get("dosage", "")
        anupana = anupana_map.get(med["id"], med.get("anupana", "warm water"))
        entry = f"{name} — {dosage} (with {anupana})"
        slots.get(timing, slots["twice_daily"]).append(entry)

    schedule = []
    if slots["morning"] or slots["morning_and_night"]:
        schedule.append({
            "time": "Morning (empty stomach or with light breakfast)",
            "medicines": slots["morning"] + slots["morning_and_night"],
        })
    if slots["before_meals"]:
        schedule.append({"time": "Before meals (30 min prior)", "medicines": slots["before_meals"]})
    if slots["after_meals"]:
        schedule.append({"time": "After meals", "medicines": slots["after_meals"]})
    if slots["twice_daily"]:
        schedule.append({"time": "Twice daily (morning & evening)", "medicines": slots["twice_daily"]})
    if slots["multiple_times_daily"]:
        schedule.append({"time": "3–4 times daily (as directed)", "medicines": slots["multiple_times_daily"]})
    if slots["before_sleep"] or slots["night_application"]:
        schedule.append({
            "time": "Night / Before sleep",
            "medicines": slots["before_sleep"] + slots["night_application"],
        })
    return [s for s in schedule if s["medicines"]]


# Dosha-specific lifestyle guidance (used as base; enricher deepens it per protocol)
_LIFESTYLE_BY_DOSHA = {
    "vata": {
        "dietary_note": "Favour warm, unctuous, nourishing foods. Eat at fixed times. Use generous ghee.",
        "routine_note": "Follow strict Dinacharya. Abhyanga (oil massage) daily with sesame oil. Avoid multitasking.",
        "avoid": ["cold/raw foods", "late nights", "excessive travel", "stimulant caffeine", "fasting"],
    },
    "pitta": {
        "dietary_note": "Favour cooling, sweet, bitter, astringent foods. Coconut water and pomegranate daily.",
        "routine_note": "Avoid overheating and competitive stress. Moonlight walks. Shitali pranayama.",
        "avoid": ["alcohol", "excess sun exposure", "spicy/fried/fermented food", "suppressing emotions"],
    },
    "kapha": {
        "dietary_note": "Favour light, warm, pungent, and spiced meals. Honey over sugar. Skip breakfast if not hungry.",
        "routine_note": "Vigorous exercise daily. Avoid daytime sleeping. Dry Garshana (powder massage).",
        "avoid": ["cold dairy", "fried food", "excess sugar", "sedentary habits", "eating out of habit"],
    },
}


def generate_medicines_plan(
    user_profile: dict,
    medicines_prefs: dict,
    ayurvedic_remedies: list,
    plan_type: str = "clinical_medicine",
) -> dict:
    plan_id = f"medicines_{user_profile.get('id', 'usr')}_{int(datetime.now(timezone.utc).timestamp())}"

    # ── Profile extraction ──────────────────────────────────────────────────
    dominant_dosha  = (user_profile.get("dominant_dosha") or "vata").lower()
    secondary_dosha = (user_profile.get("secondary_dosha") or "pitta").lower()
    # Use Vikriti (imbalance state) for scoring if available, else fall back to Prakriti
    vikriti_dominant  = (user_profile.get("vikriti_dominant") or dominant_dosha).lower()
    vikriti_secondary = (user_profile.get("vikriti_secondary") or secondary_dosha).lower()
    agni_type   = (user_profile.get("agni_type") or "sama").lower()
    ama_level   = (user_profile.get("ama_indicator") or "low").lower()
    season      = (user_profile.get("current_season") or "").lower()
    is_pregnant = bool(user_profile.get("pregnancy_or_nursing", False))
    gender      = (user_profile.get("gender") or "").lower()
    age         = int(user_profile.get("age") or 30)

    # Structured medication multi-select from preferences (list of category strings)
    current_meds_prefs = medicines_prefs.get("current_allopathic_medications") or []
    # Also include free-text from user profile (legacy)
    current_meds_profile = user_profile.get("current_medications") or []
    current_meds = [m.lower().replace(" ", "_") for m in current_meds_prefs + current_meds_profile]

    allergies       = user_profile.get("allergies") or []
    medical_history = [c.lower() for c in (user_profile.get("medical_history") or [])]
    ingredient_access  = (medicines_prefs.get("ingredient_access") or "can_buy_herbs").lower()
    previous_tried     = [m.lower().strip() for m in (medicines_prefs.get("previous_ayurvedic_medicines") or [])]

    # Ama self-assessment from preferences can override profile value
    ama_override = medicines_prefs.get("ama_self_assessment")
    if ama_override:
        ama_level = ama_override.lower()

    # ── Condition normalisation ────────────────────────────────────────────
    normalised_conditions: list[str] = []
    seen: set[str] = set()
    for cond in medical_history:
        c = cond.replace(" ", "_")
        norm = _CONDITION_ALIAS.get(c, c)
        if norm not in seen:
            normalised_conditions.append(norm)
            seen.add(norm)

    primary_condition = normalised_conditions[0] if normalised_conditions else ""

    # ── Chikitsa approach (Shamana vs. Shodhana) ──────────────────────────
    # If Ama is high or multiple Kapha/Pitta conditions → Shodhana first
    # Otherwise → Shamana (pacification)
    chikitsa_approach = "Shodhana" if (
        ama_level == "high" or
        (vikriti_dominant == "kapha" and len(normalised_conditions) >= 2)
    ) else "Shamana"

    # ── Safety tier gate ──────────────────────────────────────────────────
    max_safety_tier = 1 if ingredient_access == "kitchen_only" else 2

    # Elderly (>70) or paediatric (<12) → additional caution for Tier 2 with metals
    restrict_bhasma = age > 70 or age < 12

    # Gender filter
    def gender_ok(med: dict) -> bool:
        gs = med.get("gender_specific")
        return gs is None or gs.lower() == gender

    # ── Score and filter ──────────────────────────────────────────────────
    scored:  list[tuple[int, dict]] = []
    blocked: list[dict] = []

    for med in _MEDICINES_KB:
        tier = med.get("safety_tier", 1)
        if tier > max_safety_tier:
            continue
        if restrict_bhasma and med.get("type", "").lower() in ("bhasma (ash)", "pishti (powder of gems/minerals)") and tier == 2:
            blocked.append({"name": med["name"], "reason": "Mineral preparations require extra caution for your age group — consult a Vaidya"})
            continue
        if not gender_ok(med):
            continue
        is_safe, reason = _check_medicine_safety(med, is_pregnant, current_meds, allergies, medical_history)
        if not is_safe:
            blocked.append({"name": med["name"], "reason": reason})
            continue

        score = _score_medicine(
            med,
            vikriti_dominant=vikriti_dominant,
            vikriti_secondary=vikriti_secondary,
            conditions=normalised_conditions,
            agni_type=agni_type,
            ama_level=ama_level,
            current_season=season,
        )
        if score > 0:
            scored.append((score, med))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ── Split into primary / supporting / external ─────────────────────────
    condition_matched = [(s, m) for s, m in scored if any(
        _med_covers_condition(m, c) for c in normalised_conditions
    )]
    general_wellness = [(s, m) for s, m in scored if (s, m) not in condition_matched]

    # ── Condition coverage tier (honesty for rare / unmapped diseases) ─────
    # Which of the user's conditions actually have a KB-matched formulation?
    matched_conditions = {
        c for _, m in condition_matched
        for c in normalised_conditions
        if _med_covers_condition(m, c)
    }
    uncovered_conditions = [c for c in normalised_conditions if c not in matched_conditions]
    if not normalised_conditions:
        condition_coverage = "wellness"      # no conditions — general dosha wellness
    elif not condition_matched:
        condition_coverage = "general"       # rare/unmapped — only dosha-based general meds
    elif uncovered_conditions:
        condition_coverage = "partial"       # some conditions matched, some not
    else:
        condition_coverage = "curated"       # all conditions have KB-matched formulations

    primary_formulations    = [m for _, m in condition_matched[:3]]
    supporting_formulations = [m for _, m in (condition_matched[3:5] + general_wellness[:2])]
    all_selected            = primary_formulations + supporting_formulations

    external_oils           = [m for m in all_selected if m.get("application_type") == "external"]
    primary_formulations    = [m for m in primary_formulations    if m.get("application_type") != "external"]
    supporting_formulations = [m for m in supporting_formulations if m.get("application_type") != "external"]

    # ── Condition-optimised Anupana per medicine ──────────────────────────
    anupana_map: dict[str, str] = {}
    for med in primary_formulations + supporting_formulations + external_oils:
        anupana_map[med["id"]] = _select_anupana(med, primary_condition, agni_type)
        med["selected_anupana"] = anupana_map[med["id"]]
        med["previously_tried"] = med["name"].lower() in previous_tried

    # ── Build schedules and protocol ──────────────────────────────────────
    dosage_schedule    = _build_dosage_schedule(primary_formulations + supporting_formulations, anupana_map)
    treatment_protocol = _build_treatment_protocol(primary_formulations + supporting_formulations, agni_type, normalised_conditions)

    lifestyle_guidance = _LIFESTYLE_BY_DOSHA.get(vikriti_dominant, _LIFESTYLE_BY_DOSHA["vata"])

    return {
        "plan_id":               plan_id,
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "user_dosha":            dominant_dosha,
        "secondary_dosha":       secondary_dosha,
        "vikriti_dominant":      vikriti_dominant,
        "vikriti_secondary":     vikriti_secondary,
        "agni_type":             agni_type,
        "ama_level":             ama_level,
        "current_season":        season,
        "chikitsa_approach":     chikitsa_approach,
        "active_conditions":     normalised_conditions,
        "condition_coverage":    condition_coverage,
        "uncovered_conditions":  uncovered_conditions,
        "vaidya_review_required": bool(uncovered_conditions),
        "coverage_note": (
            "No formulation in our classical knowledge base specifically matches "
            f"{', '.join(c.replace('_', ' ') for c in uncovered_conditions)}. "
            "The medicines below are dosha-balancing general support — a qualified Vaidya "
            "should prescribe condition-specific formulations for these."
            if uncovered_conditions else ""
        ),
        "primary_formulations":  primary_formulations,
        "supporting_formulations": supporting_formulations,
        "external_therapies":    external_oils,
        "dosage_schedule":       dosage_schedule,
        "treatment_protocol":    treatment_protocol,
        "lifestyle_guidance":    lifestyle_guidance,
        "blocked_medicines":     blocked,
        "enriched":              False,
        "disclaimer": (
            "These Ayurvedic formulations are recommended based on your personalised profile. "
            "This is wellness guidance, not a substitute for clinical diagnosis. "
            "Always consult a qualified Ayurvedic Vaidya or physician before starting any new "
            "herbal medicine, particularly if you are on prescription medications."
        ),
    }
