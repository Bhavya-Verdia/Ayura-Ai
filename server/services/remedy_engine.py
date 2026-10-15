from datetime import datetime, timezone
import json
import re
import os
from core.kb_cache import kb_cache
from engine.condition_vocab import condition_matches_term, normalize_condition
from engine.herb_overlap import already_taking, herbs_in
from engine.contraindication_tokens import (
    assumed_state_notes,
    build_derived_states,
    contraindication_hit,
    usage_notes,
)


# The onboarding vocabulary and the formulary's `conditions` vocabulary were
# written separately, and 30 of the 70 conditions onboarding offers matched no
# formulation at all — osteoarthritis among them, against a formulary holding
# Yogaraj Guggulu and twenty other `arthritis` entries. Those patients were given
# Triphala and a cough powder as "general support".
#
# One condition → the formulary terms whose formulations are INDICATED for it.
# One-to-many on purpose: the one-to-one alias table had to pick, and picked
# wrongly (`ibs` was sent to the IBD formulations; `migraine` lost Pathyadi).
#
# Deliberately absent, so they stay "uncovered" with the Vaidya note rather than
# being served a near match: diabetes_type1 (hypoglycaemic herbs beside insulin),
# hyperthyroidism (the formulary's `thyroid` entries treat the opposite state),
# atrial_fibrillation (Arjuna beside digoxin and anticoagulants), bipolar,
# multiple_sclerosis, lupus, scleroderma, celiac, gallstones, sleep_apnea,
# low_blood_pressure, varicose_veins, vertigo, tinnitus, rosacea.
# AUTHORED, NOT CLINICALLY REVIEWED — `vaidya_condition_formulary_map.csv`.
_CONDITION_KB_TERMS: dict[str, tuple[tuple[str, ...], str]] = {
    "osteoarthritis": (("arthritis", "joint_pain"),
                       "Sandhigata Vata — the formulary's arthritis and joint-pain entries are written for it."),
    "ankylosing_spondylitis": (("arthritis", "back_pain", "low_back_pain"),
                               "Treated as Vata in the spine and joints; the anti-inflammatory Guggulu entries are indicated."),
    "lumbar_spondylosis": (("low_back_pain", "back_pain"), "Kati-graha — the back-pain entries."),
    "cervical_spondylosis": (("cervical_spondylosis", "neurological"),
                             "Griva-graha; the cervical and Vata-nervine entries."),
    "fibromyalgia": (("muscle_stiffness", "vata_vyadhi"),
                     "Mamsagata Vata — the muscle-stiffness and Vata-vyadhi entries."),
    "osteoporosis": (("calcium_deficiency",), "Asthi Kshaya — the calcium entries (Pravala, Mukta, Shankha)."),
    "peripheral_neuropathy": (("neurological_weakness", "vata_vyadhi"),
                              "Vata in the peripheral nerves; the nervine Vata-vyadhi entries."),
    "copd": (("respiratory_disorders", "chronic_cough", "kapha_respiratory"),
             "Chronic Kapha-Vata Shwasa; the chronic respiratory entries, not the acute-infection ones."),
    "chronic_bronchitis": (("bronchitis", "chronic_cough", "respiratory_disorders"),
                           "Kasa — the bronchitis and chronic-cough entries."),
    "ibd_crohns": (("inflammatory_bowel_disease",), "The formulary's IBD entries."),
    "ulcerative_colitis": (("inflammatory_bowel_disease",), "The formulary's IBD entries."),
    "ibs": (("ibs", "irritable_bowel", "grahani"),
            "Grahani. Not the IBD entries, which the old alias sent IBS patients to."),
    "migraine": (("migraine", "headache"), "Ardhavabhedaka — the migraine entry first, then headache."),
    "metabolic_syndrome": (("obesity", "dyslipidemia"),
                           "Medoroga; obesity and lipid entries. Diabetic entries only if diabetes is recorded."),
    "hashimoto": (("hypothyroid",),
                  "Usually hypothyroid. The thyroid-stimulating entries are wrong in its early hyperthyroid phase — the Vaidya confirms the state."),
    "acne_severe": (("acne", "skin_disorders"), "Yauvana Pidika — acne, then the Rakta-shodhaka skin entries."),
    "vitiligo": (("skin_disorders",), "Shvitra; the general Kushtha entries. Bakuchi-specific formulation is not in the formulary."),
    "endometriosis": (("dysmenorrhea", "menstrual_disorders"), "Kashtartava — the painful-menstruation entries."),
    "uterine_fibroids": (("uterine_disorders",), "Garbhashaya Granthi — the uterine entries."),
    "ocd": (("anxiety",), "Manovaha Srotas; the anxiolytic Medhya entries."),
    "ptsd": (("ptsd", "anxiety"), "The formulary's own PTSD entries, then anxiety."),
    "adhd": (("adhd", "memory_impairment"), "The formulary's ADHD entries, then the Medhya Rasayanas."),
}


def _kb_terms(user_cond: str) -> tuple[str, ...]:
    c = user_cond.lower()
    return (c, *_CONDITION_KB_TERMS.get(c, ((), ""))[0])


def _med_covers_condition(med: dict, user_cond: str) -> bool:
    """True if a medicine's `conditions` cover the user's condition — matching by
    exact string, the authored onboarding → formulary map, or shared canonical
    vocabulary key (so 'diabetes_type2' matches a KB entry tagged 'diabetes')."""
    med_conds = [x.lower() for x in med.get("conditions", [])]
    terms = _kb_terms(user_cond)
    if any(t in med_conds for t in terms):
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
    "gerd": "gerd",
    "acid_reflux": "hyperacidity",
    "chronic_constipation": "constipation",
    "chronic_fatigue": "chronic_fatigue_syndrome",
    "ra": "rheumatoid_arthritis",
    "depression": "depression",
    "cervical": "cervical_spondylosis",
}

# Ingredient blocks for home remedies: (canonical conditions, blocked ingredients).
# Written as canonical condition names so `condition_matches_term` resolves the
# synonyms — "thyroid" alone used to be matched as a substring, which caught
# hyperthyroidism and hypothyroidism but nothing a user typed by hand.
_REMEDY_INGREDIENT_BLOCKS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("diabetes_type1", "diabetes_type2"), ("guggulu", "honey", "jaggery", "mishri", "sugar")),
    # Eucalyptus and menthol vapour and a sniffed powder are airway irritants that
    # can set off bronchospasm. An eleven-year-old asthmatic was told to steam with
    # eucalyptus and then sniff dry ginger powder.
    (("asthma", "copd", "chronic_bronchitis"), ("eucalyptus", "menthol", "sniff")),
    (("hypertension",), ("salt", "ajwain", "stimulant")),
    (("hypothyroidism", "hyperthyroidism", "hashimoto"), ("ashwagandha",)),
    (("ibs", "ulcerative_colitis", "ibd_crohns"), ("pippali", "trikatu")),
)

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

def _alt_blocked_by_condition(text: str, medical_history) -> bool:
    low = (text or "").lower()
    for group, items in _REMEDY_INGREDIENT_BLOCKS:
        if any(condition_matches_term(c, g) for c in medical_history or [] for g in group) \
                and any(i in low for i in items if i != "ashwagandha"):
            return True
    return False


def _escalation(remedy_kb: dict | None) -> str:
    """The KB's authored "consult a doctor if…" line for a symptom.

    Tolerates a missing entry because the severity gate runs for symptoms the KB does
    not hold, where there is no line to give and a referral is issued anyway.
    """
    return ((remedy_kb or {}).get("consult_doctor_if") or "").strip()



# ── Shared with Panchakarma: what a typed medicine is, and what an allergy is in ──
# Both live in `panchakarma_clinical.json` so the three features recognise the same
# medicine names and the same allergen compositions. The medicines plan matched
# typed names by substring against its category tokens, so "warfarin" typed into
# the profile still received Triphala, which the form's "Blood thinners" option
# blocks; "Glycomet 500" (metformin) was checked against nothing.

def _resolve_medications(medications) -> tuple[list[str], dict | None]:
    """Interaction tokens for typed medicine names, and what was not recognised."""
    from services.panchakarma_engine import _medication_findings, pk_clinical
    found = _medication_findings(medications)
    classes = pk_clinical.get("medication_classes") or {}
    tokens: list[str] = []
    for cls in found["tokens"]:
        for t in (classes.get(cls) or {}).get("remedy_tokens") or []:
            if t not in tokens:
                tokens.append(t)
    review = None
    if found["matched"] or found["unmatched"]:
        review = {
            "matched": found["matched"],
            "unmatched": found["unmatched"],
            "notice": (
                "Not recognised, so nothing in this plan has been checked against "
                f"{'it' if len(found['unmatched']) == 1 else 'them'}: {', '.join(found['unmatched'])}. "
                "Show every medicine you take to the Vaidya and your doctor."
            ) if found["unmatched"] else None,
        }
    return tokens, review


