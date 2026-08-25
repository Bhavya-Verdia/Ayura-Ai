"""
Authored triage of every contraindication token in the medicines / home-remedy KBs.

The medicines and home-remedy knowledge bases carry a `contraindications` list per
entry. Those lists were written as prose-for-a-human and then fed to a gate that
compares them, as strings, against the user's `medical_history`. Sweeping all 164
distinct tokens against the 102 conditions the app can actually record found that
most of them could never match anything:

  - 7 named a disease the app records under a different name (`hypotension` vs the
    app's `low_blood_pressure`) — the same synonym-blind failure that left a HARD
    bar on bloodletting dead in the Panchakarma engine. Those now resolve through
    `condition_vocab.condition_matches_term`.
  - ~50 uses are not conditions at all but *derived states* the engine already
    computes and never passed to the gate: `pitta_excess`, `ama_condition`,
    `children`, `fever`, `diarrhea`.
  - ~40 are not user states in any form: `do_not_ingest`, `after_meals`,
    `authenticated_source_only`. They are usage warnings, and a gate is the wrong
    place for them — they need to reach the person taking the medicine.
  - the rest are emergency red flags ("stroke_symptoms_seek_emergency") whose whole
    value is being *shown* to someone, which a silent filter never does.

So a token is classified here into exactly one of four kinds, and `classify` is
total: a token that is none of them is a KB defect, and `tests/test_contraindication_tokens.py`
fails on it. Silence is not one of the options — the same rule the Panchakarma
contraindication coverage test enforces.

Every clinical claim below is authored, not derived, and carries its mechanism in
the comment or the surfaced text. Nothing here has been reviewed by a BAMS
practitioner yet; `scripts/reviewer_packet.py` emits it as Part 3 of the packet.
"""
from __future__ import annotations

from collections.abc import Callable

from engine.condition_vocab import condition_matches_term, normalize_condition