def _allergen_entries(allergies) -> list[dict]:
    """The composition entries for a patient's declared allergies.

    The check was `allergy in ingredients_text`, so "dairy" was looked for in a list
    of herbs and ghee and never found, and the Anupana — milk, ghee, honey, the
    vehicle the patient swallows the medicine in — was never checked at all."""
    from services.panchakarma_engine import pk_clinical
    if isinstance(allergies, str):
        allergies = [allergies]
    table = pk_clinical.get("allergens") or {}
    out = []
    for a in allergies or []:
        key = str(a).strip().lower().replace(" ", "_")
        if key in table and isinstance(table[key], dict):
            out.append({"key": key, **table[key]})
        elif key:
            # An allergy outside the table is still checked by its own word.
            out.append({"key": key, "label": str(a), "terms": [key.replace("_", " ")]})
    return out


def _contains_allergen(text: str, entry: dict) -> bool:
    low = (text or "").lower()
    excepts = [e.lower() for e in entry.get("except", [])]
    for term in entry["terms"]:
        for m in re.finditer(rf"\b{re.escape(term)}\b", low):
            if not any(e in low[max(0, m.start() - 24):m.start()] for e in excepts):
                return True
    return False


# A condition rules out an Anupana as surely as an allergy: rock-salt water for
# kidney disease and hypertension, honey or mishri for a diabetic.
_ANUPANA_CONDITION_TERMS: tuple[tuple[tuple[str, ...], dict], ...] = (
    (("hypertension", "chronic_kidney_disease"), {"label": "salt (blood pressure / kidneys)",
                                                  "terms": ["salt", "saindhava", "lavana"]}),
    (("diabetes_type1", "diabetes_type2"), {"label": "sugar (diabetes)",
                                            "terms": ["honey", "madhu", "mishri", "sugar", "jaggery", "guda"]}),
)


def _allergen_safe_anupana(anupana: str, entries: list[dict],
                           medical_history=None) -> tuple[str, str | None]:
    """Keep the Anupana options that carry no allergen and no ruled-out item; say so
    when one was dropped."""
    entries = list(entries or []) + [
        rule for group, rule in _ANUPANA_CONDITION_TERMS
        if any(condition_matches_term(c, g) for c in medical_history or [] for g in group)]
    if not entries or not anupana:
        return anupana, None
    hit = [e for e in entries if _contains_allergen(anupana, e)]
    if not hit:
        return anupana, None
    options = [o.strip() for o in re.split(r",|\bor\b|/", anupana) if o.strip()]
    safe = [o for o in options if not any(_contains_allergen(o, e) for e in entries)]
    labels = ", ".join(e["label"].lower() for e in hit)
    if safe:
        new = " or ".join(safe)
        return new, f"Take it with {new}: the usual Anupana, '{anupana}', contains {labels}."
    return "warm water", (f"Take it with warm water: the usual Anupana, '{anupana}', contains {labels}. "
                          "Ask the Vaidya whether the medicine needs a different vehicle.")


def filter_remedies(user_profile: dict, symptom_input: dict) -> list:
    filtered_results = []

    # Use `or <default>` (not the .get default) so a present-but-null field —
    # e.g. current_medications: None on a user who never set meds — coerces to an
    # empty collection instead of None, which would blow up the `for … in` loops
    # below with "'NoneType' object is not iterable".
    symptoms = symptom_input.get("symptoms") or []
    severity = symptom_input.get("severity") or {}
    duration = symptom_input.get("duration") or {}
    taste_prefs = symptom_input.get("preference_taste_smell") or []

    pregnancy_or_nursing = user_profile.get("pregnancy_or_nursing", False)
    current_meds = user_profile.get("current_medications") or []
    # Typed names resolve to the interaction vocabulary the KB uses.
    current_meds = list(current_meds) + _resolve_medications(current_meds)[0]
    medical_history = user_profile.get("medical_history") or []
    allergies = user_profile.get("allergies") or []
    allergen_entries = _allergen_entries(allergies)
    remedy_classes = _patient_classes(user_profile.get("current_medications") or [],
                                      symptom_input.get("current_allopathic_medications") or [])
    dominant_dosha = user_profile.get("dominant_dosha", "vata").lower()
    # Only a recorded second Dosha. It defaulted to "pitta", so a Kapha patient
    # whose Kapha remedy was unsafe was handed the Pitta one — Shatavari in coconut
    # water, Kapha-building, for an obese diabetic — before the universal remedy
    # was ever tried.
    secondary_dosha = (user_profile.get("secondary_dosha") or "").lower() or None

    all_remedies = kb_cache.ayurvedic_remedies or _REMEDIES_FALLBACK

    for sym_id in symptoms:
        sym_sev = severity.get(sym_id, "mild")
        sym_dur = duration.get(sym_id, "recent")

        # Find remedy in KB (resolve onboarding labels to KB ids; fall back to raw).
        #
        # Resolved BEFORE the severity gate so a referral can carry the KB's own
        # escalation line. The gate still fires for a symptom that is not in the KB —
        # a severe complaint we hold no remedy for is exactly when a referral matters
        # — so the `not remedy_kb` bail stays below it, not above.
        _sid = _SYMPTOM_ALIASES.get(str(sym_id).lower(), str(sym_id).lower())
        remedy_kb = next((r for r in all_remedies if r.get("symptom_id") == _sid), None)

        # a) Severity gate
        if sym_sev == "severe":
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "see_doctor",
                "message": "This symptom requires immediate medical attention. Please consult a doctor.",
                # The specific thing to watch for, which the generic sentence above
                # cannot say: "vision loss, numbness, or vomiting" for a migraine,
                # "stools contain blood" for diarrhoea. Every one of the 60 entries
                # carries one and it reached the user through no channel at all.
                "consult_doctor_if": _escalation(remedy_kb),
            })
            continue

        if not remedy_kb:
            continue

        # b) Duration gate, calibrated by severity.
        #
        # This was `sym_dur in ["chronic", "months"]` — duration alone — which left
        # `moderate` as the one severity value that decided nothing: a moderate
        # symptom and a mild one produced byte-identical output at every duration.
        # `severe` is already a referral above, so the practitioner threshold is the
        # only lever severity has left. It is also the only one available: the KB
        # holds exactly one remedy per (symptom, dosha) plus a universal, so there is
        # no stronger preparation to escalate a moderate case TO.
        #
        # The rule is that severity buys down the duration you are allowed to wait:
        # mild still waits for months, moderate stops at weeks. Only one combination
        # changes — moderate + weeks — and it changes towards review, not away.
        requires_practitioner = (
            _DURATION_RANK.get(sym_dur, 0) >= _PRACTITIONER_DURATION_FLOOR.get(sym_sev, 2))
        practitioner_reason = _practitioner_reason(sym_sev, sym_dur) if requires_practitioner else ""

        # c) Pregnancy filter
        # 54 of 60 entries author a `pregnancy_alternative` — "Ginger tea with
        # mishri only — avoid hing" for nausea — and it was read only by the vector
        # seeder, so every pregnant patient was told no safe remedy existed. It is
        # served now, screened like any remedy, and with the practitioner named.
        alt = (remedy_kb.get("pregnancy_alternative") or "").strip()
        if pregnancy_or_nursing and not remedy_kb.get("pregnancy_safe", False) and alt \
                and not any(_contains_allergen(alt, e) for e in allergen_entries) \
                and not _alt_blocked_by_condition(alt, medical_history):
            filtered_results.append({
                "symptom_id": sym_id,
                "symptom_display": remedy_kb.get("symptom_display", sym_id),
                "severity": sym_sev,
                "duration": sym_dur,
                "remedy": {"name": f"Pregnancy-safe option for {remedy_kb.get('symptom_display', sym_id)}",
                           "preparation": alt, "ingredients": []},
                "pregnancy_alternative": True,
                "usage_cautions": ["The usual remedy for this is not safe in pregnancy; this is the "
                                   "gentler option. Tell your obstetrician and Vaidya you are using it."],
                "requires_practitioner": requires_practitioner,
                "practitioner_reason": practitioner_reason,
                "dosha_used": "pregnancy",
                "consult_doctor_if": _escalation(remedy_kb),
                "source": remedy_kb.get("source", "Traditional"),
            })
            continue
        if pregnancy_or_nursing and not remedy_kb.get("pregnancy_safe", False):
            filtered_results.append({
                "symptom_id": sym_id,
                "action": "consult_doctor",
                "message": "Safe remedy not available during pregnancy. Please consult your Ayurvedic practitioner.",
                "consult_doctor_if": _escalation(remedy_kb),
            })
            continue

        # d) Symptom-level contraindications.
        #
        # Every one of the 60 remedy entries carries a `contraindications` list and
        # 41 of them are non-empty — and nothing in this engine had ever read the
        # field. The hyperacidity remedy is barred during an active ulcer, the
        # oedema remedy when the swelling is cardiac or renal, the diarrhoea
        # remedy in dysentery. All of it was inert.
        #
        # The symptom being treated is removed from the derived state first: the
        # fever remedy lists `high_fever_above_103`, which reads the reported fever,
        # and would otherwise withhold the fever remedy from everyone with a fever.
        # Temperature is a number this app never sees, so that one is shown to the
        # user as a red flag instead of being guessed at.
        remedy_states = build_derived_states(
            user_profile, symptoms=[s for s in symptoms if s != sym_id])
        remedy_contra = remedy_kb.get("contraindications") or []
        blocked_by = next(
            (hit for tok in remedy_contra
             if (hit := contraindication_hit(tok, medical_history, remedy_states))),
            None,
        )
        if blocked_by:
            filtered_results.append({
                "symptom_id": sym_id,
                "symptom_display": remedy_kb.get("symptom_display", sym_id),
                "action": "consult_doctor",
                "message": (
                    f"Home treatment is not appropriate here: {blocked_by.replace('_', ' ')}. "
                    "Please see a practitioner."
                ),
                "consult_doctor_if": _escalation(remedy_kb),
            })
            continue

        remedy_cautions, remedy_red_flags = usage_notes(remedy_contra)

        candidate_notes: list[str] = []

        # dosha selection helper
        def is_safe(cand_remedy):
            # Notes belong to the candidate being judged; the last one judged is
            # the one served.
            candidate_notes.clear()
            if not cand_remedy:
                return False, None

            # Extract text to search for ingredients
            ingredients_list = cand_remedy.get("ingredients") or []
            ingredients_text = " ".join([i.get("item", "").lower() for i in ingredients_list])

            # e) Ingredient-level contraindication.
            #
            # The keys used to be matched with `key in condition`, which is the
            # substring test this codebase has removed everywhere else. It caught
            # "diabetes" inside "diabetes_type2" by luck and missed "hypertension"
            # in "high_blood_pressure" entirely — the form the app actually stores
            # when someone ticks high blood pressure. Each group now names the
            # canonical conditions it covers.
            for group, blocked_items in _REMEDY_INGREDIENT_BLOCKS:
                cond = next(
                    (c for c in medical_history
                     if any(condition_matches_term(c, g) for g in group)),
                    None,
                )
                if not cond:
                    continue
                # The method too: "strain and drink warm with honey" is in the
                # preparation, not the ingredient list, and a diabetic was given it.
                prep_text = ingredients_text + " " + str(cand_remedy.get("preparation") or "").lower()
                for item in blocked_items:
                    if item not in prep_text:
                        continue
                    if item == "ashwagandha":
                        # Recorded here, never on `cand_remedy`: that dict is the
                        # shared KB entry, and writing onto it served this thyroid
                        # caution to every later user given the same remedy.
                        candidate_notes.append("Use Ashwagandha with caution due to thyroid history.")
                    else:
                        return False, f"Contraindicated for {cond}"

            # d) Drug interaction
            # The medicines plan's map plus the kitchen herbs only remedies use. Two
            # copies had drifted: Ashwagandha was barred beside clonazepam in the
            # medicines plan and served as "Ashwagandha milk" by this one.
            drug_interaction_map = {k: list(v) for k, v in _DRUG_HERB_MAP.items()}
            for herb, cats in {
                "ashwagandha": ["thyroid_medication", "immunosuppressants"],
                "neem": ["diabetes_medication", "immunosuppressants"],
                "fenugreek": ["diabetes_medication", "blood_thinners"],
                "aloe_vera": ["diabetes_medication", "blood_thinners"],
                "tulsi": ["blood_thinners"],
                "nutmeg": ["sedatives"],
                "jatamansi": ["sedatives"],
            }.items():
                drug_interaction_map[herb] = sorted(set(drug_interaction_map.get(herb, [])) | set(cats))

            for med in current_meds:
                med_l = med.lower().replace(" ", "_")
                for herb, interactions in drug_interaction_map.items():
                    if herb in ingredients_text:
                        for interaction in interactions:
                            if interaction in med_l:
                                return False, {"interaction_found": True, "medication": med, "herb": herb}

            # e2) The authored herb x medicine table the medicines plan reads.
            bar, notes = _interaction_findings(herbs_in(ingredients_text), remedy_classes)
            if bar:
                return False, bar
            candidate_notes.extend(notes)

            # f) Allergy filter — by composition, over the ingredients and the method.
            method = " ".join([ingredients_text, str(cand_remedy.get("preparation") or ""),
                               str(cand_remedy.get("name") or "")])
            for entry in allergen_entries:
                if _contains_allergen(method, entry):
                    return False, f"Contains {entry['label'].lower()} (declared allergy)"

            return True, None

        selected_remedy = None
        dosha_used = dominant_dosha
        candidate = remedy_kb.get("remedies", {}).get(dominant_dosha)

        interaction_warning = None

        safe, reason = is_safe(candidate)
        why_not = reason if isinstance(reason, str) else None
        if not safe:
            if isinstance(reason, dict) and reason.get("interaction_found"):
                interaction_warning = reason
            dosha_used = secondary_dosha
            candidate = remedy_kb.get("remedies", {}).get(secondary_dosha) if secondary_dosha else None
            safe, reason = is_safe(candidate)
            why_not = (reason if isinstance(reason, str) else None) or why_not
            if not safe:
                if isinstance(reason, dict) and reason.get("interaction_found"):
                    interaction_warning = reason
                candidate = remedy_kb.get("universal_remedy")
                dosha_used = "universal"
                safe, reason = is_safe(candidate)
                why_not = (reason if isinstance(reason, str) else None) or why_not
                if not safe:
                    msg = {"symptom_id": sym_id, "action": "consult_doctor",
                           "message": "No safe remedy available due to interactions/allergies."}
                    if not why_not and interaction_warning:
                        why_not = (f"{interaction_warning['herb']} interacts with "
                                   f"{interaction_warning['medication']}")
                    if why_not:
                        # Say which: "interactions/allergies" told a diabetic nothing
                        # about why their headache was referred.
                        msg["message"] = (f"No home remedy for this suits you ({why_not}). "
                                          "Please see a practitioner.")
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
            # A copy: the KB entry is shared by every request in the process.
            "remedy": dict(selected_remedy),
            "caution_notes": list(dict.fromkeys(candidate_notes)),
            # The entry's own `drug_interactions` (33 of 60 carry one) was read by
            # nothing. Stated, not used to withhold: it is authored per complaint,
            # not per remedy, so it names a herb this patient may not be given.
            "medication_cautions": [
                t.replace("_", " ") for t in (remedy_kb.get("drug_interactions") or [])
                if any(t.lower() == m.lower() or t.lower() in m.lower().replace(" ", "_")
                       for m in current_meds)
            ],
            "requires_practitioner": requires_practitioner,
            # Which trigger fired. The note in the view said "Chronic/long-duration
            # symptom" whatever the cause, which is wrong copy for a moderate
            # complaint that has run a fortnight.
            "practitioner_reason": practitioner_reason,
            "taste_notices": _taste_notices(selected_remedy, taste_prefs),
            "drug_interaction_warning": interaction_warning,
            "source": remedy_kb.get("source", "Traditional"),
            "dosha_used": dosha_used,
            # The half of the KB's contraindication list that names a state the
            # app cannot observe — "vomiting blood needs emergency care", "do not
            # apply to broken skin". Being read is the only way these ever work.
            "usage_cautions": remedy_cautions,
            "red_flags": remedy_red_flags,
            # Authored on all 60 entries and, until now, read by exactly one thing —
            # `build_vectors.py`. The escalation guidance was embedded for the model
            # and shown to nobody. For 38 of the served remedies no other field
            # carried it either: their `red_flags` are empty.
            "consult_doctor_if": _escalation(remedy_kb),
            # `severity_gate` in the KB. It is NOT a ceiling on treatment — it labels
            # how serious the complaint itself is, which is why `ojas_building` and
            # `seasonal_detox` carry "mild" (they have no severity at all) and why the
            # graver complaints correlate with `use_with_caution` remedies rather than
            # against them. Gating on it would withhold the headache remedy at moderate
            # while still serving the migraine remedy at moderate. Surfaced under an
            # honest name so the next reader is not invited to make that mistake.
            "symptom_seriousness": remedy_kb.get("severity_gate") or "",
        })

    return filtered_results

# Dietary guidance carries contraindications exactly as a remedy ingredient does,
# and this engine already gates the ingredients — `blocks` in the candidate loop
# withholds guggulu and honey from a diabetic, salt from a hypertensive. The
# GENERAL GUIDELINES were static prose per dosha and passed no gate at all, so
# the same diabetic was told to eat "sweet fruits" and someone with chronic
# kidney disease to drink "coconut water", which is a potassium load.
#
# `build_remedy_plan` was handed the whole user profile and read `dominant_dosha`
# out of it. Same fault as the gym warm-up: the structured data was filtered
# carefully and the prose beside it was not filtered at all.
#
# Matching is substring-based in both directions, the way `_matches_condition`
# and the ingredient blocks already work, so "type_2_diabetes" catches "diabetes".
_GUIDELINE_RESTRICTIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("coconut water",
     ("kidney", "renal", "ckd", "dialysis", "hyperkalemia", "hyperkalaemia"),
     "cool water with lime"),
    ("sweet fruits",
     ("diabetes", "diabetic", "prediabetes", "insulin_resistance", "pcos"),
     "low-sugar fruits (guava, pear, berries)"),
    ("oily foods",
     ("gallbladder", "gallstone", "pancreatitis", "cholesterol", "dyslipidemia",
      "dyslipidaemia", "fatty_liver"),
     "lightly oiled foods"),
    ("spiced foods",
     ("gerd", "acid_reflux", "hyperacidity", "gastritis", "ulcer", "ibs",
      "inflammatory_bowel", "crohn", "colitis"),
     "lightly seasoned foods"),
)