# ── Kind 1: disease tokens ────────────────────────────────────────────────────
# token -> the canonical conditions it bars. These are the tokens whose name the
# app does not use, so a string comparison could never fire: the KB says
# `gastric_ulcer`, onboarding records `peptic_ulcer`.
#
# Severity and control qualifiers ("severe_", "uncontrolled_") are deliberately
# mapped onto the *unqualified* condition. A profile has no field for how severe
# or how well-controlled a disease is, so the choice is between barring everyone
# with the disease and barring nobody. A withheld formulation costs the user one
# of ~200; a missed contraindication costs them the organ the herb acts on.
CONDITION_TOKENS: dict[str, tuple[str, ...]] = {
    # Ulcer disease — hot, pungent Deepana herbs (Trikatu, Pippali, Chitraka)
    # aggravate an eroded mucosa. 12 formulations carry one of these spellings.
    "ulcer": ("peptic_ulcer",),
    "active_ulcer": ("peptic_ulcer",),
    "gastric_ulcer": ("peptic_ulcer",),
    "gastric_ulcers": ("peptic_ulcer",),

    # IBD. The KB writes the class name; onboarding records the two diseases.
    "colitis": ("ulcerative_colitis", "ibd_crohns"),
    "inflammatory_bowel_disease": ("ulcerative_colitis", "ibd_crohns"),
    "ibs_diarrhea_predominant": ("ibs",),

    # Autoimmune disease as a class. Ashwagandha, Guduchi/Giloy and Amalaki are
    # Rasayana immunomodulators; in an autoimmune process the immune response is
    # the disease, so stimulating it is the wrong direction. Type 1 diabetes is
    # included because it IS autoimmune, which is easy to forget when the same
    # profile field also holds type 2.
    "autoimmune_disease": (
        "lupus", "rheumatoid_arthritis", "hashimoto", "multiple_sclerosis",
        "psoriasis", "celiac", "vitiligo", "ulcerative_colitis", "ibd_crohns",
        "ankylosing_spondylitis", "diabetes_type1",
    ),
    "auto_immune_disease_on_immunosuppressants": (
        "lupus", "rheumatoid_arthritis", "hashimoto", "multiple_sclerosis",
        "psoriasis", "celiac", "vitiligo", "ulcerative_colitis", "ibd_crohns",
        "ankylosing_spondylitis", "diabetes_type1",
    ),
    "alopecia_areata_autoimmune": ("alopecia", "lupus", "hashimoto", "vitiligo"),

    # Cardiac. `cardiac_disorders` guards Kanakasava (contains Datura) and
    # Shwas Kuthar Rasa (contains Vatsanabha/aconite) — both cardioactive.
    "cardiac_disorders": ("heart_disease", "heart_failure", "atrial_fibrillation"),
    "cardiac_oedema": ("heart_failure", "heart_disease"),

    # Hepatic. Tamra Bhasma (copper) and Sutashekara Rasa are hepatically handled;
    # the app has no "liver failure" checkbox, so bar on any recorded liver disease.
    "hepatic_failure": ("liver_disease", "fatty_liver", "hepatitis_chronic"),
    "liver_failure": ("liver_disease", "fatty_liver", "hepatitis_chronic"),
    "severe_liver_disease": ("liver_disease", "fatty_liver", "hepatitis_chronic"),
    "liver_disease_severe": ("liver_disease", "fatty_liver", "hepatitis_chronic"),

    # Renal.
    "severe_kidney_failure": ("chronic_kidney_disease",),
    "severe_renal_failure": ("chronic_kidney_disease",),

    # Diabetes. Guards Chyawanprash and the Asava/Arishta group, which are
    # jaggery- or sugar-based, and Kapikachu (L-DOPA, glycaemic effect).
    "diabetes_high_sugar": ("diabetes_type1", "diabetes_type2"),
    "diabetes_poorly_controlled": ("diabetes_type1", "diabetes_type2"),
    "uncontrolled_diabetes": ("diabetes_type1", "diabetes_type2"),
    "severe_diabetes": ("diabetes_type1", "diabetes_type2"),
    "type1_diabetes_on_insulin": ("diabetes_type1",),

    "severe_hypotension": ("low_blood_pressure",),
    "hypertension_due_to_lavana": ("hypertension",),
    # Haematology: Loha Bhasma / Lohasava are iron; an inherited haemolytic
    # anaemia is an iron-loading state, not an iron-deficient one.
    "severe_anemia": ("anemia", "sickle_cell", "thalassemia"),
    "severe_anaemia_hb_below_8": ("anemia", "sickle_cell", "thalassemia"),
    "severe_constipation": ("constipation_chronic",),
    "gallstones_active": ("gallstones",),
    "hyperuricemia_severe": ("gout",),
    "thyroid_hyperthyroidism": ("hyperthyroidism",),
    "hyperthyroid_use_opposite_approach": ("hyperthyroidism",),

    # Emaciation is also derived from BMI below — a user can be underweight
    # without ever ticking a box, which is the usual case.
    "emaciation": ("underweight",),
    "severe_emaciation": ("underweight",),

    # Uterine bleeding. Rajapravartini Vati is an emmenagogue.
    "heavy_menstruation": ("menorrhagia", "uterine_fibroids", "endometriosis"),
    "active_uterine_bleeding": ("menorrhagia", "uterine_fibroids", "endometriosis"),
    "heavy_bleeding": ("menorrhagia", "uterine_fibroids", "endometriosis"),
    "heavy_bleeding_for_vata_kapha": ("menorrhagia", "uterine_fibroids", "endometriosis"),
}

# ── Kind 2: derived-state tokens ──────────────────────────────────────────────
# The Panchakarma engine learned this the hard way: a derived Ayurvedic state is
# not in `medical_history`, so a gate that only reads medical history can never
# fire on one. `pitta_excess` alone guards 31 formulations and had never once
# matched anything.
#
# Dosha tokens read VIKRITI (current imbalance), not Prakriti — the same signal
# `_score_medicine` already uses — except `*_predominant` / `*_constitution_*`,
# which name the constitution and read Prakriti.
_Predicate = Callable[[dict], bool]