# Each guideline is one or two sentences: what to eat, then what to avoid. A term
# appearing AFTER "Avoid" is already being warned against, and substituting there
# inverts the advice — the first version of this produced "Avoid heavy, sweet,
# moist well-cooked foods with only a little ghee" for a Kapha with gallstones,
# which reads as a warning against the safer option.
_AVOID_CLAUSE = "avoid"


def _gate_guidelines(guidelines: dict, medical_history) -> tuple[dict, list]:
    """Swap a dietary item a declared condition rules out, and say that it was
    swapped. Silently changing clinical guidance is its own problem."""
    tokens = [str(c).lower() for c in (medical_history or []) if c]
    if not tokens:
        return guidelines, []

    out = dict(guidelines)
    swapped: list[tuple[str, str]] = []
    for term, contra, replacement in _GUIDELINE_RESTRICTIONS:
        if not any(k in tok or tok in k for k in contra for tok in tokens):
            continue
        for field in ("diet_during_recovery", "lifestyle_notes"):
            text = out.get(field) or ""
            low = text.lower()
            # Only the recommending half. Past "Avoid", the term is already the
            # thing being warned against.
            limit = low.index(_AVOID_CLAUSE) if _AVOID_CLAUSE in low else len(text)
            idx = low.find(term)
            if idx == -1 or idx >= limit:
                continue
            out[field] = text[:idx] + replacement + text[idx + len(term):]
            swapped.append((term, replacement))
    notices = [f"'{t}' replaced with '{r}' — your declared health history rules it out."
               for t, r in swapped]
    return out, notices


# `follow_up` was one fixed sentence — "If symptoms persist beyond 7 days, consult
# an Ayurvedic practitioner" — printed to everyone. Told to somebody whose symptom
# has run for three months it is advice eleven weeks out of date, and it reads as
# reassurance at the exact moment the plan should be escalating.
_FOLLOW_UP_BY_DURATION = {
    "recent": "If symptoms persist beyond 7 days, consult an Ayurvedic practitioner.",
    "weeks": ("These symptoms have already run for weeks, so the 7-day rule has passed. "
              "Book an Ayurvedic practitioner rather than waiting further, and use these "
              "remedies as support in the meantime."),
    "months": ("A symptom lasting months is not a self-care case. See an Ayurvedic "
               "practitioner and a doctor — persistent symptoms need a diagnosis before "
               "they need a remedy. Use these only alongside that."),
    "chronic": ("A chronic symptom needs a practitioner who can follow it over time. "
                "These remedies support the picture; they do not replace the assessment. "
                "Book one, and see a doctor for anything undiagnosed."),
}

_DURATION_RANK = {"recent": 0, "weeks": 1, "months": 2, "chronic": 3}

# How long a symptom may run before it wants a practitioner, by how bad it is.
# `severe` is absent because it never reaches this test — it is referred outright.
_PRACTITIONER_DURATION_FLOOR = {"mild": 2, "moderate": 1}


def _practitioner_reason(severity: str, duration: str) -> str:
    """Why the practitioner note is showing, in the words that fit the trigger."""
    if severity == "moderate" and _DURATION_RANK.get(duration, 0) == 1:
        return ("A moderate symptom that has already run for weeks is past the point "
                "where self-care should be carrying it on its own.")
    if _DURATION_RANK.get(duration, 0) >= 2:
        return ("A symptom running for months or longer needs a practitioner who can "
                "follow it over time.")
    return "This symptom warrants review by an Ayurvedic practitioner."


def _follow_up_advice(symptom_input: dict, referred: list) -> str:
    """Follow-up keyed to the longest-running symptom, and to any referral.

    The longest one governs because it is the one the 7-day rule has already failed;
    telling somebody with a three-month complaint and a three-day one to "wait a
    week" answers only the easier half.
    """
    durations = (symptom_input.get("duration") or {}).values()
    worst = max(durations, key=lambda d: _DURATION_RANK.get(d, 0), default="recent")
    advice = _FOLLOW_UP_BY_DURATION.get(worst, _FOLLOW_UP_BY_DURATION["recent"])
    if referred:
        advice = ("One or more of your symptoms needs medical attention now — see the "
                  "referrals above before starting anything here. ") + advice
    return advice


# ── Taste and smell preference ────────────────────────────────────────────────
# `preference_taste_smell` ("no_bitter", "no_strong_smell") was declared and read by
# nothing. The remedy KB carries no Rasa field, so this is an authored ingredient map
# rather than KB data — and it is deliberately small, covering only ingredients whose
# taste or smell is not in dispute.
#
# It FLAGS rather than filters. Each symptom usually has one remedy per Dosha, so
# excluding on taste would often leave nothing, and a preference must not cost
# somebody their treatment. Ayurveda has a better answer anyway: Anupana — the
# vehicle a medicine is taken with — is chosen partly to make it palatable, so the
# notice names the classical masking rather than just reporting the clash.
#
# AUTHORED, NOT CLINICALLY REVIEWED.
_BITTER_INGREDIENTS = {
    "neem", "guduchi", "triphala", "karela", "bitter gourd", "kalmegh", "kutki",
    "aloe vera", "punarnava", "manjistha", "chirata", "vasaka", "turmeric",
}
_STRONG_SMELL_INGREDIENTS = {
    "hing", "asafoetida", "mustard oil", "eucalyptus", "garlic", "camphor",
    "neem", "onion", "clove oil", "ajwain",
}

_TASTE_MASKING = {
    "no_bitter": ("Bitter (Tikta) is the active principle in these, so it cannot be removed "
                  "without removing the effect. Take it with the Anupana already listed — "
                  "honey, warm milk or mishri — which is what classically carries a bitter "
                  "medicine, and follow immediately with warm water."),
    "no_strong_smell": ("Take it in a well-ventilated room and follow with warm water or a "
                        "cardamom pod. For oils, warm slightly less — heat is what drives "
                        "the smell off."),
}


def _taste_notices(remedy: dict, preferences: list[str]) -> list[str]:
    """Where a chosen remedy clashes with a stated taste or smell preference."""
    if not preferences or not isinstance(remedy, dict):
        return []
    text = " ".join(
        str(i.get("item", "")).lower() for i in (remedy.get("ingredients") or [])
    )
    notices = []
    for preference, terms, label in (
        ("no_bitter", _BITTER_INGREDIENTS, "bitter"),
        ("no_strong_smell", _STRONG_SMELL_INGREDIENTS, "strongly scented"),
    ):
        if preference not in preferences:
            continue
        hits = sorted({t for t in terms if t in text})
        if hits:
            notices.append(
                f"You asked to avoid {label} remedies, and this one contains "
                f"{', '.join(hits)}. {_TASTE_MASKING[preference]}"
            )
    return notices


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

    guidelines, guideline_notices = _gate_guidelines(
        guidelines, user_profile.get("medical_history"))

    return {
        "plan_id": plan_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_dosha": dominant_dosha,
        "symptoms_addressed": symptoms_addressed,
        "doctor_referrals": doctor_referrals,
        "general_guidelines": guidelines,
        "guideline_notices": guideline_notices,
        "ayurvedic_context": "",
        "follow_up": _follow_up_advice(symptom_input, doctor_referrals),
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
    # The same matcher as coverage. Exact-string matching here scored a formulation
    # 0 for a condition `_med_covers_condition` said it covered.
    matched_conditions = [c for c in conditions if _med_covers_condition(med, c)]
    score += len(matched_conditions) * 5

    # 2. Multi-condition synergy bonus (+3 if covers ≥2 of user's conditions)
    if len(matched_conditions) >= 2:
        score += 3

    # 3. Dominant Vikriti match (+3 — use vikriti, not prakriti)
    if de.get(vikriti_dominant, 0) < 0:
        score += 3

    # 3b. Named for this Dosha (+2). `dosha_effects` is coarse — 311 of its 471
    # values are -1 — so the tridoshic Rasayanas tied with everything and won on
    # file order: every Vata, Pitta and Kapha patient with nothing to treat got the
    # same Triphala and Chyawanprash. The authored karma says which Dosha a
    # formulation is written against.
    if f"{vikriti_dominant}hara" in {k.lower() for k in karma_set}:
        score += 2

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

    # 7. Season penalty (−5 if medicine should be avoided in current season).
    # Normalised: three entries said "summer" while the app stores "grishma", so
    # they never fired.
    from services.panchakarma_engine import _current_ritu
    if current_season and current_season.lower() in {_current_ritu(x) for x in med.get("season_avoid", [])}:
        score -= 5

    # 8. Ritucharya by Virya (Ashtanga Hridaya Sutrasthana 3). Only 36 of 157
    # formulations carry a `season_avoid`, so the season decided almost nothing;
    # every formulation carries a Virya. Cooling medicines suit the Pitta seasons,
    # warming ones the cold — a nudge, below a condition match.
    virya = (med.get("virya") or "").lower()
    if current_season in ("grishma", "sharad"):
        score += 1 if virya == "sheeta" else -2 if virya == "ushna" else 0
    elif current_season in ("hemanta", "shishira", "varsha", "vasanta"):
        score += 1 if virya == "ushna" else -1 if virya == "sheeta" and current_season != "vasanta" else 0

    return score


def _check_medicine_safety(
    med: dict,
    is_pregnant: bool,
    current_meds: list[str],
    allergies: list[str],
    medical_history: list[str],
    derived_states: dict | None = None,
) -> tuple[bool, str | None]:
    """4-layer safety gate. Returns (is_safe, reason_if_blocked)."""
    if is_pregnant and not med.get("pregnancy_safe", False):
        return False, "Not safe during pregnancy"

    # Contraindications vs medical history and derived state.
    #
    # This used to be a raw `term_in_condition`, which compares STRINGS and never
    # consults the alias table — so a contraindication authored under one of two
    # names for a disease never fired against the other. Measured across both KBs:
    # 7 tokens were dead that way, including `hypotension` on Arjuna Churna (the
    # app records `low_blood_pressure`), `renal_disease` on Abhraka Bhasma (a mica
    # preparation, app records `chronic_kidney_disease`) and `hyperthyroid` on
    # Ashwagandha — the exact interaction the herb-level safety work was built for.
    # Same defect the Panchakarma gate had; `condition_matches_term` is the fix.
    #
    # `contraindication_hit` also reaches the ~50 uses that are derived states
    # rather than diagnoses (`pitta_excess`, `ama_condition`, `fever`, `children`).
    # Those can never appear in `medical_history` and so had never matched anything.
    med_contraindications = med.get("contraindications", [])
    for contra in med_contraindications:
        hit = contraindication_hit(contra, medical_history, derived_states)
        if hit:
            return False, f"Contraindicated: {hit}"

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

    # Allergy check — by composition. A Ghrita is ghee and a Taila is sesame oil
    # unless another base is named; "dairy" never appears in an ingredient list.
    for entry in _allergen_entries(allergies):
        if _contains_allergen(" ".join([all_ingredients_text, med.get("name", ""),
                                        med.get("type", "")]), entry):
            return False, f"Contains {entry['label'].lower()} (declared allergy)"

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
        # One at a time. "Introduce all formulations at once" made any reaction
        # impossible to attribute, and the narrative beside it said the opposite.
        "week_1_2": (
            f"Start one formulation at a time, adding the next after 2–3 days if the last is "
            f"well tolerated{week_1_2_suffix}. Focus on Ama clearance and Agni kindling. If "
            "anything disagrees with you, the last one added is the likely cause."
            if len(formulations) > 1 else
            f"Start at the prescribed dosage{week_1_2_suffix}. Focus on Ama clearance and Agni "
            "kindling. Monitor for any digestive sensitivity."),
        "week_3_4": "Progress to full standard dose (if started lower). Therapeutic action on target Dhatus begins. Primary symptoms should show first signs of improvement.",
        "week_5_plus": (
            f"Maintenance phase — continue for {min_weeks}–{max_weeks} weeks total. "
            f"For {condition_context}: reassess with a Vaidya at Week {min_weeks}. "
            "If full symptomatic relief, taper to once-daily for 2 weeks before stopping."
        ),
        "dose_note": dose_note,
        "total_duration": f"{min_weeks}–{max_weeks} weeks (condition-dependent)",
    }


# Onboarding accepts an age from 10, so children reach this engine. `engine/
# contraindication_tokens.py` already draws the line at 12 — `children` and
# `children_without_supervision` both resolve to `_age_below(12)` — and
# `restrict_bhasma` uses the same boundary, so paediatric dosing uses it too rather
# than inventing a third definition of "child" in the same file.
PAEDIATRIC_AGE = 12
ADOLESCENT_AGE = 16
ELDER_START_LOW_AGE = 75
FALLS_CAUTION_AGE = 65
_SEDATING_HERBS = {"jatamansi", "tagara", "sarpagandha", "ashwagandha", "brahmi", "shankhpushpi"}


def _lower_end(dose: str) -> str:
    """'3–5g with warm water' → '3g with warm water'; '1–2 tablets' → '1 tablet'."""
    def repl(m):
        low, space, unit = m.group(1), m.group(2), m.group(3) or ""
        if unit.startswith("tablet"):
            unit = "tablet" if low == "1" else "tablets"
        return f"{low}{space}{unit}"
    dose = dose or ""
    # "500mg–1g": a unit on each end.
    two_units = re.sub(r"(\d+(?:\.\d+)?\s*(?:mg|g|ml))\s*(?:–|-|to)\s*\d+(?:\.\d+)?\s*(?:mg|g|ml)\b",
                       r"\1", dose, count=1)
    if two_units != dose:
        return two_units
    return re.sub(r"(\d+(?:\.\d+)?)\s*(?:–|-|to)\s*\d+(?:\.\d+)?(\s*)(mg|g|ml|tablets?|tsp|tbsp)?",
                  repl, dose, count=1)


def _apply_patient_dosage(med: dict, age: int) -> None:
    """Put the dose this patient should actually take on `dosage`.

    `dosage_pediatric` is authored on 95 of the 157 formulations and, before this,
    was read by `scripts/build_vectors.py` and the medicine card — as a footnote
    beneath the adult dose. The `dosage_schedule`, which is the list a patient
    actually follows morning by morning, was built from the adult figure at every
    age. An 11-year-old prescribed Agastya Rasayana read "3–5g" in one place,
    "10–15g twice daily" in the schedule, and "1g with honey" in a note.

    Mutates a COPY — see `_annotate`. Never hand this a `_MEDICINES_KB` entry.
    """
    if age >= ELDER_START_LOW_AGE:
        # Start low: Agni and clearance both fall with age, and a frail patient is
        # where an adult-range dose does harm first.
        lower = _lower_end(med.get("dosage", ""))
        if lower != med.get("dosage", ""):
            med["dosage_adult"] = med.get("dosage", "")
            med["dosage"] = lower
            med["dosage_basis"] = "older adult (start at the lower end; the Vaidya may raise it)"
        return
    if PAEDIATRIC_AGE <= age < ADOLESCENT_AGE:
        # 12–15 sat on the full adult range. Under 16 the Dhatus are still forming
        # (Charaka Vimanasthana 8.122, the line Panchakarma draws), so they take the
        # bottom of it: "3–5g" becomes "3g". The range's own floor, not an invented
        # fraction — the author of every range already judged that figure safe.
        lower = _lower_end(med.get("dosage", ""))
        if lower != med.get("dosage", ""):
            med["dosage_adult"] = med.get("dosage", "")
            med["dosage"] = lower
            med["dosage_basis"] = "adolescent (lower end of the adult range)"
        return
    if age >= PAEDIATRIC_AGE:
        return
    paediatric = (med.get("dosage_pediatric") or "").strip()
    if paediatric:
        med["dosage_adult"] = med.get("dosage", "")
        med["dosage"] = paediatric
        med["dosage_basis"] = "paediatric"


def _has_paediatric_dose(med: dict, age: int) -> bool:
    """Whether this formulation can be dosed for this patient at all."""
    return age >= PAEDIATRIC_AGE or bool((med.get("dosage_pediatric") or "").strip())


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
# The per-Dosha lifestyle lines were printed whatever else was on file: a Pitta
# patient with kidney disease was told "coconut water daily" (a potassium load),
# a Kapha patient on insulin "skip breakfast if not hungry", a Vata patient
# allergic to sesame "Abhyanga daily with sesame oil", a Kapha cardiac patient
# "vigorous exercise daily". (phrase, conditions or allergens or states, safe phrase)
_LIFESTYLE_RESTRICTIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("Coconut water and pomegranate daily.",
     ("chronic_kidney_disease", "kidney_disease"),
     "Pomegranate daily; coconut water only if your kidney doctor allows potassium."),
    ("Use generous ghee.", ("allergy:dairy",), "Cook with oil rather than ghee."),
    ("Use generous ghee.",
     ("gallstones", "high_cholesterol", "obesity", "fatty_liver", "metabolic_syndrome"),
     "Use a little oil or ghee in cooking, as your conditions allow."),
    ("Abhyanga (oil massage) daily with sesame oil.",
     ("allergy:sesame",),
     "Abhyanga (oil massage) daily with coconut oil."),
    ("Honey over sugar.",
     ("diabetes", "diabetes_type1", "diabetes_type2", "allergy:honey"),
     "Keep both honey and sugar low."),
    ("Skip breakfast if not hungry.",
     ("diabetes", "diabetes_type1", "diabetes_type2", "state:child", "state:pregnant"),
     "Keep breakfast light rather than skipping it."),
    ("Vigorous exercise daily.",
     ("heart_disease", "atrial_fibrillation", "hypertension", "state:pregnant", "state:over_65"),
     "Brisk walking daily, at a pace your doctor has cleared."),
    ("Vigorous exercise daily.",
     ("asthma", "copd", "chronic_bronchitis"),
     "Daily exercise, warming up first and stopping at any wheeze; keep the reliever inhaler at hand."),
)


def _gate_lifestyle(lifestyle: dict, medical_history, allergies, age: int, pregnant: bool) -> tuple[dict, list[str]]:
    """Replace a lifestyle line a declared condition, allergy or state rules out, and say so."""
    states = {f"allergy:{e['key']}" for e in _allergen_entries(allergies)}
    if age < 16:
        states.add("state:child")
    if age > 65:
        states.add("state:over_65")
    if pregnant:
        states.add("state:pregnant")
    out, notes = dict(lifestyle), []
    for phrase, triggers, safe in _LIFESTYLE_RESTRICTIONS:
        why = next((t for t in triggers if t in states or any(
            condition_matches_term(c, t) for c in medical_history or [] if ":" not in t)), None)
        if not why:
            continue
        for field in ("dietary_note", "routine_note"):
            if phrase in (out.get(field) or ""):
                out[field] = out[field].replace(phrase, safe)
                notes.append(f"'{phrase}' changed — {why.split(':')[-1].replace('_', ' ')}.")
    return out, notes


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