def _vikriti(dosha: str) -> _Predicate:
    return lambda s: dosha in s.get("vikriti", set())


def _prakriti(dosha: str) -> _Predicate:
    return lambda s: dosha in s.get("prakriti", set())


def _symptom(*names: str) -> _Predicate:
    return lambda s: bool(set(names) & s.get("symptoms", set()))


def _age_below(limit: int) -> _Predicate:
    return lambda s: s.get("age") is not None and s["age"] < limit


DERIVED_TOKENS: dict[str, tuple[_Predicate, str]] = {
    # Pitta-aggravated: Trikatu, Haritaki, Agnitundi and the other hot/pungent
    # Deepana-Pachana group add heat to a state that is already hot.
    "pitta_excess":          (_vikriti("pitta"), "Pitta is currently aggravated"),
    "pitta_disorders":       (_vikriti("pitta"), "Pitta is currently aggravated"),
    "active_pitta_disorders": (_vikriti("pitta"), "Pitta is currently aggravated"),
    "severe_pitta":          (_vikriti("pitta"), "Pitta is currently aggravated"),
    "severe_pitta_disorders": (_vikriti("pitta"), "Pitta is currently aggravated"),
    "kapha_excess":          (_vikriti("kapha"), "Kapha is currently aggravated"),
    "kapha_disorders":       (_vikriti("kapha"), "Kapha is currently aggravated"),
    "vata_excess":           (_vikriti("vata"), "Vata is currently aggravated"),
    "vata_disorders":        (_vikriti("vata"), "Vata is currently aggravated"),
    "severe_vata_disorders": (_vikriti("vata"), "Vata is currently aggravated"),
    "severe_vata_imbalance": (_vikriti("vata"), "Vata is currently aggravated"),
    "vata_predominant":      (_prakriti("vata"), "Vata-predominant constitution"),
    "vata_constitution_dominant": (_prakriti("vata"), "Vata-predominant constitution"),
    "kapha_predominant":     (_prakriti("kapha"), "Kapha-predominant constitution"),

    # Ama: a Rasayana or a Bala/Balarishta nourishing tonic on top of undigested
    # Ama feeds the Ama. Deepana-Pachana comes first — the same sequencing the
    # Panchakarma engine enforces.
    "ama": (lambda s: s.get("ama_level") in ("moderate", "high"),
            "Ama (metabolic toxins) present — nourishing tonics feed it"),
    "ama_condition": (lambda s: s.get("ama_level") in ("moderate", "high"),
                      "Ama (metabolic toxins) present — nourishing tonics feed it"),
    "ama_condition_severe": (lambda s: s.get("ama_level") == "high",
                             "High Ama — clear it with Deepana-Pachana first"),

    # Acute states, read from the symptoms the user is reporting in this very
    # request. Available to both engines and passed to neither before.
    "fever":        (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "active_fever": (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "acute_fever":  (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "fever_active": (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "active_fever_above_101": (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "high_fever_above_103":   (_symptom("fever_mild", "fever"), "you are reporting fever"),
    "pregnancy_with_fever":   (lambda s: bool(s.get("is_pregnant"))
                               and bool({"fever_mild", "fever"} & s.get("symptoms", set())),
                               "pregnancy with fever needs clinical assessment"),
    "diarrhea":       (_symptom("diarrhea", "dysentery"), "you are reporting diarrhoea"),
    "diarrhea_acute": (_symptom("diarrhea", "dysentery"), "you are reporting diarrhoea"),
    "severe_diarrhea": (_symptom("diarrhea", "dysentery"), "you are reporting diarrhoea"),
    "dysentery":      (_symptom("diarrhea", "dysentery"), "you are reporting diarrhoea"),
    "acute_cold_flu": (_symptom("common_cold", "cough_wet", "dry_cough", "sinus_congestion"),
                       "you are reporting an acute cold"),
    "chronic_cold_conditions": (_symptom("common_cold", "cough_wet", "dry_cough"),
                                "you are reporting cold symptoms"),

    # Age. Onboarding accepts age from 10, so paediatric contraindications are
    # reachable — and were gated for mineral Bhasmas only, by a separate rule.
    "children":                        (_age_below(12), "under 12"),
    "children_without_supervision":    (_age_below(12), "under 12"),
    "children_under_5":                (_age_below(5), "under 5"),
    "children_under_7_without_guidance": (_age_below(7), "under 7"),

    # Pregnancy/nursing is gated ahead of this by `pregnancy_safe`, but the token
    # appears in 95 contraindication lists and must not read as unclassified.
    "pregnancy":                            (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "pregnant":                             (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "pregnancy_first_trimester":            (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "pregnancy_first_trimester_high_doses": (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "pregnancy_high_doses":                 (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "pregnancy_high_doses_more_than_1g":    (lambda s: bool(s.get("is_pregnant")), "pregnancy"),
    "nursing":                              (lambda s: bool(s.get("is_pregnant")), "nursing"),

    # BMI, which the engine computes for every user. Bitter/scraping herbs
    # (Neem, Kutki, Triphala Guggulu) are Lekhana — they reduce tissue, which is
    # the wrong direction for someone already depleted.
    "emaciation": (lambda s: s.get("bmi") is not None and s["bmi"] < 18.5,
                   "BMI below 18.5 — reducing herbs deplete further"),
    "severe_emaciation": (lambda s: s.get("bmi") is not None and s["bmi"] < 16.0,
                          "BMI below 16 — reducing herbs deplete further"),
}

# ── Kind 3: usage cautions ────────────────────────────────────────────────────
# Not a user state in any form. These describe how the preparation is taken, and
# filed in `contraindications` they reached nobody: the gate cannot match them and
# the view never rendered the field. They are surfaced with the formulation now.
CAUTION_TOKENS: dict[str, str] = {
    "do_not_ingest":
        "External use only — do not swallow.",
    "do_not_swallow_large_quantities_camphor":
        "Contains camphor. Dissolve slowly in the mouth; do not swallow in quantity.",
    "after_meals":
        "Not to be used just after eating — Nasya is done on an empty stomach.",
    "authenticated_source_only":
        "Use only an authenticated, properly processed (Shodhita) source. Mineral "
        "preparations from uncertified suppliers carry a real heavy-metal risk.",
    "non_certified_source":
        "Use only a certified source — uncertified metal preparations carry a "
        "heavy-metal risk.",
    "long_term_use":
        "Not intended for continuous long-term use. Review the course periodically "
        "with a practitioner.",
    "without_clinical_supervision":
        "Take only under the supervision of a qualified practitioner.",
    "mucous_membranes":
        "Do not apply to mucous membranes — eyes, inner nose, or genitals.",
    "sensitive_skin_patch_test_first":
        "Patch-test on a small area of skin first if your skin is sensitive.",
    "anticoagulant_therapy_high_doses":
        "At high doses this can add to the effect of blood-thinning medication. "
        "Keep to the stated dose if you take an anticoagulant.",
    "trying_to_conceive_male":
        "Not advised while actively trying to conceive — it can lower sperm count.",
    "saffron_allergy":
        "Contains saffron. Do not use if you are allergic to it.",
    "alcohol_sensitivity":
        "Asava/Arishta preparations contain naturally fermented alcohol (5–10%).",
    "alcohol_dependence":
        "Asava/Arishta preparations contain naturally fermented alcohol — not "
        "suitable if you are recovering from alcohol dependence.",
    "active_hormonal_treatment_consult_first":
        "Speak to your doctor first if you are on hormonal treatment.",
    "hypoglycemia_risk":
        "Can lower blood sugar. Monitor closely if you take glucose-lowering "
        "medication.",
    "active_inflammation":
        "Do not use over an actively inflamed, hot or swollen area.",
}

# ── Kind 4: red flags ─────────────────────────────────────────────────────────
# "If this describes you, this is not the remedy — get seen." The whole value of
# these is being read by a person, and the only code that touched them was a
# filter that silently dropped them. Home remedies carry most of them.
#
# Several also name a real disease (`hemochromatosis`, `bradycardia`). Those still
# block when they appear in a user's free-text history — the matcher checks that
# first — but the app has no field for them, so they are shown as well.
RED_FLAG_TOKENS: dict[str, str] = {
    "stroke_symptoms_seek_emergency":
        "Sudden vertigo with weakness, slurred speech or facial droop is a stroke "
        "until proven otherwise — call emergency services, do not self-treat.",
    "anaphylaxis_use_epipen_immediately":
        "Hives with swelling of the lips or tongue, or any difficulty breathing, is "
        "anaphylaxis — use an adrenaline auto-injector and call emergency services.",
    "active_suicidal_ideation_seek_emergency_care":
        "If you are having thoughts of harming yourself, seek emergency care now. "
        "This is not something to treat at home.",
    "acute_asthma_attack_use_inhaler":
        "During an acute attack use your prescribed inhaler. These measures are for "
        "between attacks only.",
    "severe_vomiting_with_blood":
        "Vomiting blood, or what looks like coffee grounds, needs emergency care.",
    "jaundice_with_fever":
        "Yellow eyes or skin with fever needs medical assessment, not home treatment.",
    "strep_throat_with_high_fever":
        "A sore throat with high fever, white patches or a rash may be strep and may "
        "need antibiotics.",
    "severe_infection_with_fever":
        "Burning urination with fever or flank pain suggests a kidney infection — see "
        "a doctor, this needs antibiotics.",
    "active_infection_needs_antibiotics":
        "Discharge with fever, pain or a foul odour suggests infection needing "
        "antibiotics — see a doctor.",
    "postpartum_infection_seek_medical_care_first":
        "Fever, foul-smelling discharge or severe pain after childbirth needs urgent "
        "medical care.",
    "endometriosis_severe_consult_gynae":
        "Severe or worsening period pain deserves a gynaecological assessment — do "
        "not simply manage it at home.",
    "deep_wounds_require_stitches":
        "A deep or gaping wound needs stitches — go to a clinic.",
    "diabetic_wounds":
        "A wound on diabetic skin can deteriorate quickly. Have it looked at rather "
        "than treating it at home.",
    "second_degree_burns":
        "Blistering burns are second-degree — do not apply oils or pastes; get "
        "medical care.",
    "burns_on_face_or_genitals":
        "Burns on the face or genitals need medical care regardless of size.",
    "infected_open_wounds":
        "Do not apply to broken skin that is infected — spreading redness, pus or "
        "fever needs medical care.",
    "open_wounds":
        "Do not apply to broken or open skin.",
    "active_open_wounds":
        "Do not apply to open wounds.",
    "skin_infection":
        "Do not apply over an active skin infection.",
    "skin_infections":
        "Do not apply over an active skin infection.",
    "active_skin_infection":
        "Do not apply over an active skin infection.",
    "scalp_infection":
        "Do not apply to an infected scalp.",
    "active_infection":
        "Not while you have an active infection.",
    "active_eye_infection_conjunctivitis":
        "Not for use with an active eye infection — red, sticky or discharging eyes "
        "need to be seen.",
    "dandruff_with_weeping_lesions":
        "Weeping or crusted scalp lesions are not simple dandruff — have them seen.",
    "hair_loss_with_oily_scalp":
        "Heavy oil application is the wrong approach for an already oily scalp.",
    "deviated_nasal_septum_severe":
        "A significantly deviated septum needs an ENT opinion, not steam and drops.",
    "herniated_disc_severe":
        "Leg weakness, numbness or bladder changes with back pain need urgent "
        "assessment — not home treatment.",
    "epistaxis":
        "Stop if you get nosebleeds — warming nasal preparations can worsen them.",
    "thrombosed_piles":
        "A hard, acutely painful pile is likely thrombosed and needs to be seen.",
    "dehydration":
        "Do not use if you are dehydrated — replace fluids first.",
    "dehydration_severe":
        "Severe dehydration (dizziness, no urine, dry mouth) needs oral rehydration "
        "salts or medical care, not herbs.",
    "severe_dehydration":
        "Severe dehydration needs oral rehydration or medical care first.",
    "edema":
        "New or worsening swelling of the legs can be a heart, kidney or liver sign "
        "— have it assessed before treating it as a Kapha problem.",
    "hypoglycemia":
        "Do not use if you get low blood sugar episodes.",
    "hypokalemia":
        "Not with low potassium — liquorice (Yashtimadhu) lowers it further.",
    "hypercalcemia":
        "Not with high blood calcium — this is a calcium-bearing preparation.",
    "hyperparathyroidism":
        "Not with an overactive parathyroid — this is a calcium-bearing preparation.",
    "bradycardia":
        "Not if your resting pulse runs slow — this preparation can slow it further.",
    "slow_pulse":
        "Not if your resting pulse runs slow.",
    "hemochromatosis":
        "Not with iron overload (haemochromatosis) — this is an iron preparation.",
    "wilson_disease":
        "Not with Wilson's disease — this is a copper preparation and copper is "
        "exactly what that condition cannot clear.",
    "bile_duct_obstruction":
        "Not with a blocked bile duct — turmeric stimulates bile flow.",
    "bleeding_disorders":
        "Not with a bleeding disorder or while on anticoagulants.",
    # Also derived from the reported symptom, but the threshold is a number the
    # app never sees, so the person holding the thermometer has to be told.
    "high_fever_above_103":
        "A fever above 103°F (39.4°C) needs medical assessment, not home treatment.",
    "active_fever_above_101":
        "Not while running a fever above 101°F (38.3°C).",
}


def classify(token: str) -> str:
    """One of: condition, derived, caution, red_flag, vocabulary.

    `vocabulary` means the token already names a condition the app records under
    that name, so `condition_vocab` matches it with no entry needed here.
    Raises KeyError for anything unclassified — see the module docstring.
    """
    t = (token or "").lower().strip()
    if t in CONDITION_TOKENS:
        return "condition"
    if t in DERIVED_TOKENS:
        return "derived"
    if t in CAUTION_TOKENS:
        return "caution"
    if t in RED_FLAG_TOKENS:
        return "red_flag"
    from engine.condition_vocab import CONDITION_ALIASES
    from engine.dosha_analyzer import _DISEASE_DOSHA_SIGNAL
    if normalize_condition(t) in (set(CONDITION_ALIASES) | set(_DISEASE_DOSHA_SIGNAL)):
        return "vocabulary"
    raise KeyError(token)


def contraindication_hit(token: str, conditions, states: dict | None = None) -> str | None:
    """Reason this contraindication applies to this user, or None.

    Checks, in order: the authored disease mapping, the user's history as written
    (which covers free text and the synonym cases), then the derived state. A token
    can be both a disease and a derived state — `emaciation` is a diagnosis and a
    BMI — and either one firing is enough.
    """
    t = (token or "").lower().strip()
    history = [str(c) for c in (conditions or []) if c]

    for canonical in CONDITION_TOKENS.get(t, ()):
        for cond in history:
            if condition_matches_term(cond, canonical):
                return cond
    # Bidirectional: a KB token may be broader OR narrower than what the user
    # wrote ('liver_disease' vs 'liver'). `condition_matches_term` also resolves
    # synonyms, which plain string matching could not.
    for cond in history:
        if condition_matches_term(cond, t) or condition_matches_term(t, cond):
            return cond

    if states:
        pred = DERIVED_TOKENS.get(t)
        if pred and pred[0](states):
            return pred[1]
    return None


def usage_notes(tokens) -> tuple[list[str], list[str]]:
    """(cautions, red_flags) — the human-readable half of a contraindication list.

    Returned for display whether or not anything was blocked: a red flag describes
    a state the app cannot observe, so the only way it ever helps is by being read.
    """
    cautions, flags = [], []
    for tok in tokens or []:
        t = str(tok).lower().strip()
        if t in CAUTION_TOKENS and CAUTION_TOKENS[t] not in cautions:
            cautions.append(CAUTION_TOKENS[t])
        if t in RED_FLAG_TOKENS and RED_FLAG_TOKENS[t] not in flags:
            flags.append(RED_FLAG_TOKENS[t])
    return cautions, flags


def assumed_state_notes(tokens, states: dict | None) -> list[str]:
    """Cautions for contraindications that would fire if the user's constitution
    were taken as their current imbalance.

    Only ever reached when there is no Vikriti assessment on file. The KB's claim
    is about an aggravated dosha, so enforcing it against a constitution would bar
    a formulation on a guess — but saying nothing hides a caution the KB actually
    makes. Told, not enforced.
    """
    if not states or states.get("vikriti"):
        return []
    assumed = dict(states, vikriti=states.get("vikriti_assumed") or set())
    notes: list[str] = []
    for tok in tokens or []:
        t = str(tok).lower().strip()
        pred = DERIVED_TOKENS.get(t)
        if not pred or not t.startswith(("vata", "pitta", "kapha", "severe_vata",
                                         "severe_pitta", "active_pitta")):
            continue
        if pred[0](assumed) and pred[1] not in notes:
            notes.append(pred[1])
    return [
        f"{n.replace('is currently aggravated', 'aggravation')} is a listed "
        "contraindication for this formulation. Your Vikriti (current imbalance) "
        "has not been assessed, so this is based on your constitution — worth "
        "confirming with a practitioner."
        for n in notes
    ]


def build_derived_states(
    user_profile: dict,
    *,
    vikriti: dict | None = None,
    ama_level: str | None = None,
    symptoms=None,
    bmi: float | None = None,
) -> dict:
    """Collect the states the engines already compute into the shape the gate reads.

    Derived Ayurvedic states are not in `medical_history` and never will be, so a
    gate that reads only medical history cannot see them. This is the adapter.
    """
    prakriti = {
        str(user_profile.get("dominant_dosha") or "").lower(),
        str(user_profile.get("secondary_dosha") or "").lower(),
    } - {"", "none"}

    vikriti_set: set[str] = set()
    if vikriti:
        vikriti_set = {str(d).lower() for d in vikriti if d}
    else:
        for key in ("vikriti_dominant", "vikriti_secondary"):
            val = str(user_profile.get(key) or "").lower()
            if val and val != "none":
                vikriti_set.add(val)

    if ama_level is None:
        ama_level = str(user_profile.get("ama_level") or "low").lower()

    if bmi is None:
        try:
            weight = float(user_profile.get("weight") or 0)
            height_m = float(user_profile.get("height") or 0) / 100.0
            bmi = round(weight / (height_m ** 2), 1) if weight and height_m else None
        except (TypeError, ValueError, ZeroDivisionError):
            bmi = None

    return {
        "prakriti": prakriti,
        # Assessed imbalance only. Deliberately NOT falling back to Prakriti: the
        # KB token is `pitta_excess`, and a Pitta constitution is not a Pitta
        # aggravation. Standing in one for the other withheld 31 of 157
        # formulations from every Pitta-built user whether or not anything was
        # currently out of balance. Elsewhere in the engine that substitution is
        # fine — it only reorders a score. Here it decides what someone is allowed
        # to take, so the inference is surfaced as a caution instead (see
        # `assumed_state_notes`).
        "vikriti": vikriti_set,
        "vikriti_assumed": vikriti_set or set(prakriti),
        "ama_level": str(ama_level).lower(),
        "age": user_profile.get("age"),
        "is_pregnant": bool(user_profile.get("pregnancy_or_nursing")
                            or user_profile.get("is_pregnant")),
        "bmi": bmi,
        "symptoms": {str(s).lower() for s in (symptoms or [])},
    }