def _active_herbs(med: dict) -> set[str]:
    return set().union(*(herbs_in(i.split(" (")[0]) for i in med.get("ingredients") or []))


def _repeats_a_herb(a: dict, b: dict) -> bool:
    """Whether one of the two is a single-herb preparation of a herb the other gives.

    External oils are not compared with internal medicines: Mahanarayana Taila on
    the skin does not double an Ashwagandha dose taken by mouth."""
    if (a.get("application_type") == "external") != (b.get("application_type") == "external"):
        return False
    ha, hb = _active_herbs(a), _active_herbs(b)
    return (len(ha) == 1 and ha <= hb) or (len(hb) == 1 and hb <= ha)


_MINERAL_MARKERS = ("bhasma", "pishti", "parada", "mercury", "gandhaka", "hingula",
                    "manahshila", "haratala", "tamra", "abhraka", "loha", "mandura")


def _is_mineral(med: dict) -> bool:
    """A Rasa Aushadhi or mineral preparation, by type or by what is in it."""
    t = (med.get("type") or "").lower()
    if any(k in t for k in ("bhasma", "pishti")) or t.startswith("rasa"):
        return True
    text = " ".join(med.get("ingredients") or []).lower()
    return any(k in text for k in _MINERAL_MARKERS)


# The form's category chips, as medication classes.
_FORM_CATEGORY_CLASSES = {
    "blood_thinners": ["anticoagulants", "antiplatelets"],
    "diabetes_medication": ["insulin_or_sulfonylurea", "metformin"],
    "thyroid_medication": ["thyroid_hormone"],
    "antihypertensives": ["antihypertensives"],
    "immunosuppressants": ["immunosuppressants", "corticosteroids"],
    "sedatives": ["sedatives"],
    "antiepileptics": ["antiepileptics"],
    "antidepressants": ["ssri_snri"],
    "cardiac_glycosides": ["digoxin"],
    "nsaids": ["nsaids"],
    "hormone_therapy": ["hormonal_contraceptives"],
    "antibiotics": ["metronidazole_disulfiram"],
}


def _patient_classes(typed, form_categories) -> set[str]:
    from services.panchakarma_engine import _medication_findings
    out = set(_medication_findings(typed or [])["tokens"])
    for c in form_categories or []:
        out |= set(_FORM_CATEGORY_CLASSES.get(str(c).lower(), []))
    return out


def _herb_keys(med: dict) -> set[str]:
    keys = set(_active_herbs(med))
    if _formulation_class(med) == "fermented":
        keys.add("@fermented")
    return keys


def _interaction_findings(herbs: set[str], classes: set[str]) -> tuple[str | None, list[str]]:
    """Major (withhold, reason) and moderate (cautions) herb x medicine findings."""
    from services.panchakarma_engine import pk_clinical
    labels = {k: v.get("label", k) for k, v in (pk_clinical.get("medication_classes") or {}).items()
              if isinstance(v, dict)}
    cautions: list[str] = []
    for rule in (pk_clinical.get("herb_drug_interactions") or {}).get("rules", []):
        h = herbs & set(rule["herbs"])
        c = classes & set(rule["classes"])
        if not (h and c):
            continue
        herb = "the alcohol in it" if h == {"@fermented"} else ", ".join(sorted(x for x in h if x != "@fermented"))
        med = ", ".join(sorted(labels.get(x, x).lower() for x in c))
        text = f"{herb.title() if herb[0] != 't' else herb} with your {med}: {rule['mechanism']}"
        if rule["severity"] == "major":
            return f"Interaction — {text}", []
        cautions.append(text)
    return None, cautions


def _formulation_rule_findings(med: dict, medical_history, age: int,
                               classes: set[str] | None = None) -> tuple[str | None, list[str]]:
    """What the formulation's base and metal rule out for this patient."""
    from services.panchakarma_engine import pk_clinical
    rules = pk_clinical.get("formulation_rules") or {}
    t = (med.get("type") or "").lower()
    name = med.get("name", "")
    has = lambda conds: next((c for c in medical_history or []
                              if any(condition_matches_term(c, x) for x in conds)), None)
    hm = rules.get("heavy_metal") or {}
    text = (" ".join(med.get("ingredients") or []) + " " + name).lower()
    if any(re.search(rf"\b{re.escape(m)}\b", text) for m in hm.get("markers", [])) \
            or name in hm.get("classical_contains", []):
        return f"Prescribed in person only: {hm.get('mechanism', '')}", []
    cautions: list[str] = []
    fermented = _formulation_class(med) == "fermented"
    if fermented and age < int(rules.get("fermented_minor_age") or 18):
        return ("Contains self-generated alcohol (an Arishta or Asava) — not given under 18 "
                "without a Vaidya setting the dose."), []
    es = rules.get("fermented_elderly_sedative") or {}
    if fermented and age >= int(es.get("min_age") or 200) and set(es.get("classes") or []) & (classes or set()):
        return f"Withheld at {age} with your sleeping or sedating medicine: {es['mechanism']}", []
    sb = rules.get("sugar_base") or {}
    if any(k in t for k in sb.get("types", [])) and (c := has(sb.get("conditions", []))):
        return f"Contraindicated with {c.replace('_', ' ')}: {sb['mechanism']}", []
    for key in ("fermented_alcohol", "fermented_sugar", "fermented_reflux"):
        r = rules.get(key) or {}
        if fermented and (c := has(r.get("conditions", []))):
            if r.get("severity") == "major":
                return f"Contraindicated with {c.replace('_', ' ')}: {r['mechanism']}", []
            cautions.append(f"{c.replace('_', ' ').capitalize()}: {r['mechanism']}")
    return None, cautions


def _herb_table_findings(med: dict, findings: list[str]) -> tuple[str | None, list[str]]:
    """Hard bar (reason) and soft cautions from the shared per-herb safety table."""
    from services.panchakarma_engine import _match_contraindications, pk_clinical
    table = pk_clinical.get("herbs") or {}
    cautions: list[str] = []
    for key in sorted(_active_herbs(med)):
        entry = table.get(key)
        if not isinstance(entry, dict):
            continue
        display = entry.get("display", key.title())
        hard = _match_contraindications(findings, entry.get("hard") or {})
        if hard:
            c, mech = hard[0]
            return f"Contains {display}, contraindicated with {c.replace('_', ' ')}: {mech}", []
        for c, mech in _match_contraindications(findings, entry.get("soft") or {}):
            cautions.append(f"{display} ({c.replace('_', ' ')}): {mech}")
    return None, cautions


def _formulation_class(med: dict) -> str | None:
    """The classes a plan carries one of at most.

    Three Guggulu formulations together (Kaishor, Yogaraj and Vatari, for one
    osteoarthritis patient) is three doses of the same resin, a known gastric
    irritant. Two Arishtas or Asavas is two self-generated alcohol doses. Two
    mineral preparations stack the metal load. Shared herbs between ordinary
    compound formulations stay a Vaidya's call; these three are not."""
    t = (med.get("type") or "").lower()
    name = (med.get("name") or "").lower()
    if "guggulu" in t or "guggulu" in name:
        return "guggulu"
    if any(k in t for k in ("arishta", "asava")) or name.endswith(("arishta", "asava")):
        return "fermented"
    if _is_mineral(med):
        return "mineral"
    return None


_WELLNESS_KARMA = {"rasayana", "balya", "brimhana"}
# Kindling and digesting are wellness only where Agni or Ama asks for them.
_AGNI_KARMA = {"deepana", "pachana", "ama pachana"}

_CLASS_LABEL = {"guggulu": "a Guggulu formulation", "fermented": "a fermented (Arishta/Asava) preparation",
                "mineral": "a mineral preparation"}

# How many medicines a person takes by mouth at once. The plan gave seven in a
# third of all plans — three condition medicines, two more, two "general
# wellness" ones — each with its own timing and Anupana. Adherence falls with
# every addition and every addition is another interaction. External oils are
# not counted.
_MAX_INTERNAL = 4


def _doubling_note(med: dict, hit: dict) -> str:
    """Says it is the same medicine when every active herb in it is covered."""
    active = _active_herbs(med)
    taken = hit["already_taking"]
    if active and active <= herbs_in(taken):
        return (f"You already take {taken}, which is the same medicine as {med['name']}. "
                "Taking both doubles the dose. Ask a Vaidya which one to keep.")
    return (f"You already take {taken}, which shares {', '.join(hit['herbs'])} with "
            f"{med['name']}. Taking both doubles that dose. Ask a Vaidya which one to keep.")


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
    # The Ritu the rest of the app uses — `current_season` when declared, else the
    # calendar. An empty season switched the seasonal signal off for everyone who
    # never set one.
    from services.panchakarma_engine import _current_ritu
    season      = _current_ritu(user_profile.get("current_season"))
    is_pregnant = bool(user_profile.get("pregnancy_or_nursing", False))
    gender      = (user_profile.get("gender") or "").lower()
    age         = int(user_profile.get("age") or 30)

    # Structured medication multi-select from preferences (list of category strings)
    current_meds_prefs = medicines_prefs.get("current_allopathic_medications") or []
    # Also include free-text from user profile (legacy)
    current_meds_profile = user_profile.get("current_medications") or []
    current_meds = [m.lower().replace(" ", "_") for m in current_meds_prefs + current_meds_profile]
    resolved_tokens, medication_review = _resolve_medications(current_meds_profile)
    current_meds += [t for t in resolved_tokens if t not in current_meds]

    allergies       = user_profile.get("allergies") or []
    allergen_entries = _allergen_entries(allergies)
    medical_history = [c.lower() for c in (user_profile.get("medical_history") or [])]
    ingredient_access  = (medicines_prefs.get("ingredient_access") or "can_buy_herbs").lower()
    previous_tried     = [m.lower().strip() for m in (medicines_prefs.get("previous_ayurvedic_medicines") or [])]
    # What they take now, as against what they tried before. Panchakarma checked
    # this and the medicines plan, which prescribes the most formulations, did not.
    taking_now         = medicines_prefs.get("current_ayurvedic_medicines") or []

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

    # ── Derived states the contraindication gate could not previously see ──
    # `pitta_excess` guards 31 formulations, `ama_condition` 3, `children` 8 —
    # none of which can ever appear in `medical_history`, which was the only thing
    # the gate read. Everything here is already computed a few lines above.
    # Note: NOT `vikriti={vikriti_dominant, vikriti_secondary}` — those two already
    # fall back to Prakriti a few lines up, and the gate has to know the difference
    # between an assessed imbalance and a constitution standing in for one.
    derived_states = build_derived_states(
        user_profile,
        ama_level=ama_level,
        # Symptoms arrive by two different vocabularies. The remedies preferences
        # are keyed by remedy-KB symptom id (`fever_mild`, `diarrhea`) — the same
        # ids the KB's own contraindications name. `current_symptoms` on the
        # profile holds the Vikriti clusters onboarding collects (`heartburn_
        # acidity`), which name none of the acute states these tokens are about;
        # it is included because it costs nothing, not because it will match.
        symptoms=[
            *(medicines_prefs.get("symptom_severity") or {}),
            *(medicines_prefs.get("symptom_duration") or {}),
            *(medicines_prefs.get("symptoms") or []),
            *(user_profile.get("current_symptoms") or []),
        ],
    )

    # ── Score and filter ──────────────────────────────────────────────────
    from services.panchakarma_engine import _patient_findings
    herb_findings = list(medical_history) + _patient_findings(user_profile) + (
        ["pregnancy"] if is_pregnant else [])
    herb_notes: dict[str, list[str]] = {}
    patient_classes = _patient_classes(current_meds_profile, current_meds_prefs)
    scored:  list[tuple[int, dict]] = []
    blocked: list[dict] = []

    for med in _MEDICINES_KB:
        tier = med.get("safety_tier", 1)
        if tier > max_safety_tier:
            continue
        # By composition, not by the type string: the list matched "bhasma (ash)"
        # and the pishti spelling only, so "bhasma (calcined mineral)", "rasa
        # (mineral-herbal tablet)" and "rasa aushadhi" passed — Shwas Kuthar Rasa,
        # purified mercury and sulphur with a paediatric dose of its own, was one
        # scoring change away from a ten-year-old's asthma plan.
        if restrict_bhasma and _is_mineral(med):
            blocked.append({"name": med["name"], "reason": "Mineral preparations require extra caution for your age group — consult a Vaidya"})
            continue
        # No authored paediatric dose means there is no dose we can print for this
        # patient. Serving it with the adult figure is what happened before and is
        # the one option that is definitely wrong; serving it with no figure asks a
        # parent to guess. It is withheld and SAID, the way `blocked_medicines`
        # already surfaces the rest — 62 of 157 formulations have no paediatric
        # dose, and they were 29% of the medicine slots a child was being served.
        if not _has_paediatric_dose(med, age):
            blocked.append({
                "name": med["name"],
                "reason": ("No paediatric dose is established for this formulation — "
                           "a Vaidya must set the dose for this age"),
            })
            continue
        if not gender_ok(med):
            continue
        is_safe, reason = _check_medicine_safety(
            med, is_pregnant, current_meds, allergies, medical_history, derived_states)
        if not is_safe:
            blocked.append({"name": med["name"], "reason": reason})
            continue
        # The per-herb table Panchakarma reads. Its own docstring records Shilajit
        # going to kidney patients and Sarpagandha to anyone with hypertension; that
        # was fixed for Panchakarma and this plan still did both — Shilajit is even
        # listed here as *indicated* for kidney disease. One herb, one table.
        herb_bar, herb_cautions = _herb_table_findings(med, herb_findings)
        if not herb_bar:
            herb_bar, more = _interaction_findings(_herb_keys(med), patient_classes)
            herb_cautions += more
        if not herb_bar:
            herb_bar, more = _formulation_rule_findings(med, medical_history, age, patient_classes)
            herb_cautions += more
        if herb_bar:
            blocked.append({"name": med["name"], "reason": herb_bar})
            continue
        if herb_cautions:
            herb_notes[med["name"]] = herb_cautions

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
    # "General wellness" means Rasayana, Deepana or Pachana — something a person
    # without a diagnosis may take for weeks. It used to mean any formulation with
    # a positive score, which put Sitopaladi, a cough powder, into the plan of
    # everyone with a Vata or Kapha imbalance and nothing to treat.
    general_wellness = [(s, m) for s, m in scored if (s, m) not in condition_matched
                        and {k.lower() for k in m.get("karma", [])} & (
                            _WELLNESS_KARMA | (_AGNI_KARMA if agni_type == "manda"
                                               or ama_level in ("moderate", "high") else set()))]

    # ── Condition coverage tier (honesty for rare / unmapped diseases) ─────
    # Which of the user's conditions actually have a KB-matched formulation?
    matched_conditions = {
        c for _, m in condition_matched
        for c in normalised_conditions
        if _med_covers_condition(m, c)
    }
    uncovered_all = [c for c in normalised_conditions if c not in matched_conditions]
    # "No formulation matches hypothyroid" was false: Kanchanara Guggulu does, and was
    # withheld for the patient's thyroxine. Withheld and absent are different answers.
    all_withheld = [c for c in uncovered_all
                    if any(_med_covers_condition(m, c) for m in _MEDICINES_KB)]
    uncovered_conditions = [c for c in uncovered_all if c not in all_withheld]
    # Covered only from the outside: every internal formulation for the condition
    # was barred, and an oil is all that is left. A Pitta patient with sciatica —
    # every sciatica Guggulu and Kashayam is contraindicated in aggravated Pitta —
    # read "curated" above a plan with nothing to take by mouth.
    external_only = [
        c for c in normalised_conditions if c in matched_conditions and not any(
            _med_covers_condition(m, c) and m.get("application_type") != "external"
            for _, m in condition_matched)
    ]
    if not normalised_conditions:
        condition_coverage = "wellness"      # no conditions — general dosha wellness
    elif not condition_matched:
        condition_coverage = "general"       # rare/unmapped — only dosha-based general meds
    elif uncovered_conditions or all_withheld:
        condition_coverage = "partial"       # some conditions matched, some not
    else:
        condition_coverage = "curated"       # all conditions have KB-matched formulations

    # One herb, prescribed twice. 33 of 400 sampled plans gave Brahmi Churna and
    # Brahmi Vati together, and Arjuna Churna beside Arjunarishta, Haritaki Churna
    # beside Triphala. A single-herb preparation of a herb another formulation in
    # the plan already gives is the same dose twice under two names, and the slot
    # goes to the next candidate. Shared herbs between compound formulations
    # (Triphala's fruits, Trikatu's spices) are ordinary compounding and are left
    # alone: deciding those is a Vaidya's call, not a set operation.
    not_doubled: list[dict] = []

    def _pick(candidates: list[dict], n: int, chosen: list[dict]) -> list[dict]:
        out = []
        for med in candidates:
            if len(out) >= n:
                break
            clash = next((c for c in chosen + out if _repeats_a_herb(med, c)), None)
            if clash:
                not_doubled.append({
                    "name": med["name"],
                    "reason": f"Its herb is already in {clash['name']}, so it would double the dose.",
                })
                continue
            cls = _formulation_class(med)
            same = next((c for c in chosen + out if cls and _formulation_class(c) == cls
                         and (c.get("application_type") == "external") == (med.get("application_type") == "external")),
                        None)
            if same:
                not_doubled.append({
                    "name": med["name"],
                    "reason": f"The plan already gives {_CLASS_LABEL[cls]} ({same['name']}); two at once double it.",
                })
                continue
            if med.get("application_type") != "external" and \
                    sum(1 for c in chosen + out if c.get("application_type") != "external") >= _MAX_INTERNAL:
                continue
            out.append(med)
        return out

    # Every condition first, then depth. Ranked as one list, the higher-scoring
    # condition took every slot: an anxiety + IBS patient got four digestive
    # formulations and nothing for anxiety, though anxiety formulations had passed
    # every gate. The best for each condition goes first, in the order recorded.
    ordered: list[dict] = []
    for c in normalised_conditions:
        best = next((m for _, m in condition_matched if _med_covers_condition(m, c)
                     and m.get("application_type") != "external" and m not in ordered), None)
        if best:
            ordered.append(best)
    ordered += [m for _, m in condition_matched if m not in ordered]
    primary_formulations    = _pick(ordered, 3, [])
    rest = [m for _, m in condition_matched if m not in primary_formulations
            and m["name"] not in {d["name"] for d in not_doubled}]
    supporting_formulations = _pick(rest, 2, primary_formulations)
    # General-wellness filler only where the conditions left room. Beside three
    # condition medicines it added a cough powder to an osteoarthritis plan.
    internal_so_far = [m for m in primary_formulations + supporting_formulations
                       if m.get("application_type") != "external"]
    if condition_coverage in ("wellness", "general", "partial") or len(internal_so_far) < 2:
        supporting_formulations += _pick([m for _, m in general_wellness], 2,
                                         primary_formulations + supporting_formulations)
    all_selected            = primary_formulations + supporting_formulations

    # One external oil: two medicated oils for the same complaint is the same
    # application twice, and both are usually sesame-based.
    external_oils           = [m for m in all_selected if m.get("application_type") == "external"][:1]
    primary_formulations    = [m for m in primary_formulations    if m.get("application_type") != "external"]
    supporting_formulations = [m for m in supporting_formulations if m.get("application_type") != "external"]

    # ── Condition-optimised Anupana per medicine ──────────────────────────
    anupana_map: dict[str, str] = {}

    def _annotate(meds: list[dict]) -> list[dict]:
        """Annotate COPIES. `_MEDICINES_KB` is a module-level singleton and these
        values are per-patient, so writing them onto the KB entry publishes one
        patient's data to every other request in the process.

        That was not theoretical. `generate_medicines_plan` is synchronous and
        FastAPI runs sync endpoints in a threadpool, so two requests genuinely
        interleave here. Two concurrent users, one declaring Triphala as previously
        tried and one declaring nothing, over 80 builds: the second user was shown
        Triphala badged "Tried before" — the first user's declaration, read off the
        shared dict. Once in 80, so it is rare rather than constant, which is worse
        than constant: it cannot be reproduced from a bug report and every test that
        builds one plan at a time passes. `selected_anupana` — the condition
        -optimised liquid to take the medicine with — crosses over the same way.
        """
        out = []
        for med in meds:
            m = dict(med)
            anupana, anupana_note = _allergen_safe_anupana(
                _select_anupana(m, primary_condition, agni_type), allergen_entries, medical_history)
            anupana_map[m["id"]] = anupana
            m["selected_anupana"] = anupana
            if anupana_note:
                m["anupana_note"] = anupana_note
            m["previously_tried"] = m["name"].lower() in previous_tried
            # Flagged, not withheld: usually the answer is to stop the one being
            # self-administered, which is for the patient and their Vaidya.
            m["already_taking"] = [
                {**hit, "note": _doubling_note(m, hit)}
                for hit in already_taking(m.get("ingredients") or [], taking_now)
            ]
            # The half of `contraindications` that is not a user state: "external use
            # only", "authenticated source only", "do not swallow the camphor". They
            # were filed in a field only a filter read, so a filter that could not
            # match them dropped them — and nobody was ever told. They belong with the
            # medicine, not in the gate.
            m["usage_cautions"], m["red_flags"] = usage_notes(m.get("contraindications"))
            m["usage_cautions"] += assumed_state_notes(m.get("contraindications"), derived_states)
            m["usage_cautions"] += herb_notes.get(m["name"], [])
            if age >= FALLS_CAUTION_AGE and (_active_herbs(m) & _SEDATING_HERBS
                                             or _formulation_class(m) == "fermented"):
                m["usage_cautions"].append(
                    "Can cause drowsiness or unsteadiness — take it at night, rise slowly, and "
                    "stop if you feel light-headed (falls are the main risk after 65).")
            _apply_patient_dosage(m, age)
            out.append(m)
        return out

    primary_formulations    = _annotate(primary_formulations)
    supporting_formulations = _annotate(supporting_formulations)
    external_oils           = _annotate(external_oils)

    # ── Build schedules and protocol ──────────────────────────────────────
    dosage_schedule    = _build_dosage_schedule(primary_formulations + supporting_formulations, anupana_map)
    treatment_protocol = _build_treatment_protocol(primary_formulations + supporting_formulations, agni_type, normalised_conditions)

    lifestyle_guidance, lifestyle_notes = _gate_lifestyle(
        _LIFESTYLE_BY_DOSHA.get(vikriti_dominant, _LIFESTYLE_BY_DOSHA["vata"]),
        medical_history, allergies, age, is_pregnant)
    if lifestyle_notes:
        lifestyle_guidance = {**lifestyle_guidance, "changed_for_you": lifestyle_notes}

    # Shodhana is the Panchakarma engine's verdict, not a second opinion here. This
    # plan labelled itself "Shodhana — Vamana/Virechana indicated" from Ama and a
    # Kapha condition count alone, for ten-year-olds, eighty-year-olds and pregnant
    # women the Panchakarma engine refuses. Ask it.
    shodhana_withheld = None
    shodhana_strength = "full" if chikitsa_approach == "Shodhana" else None
    if chikitsa_approach == "Shodhana":
        from services.panchakarma_engine import generate_panchakarma_plan
        # The whole engine, not its eligibility step alone: the medicine and
        # condition bars apply when a Karma is chosen, so eligibility alone told a
        # transplant patient on tacrolimus, steroids and insulin that purification
        # was indicated.
        pk_plan = generate_panchakarma_plan(
            {**user_profile, "current_medications": current_meds_profile},
            {"setting": "clinic", "detox_experience": "some", "available_time_days": 14})
        verdict = dict(pk_plan["clinical_decisions"]["shodhana_or_shamana"])
        karma = (pk_plan["clinical_decisions"].get("pradhana_karma_selected") or {})
        if verdict.get("type") != "shamana" and not karma.get("primary"):
            verdict = {"type": "shamana", "blocking_reasons": [
                "no purification procedure is safe with your conditions and medicines"]}
        elif karma.get("safety_substitution"):
            verdict.setdefault("restricting_reasons", [])
            verdict["restricting_reasons"] = list(verdict["restricting_reasons"]) + [
                f"only {karma['primary'].replace('_', ' ').title()} would be safe for you — "
                f"{karma.get('original_karma', 'the usual Karma').title()} is not"]
            if verdict.get("type") == "shodhana":
                verdict["type"] = "mridu_shodhana"
        if verdict.get("type") == "shamana":
            chikitsa_approach = "Shamana"
            shodhana_withheld = (
                "Your Ama and conditions would point toward purification, but it is not "
                "advised for you: " + "; ".join(verdict.get("blocking_reasons") or verdict.get("reasons") or [])
                + ". These medicines pacify instead.")
        elif verdict.get("type") == "mridu_shodhana":
            shodhana_strength = "mridu"
            shodhana_withheld = (
                "Only a mild or restricted purification is suitable for you, never Vamana: "
                + "; ".join(verdict.get("restricting_reasons") or []) + ".")

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
        "shodhana_withheld":     shodhana_withheld,
        "shodhana_strength":     shodhana_strength,
        "active_conditions":     normalised_conditions,
        "condition_coverage":    condition_coverage,
        "uncovered_conditions":  uncovered_conditions,
        "vaidya_review_required": bool(uncovered_conditions or external_only or all_withheld),
        "coverage_note": " ".join(x for x in (
            ("No formulation in our classical knowledge base specifically matches "
             f"{', '.join(c.replace('_', ' ') for c in uncovered_conditions)}. "
             "The medicines below are dosha-balancing general support — a qualified Vaidya "
             "should prescribe condition-specific formulations for these.")
            if uncovered_conditions else "",
            ("Every formulation we hold for "
             f"{', '.join(c.replace('_', ' ') for c in all_withheld)} is unsuitable for you — "
             "see the excluded list for why — so none is given for it. A Vaidya should choose "
             "one in person.")
            if all_withheld else "",
            ("Every medicine taken by mouth for "
             f"{', '.join(c.replace('_', ' ') for c in external_only)} is unsuitable for you "
             "(see the excluded list), so only an external oil is given for it. A Vaidya "
             "should choose an internal formulation in person.")
            if external_only else "",
        ) if x),
        "external_only_conditions": external_only,
        "withheld_conditions":   all_withheld,
        "primary_formulations":  primary_formulations,
        "supporting_formulations": supporting_formulations,
        "external_therapies":    external_oils,
        "dosage_schedule":       dosage_schedule,
        "treatment_protocol":    treatment_protocol,
        "lifestyle_guidance":    lifestyle_guidance,
        "blocked_medicines":     blocked,
        "medication_review":     medication_review,
        "not_doubled":           not_doubled,
        "enriched":              False,
        "disclaimer": (
            "These Ayurvedic formulations are recommended based on your personalised profile. "
            "This is wellness guidance, not a substitute for clinical diagnosis. "
            "Always consult a qualified Ayurvedic Vaidya or physician before starting any new "
            "herbal medicine, particularly if you are on prescription medications."
        ),
    }
