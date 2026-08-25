import json
from datetime import datetime, timezone
from pathlib import Path

from engine.condition_vocab import condition_matches_term, term_in_condition

BASE_DIR = Path(__file__).resolve().parent.parent
THERAPIES_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_therapies.json"
PROTOCOLS_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_protocols.json"
CLINICAL_PATH  = BASE_DIR / "data" / "knowledge_base" / "panchakarma_clinical.json"
PROCEDURES_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_procedures.json"

pk_therapies: list[dict] = []
pk_protocols: dict = {}
# The single contraindication source — see its `_meta.why_this_file_exists`.
pk_clinical: dict = {}
# The step-by-step instructions. Previously ~500 words of string literals in this
# file, which meant the how-to for emesis, purgation, enema, nasal instillation and
# bloodletting could not be reviewed as data, handed to a vaidya, translated, or
# checked by a test.
pk_procedures: dict = {}

if THERAPIES_PATH.exists():
    with open(THERAPIES_PATH, "r", encoding="utf-8") as _f:
        pk_therapies = json.load(_f)

if PROTOCOLS_PATH.exists():
    with open(PROTOCOLS_PATH, "r", encoding="utf-8") as _f:
        pk_protocols = json.load(_f)

if CLINICAL_PATH.exists():
    with open(CLINICAL_PATH, "r", encoding="utf-8") as _f:
        pk_clinical = json.load(_f)

if PROCEDURES_PATH.exists():
    with open(PROCEDURES_PATH, "r", encoding="utf-8") as _f:
        pk_procedures = json.load(_f)


# ── Ritu (Season) ─────────────────────────────────────────────────────────────

# The Ritu names as `ritu_shodhana_calendar` keys them, against the names
# `engine/seasonal.py` returns.
_SEASON_TO_RITU = {
    "shishir": "shishira", "vasant": "vasanta", "grishma": "grishma",
    "varsha": "varsha", "sharad": "sharad", "hemant": "hemanta",
}
_VALID_RITUS = set(_SEASON_TO_RITU.values())


def _current_ritu(override: str | None = None) -> str:
    """The current Ayurvedic season, from the one seasonal engine the app has.

    This used to compute its own from `datetime.now().month` on whole-month
    boundaries while `engine/seasonal.py` — which yoga, diet and routine all read —
    uses mid-month transitions. **The two disagreed on a quarter of the year**: the
    first half of every odd month. On 10 March a user's yoga plan said Shishira and
    their Panchakarma plan said Vasanta, on the same day, from the same profile.

    It is not cosmetic here. The Ritu selects the season's Shodhana from
    `ritu_shodhana_calendar`, so on that date a seasonal cleanse chose Vamana
    (Vasanta's Karma) when the rest of the app considered it still winter.

    `override` honours the `current_season` preference, which was declared for
    exactly this and read by nothing — the server's clock is not necessarily in the
    user's hemisphere.
    """
    if override:
        key = str(override).strip().lower()
        if key in _VALID_RITUS:
            return key
        if key in _SEASON_TO_RITU:
            return _SEASON_TO_RITU[key]

    from engine.seasonal import get_current_season
    name = get_current_season().name.strip().lower()
    return _SEASON_TO_RITU.get(name, name if name in _VALID_RITUS else "sharad")


def _get_ritu_context(protocols: dict, override: str | None = None) -> dict:
    ritu = _current_ritu(override)
    calendar = protocols.get("ritu_shodhana_calendar", {})
    return {"ritu": ritu, **calendar.get(ritu, {})}


# ── Shodhana vs Shamana ────────────────────────────────────────────────────────

_FITNESS_TO_BALA = {
    "beginner":     ("manda",    "Manda Bala — low physical reserve; caution with strong Shodhana"),
    "intermediate": ("madhyama", "Madhyama Bala — moderate strength; standard Shodhana protocols"),
    "advanced":     ("uttama",   "Uttama Bala — strong constitution; full Shodhana well-tolerated"),
}

# Canonical Agni vocabulary. agni_type may be stored either dosha-keyed
# (vata/pitta/kapha) or classical-keyed (vishama/tikshna/manda); normalise both.
_BALA_LABEL = {"uttama": "Uttama Bala", "madhyama": "Madhyama Bala", "manda": "Manda Bala"}

_AGNI_CANON = {
    "sama": "sama",
    "vata": "vishama", "vishama": "vishama",
    "pitta": "tikshna", "tikshna": "tikshna",
    "kapha": "manda", "manda": "manda",
}
_AGNI_NAME = {
    "sama": "Sama Agni", "vishama": "Vishama Agni",
    "tikshna": "Tikshna Agni", "manda": "Manda Agni",
}


def _derive_agni(digestion_quality: str | None, dominant_dosha: str | None) -> str:
    """Derive canonical Agni from digestion quality, made dosha-aware so that
    Manda Agni (slow/Kapha — the principal Ama-former) is reachable. Classical
    ref: Charaka Sutrasthana 15 (four Agni states). Returns a canonical key:
    sama | vishama | tikshna | manda."""
    dq = (digestion_quality or "moderate").lower()
    dosha = (dominant_dosha or "").lower()
    if dq in ("strong", "sharp", "intense"):
        return "tikshna"
    if dq in ("weak", "slow", "sluggish", "poor", "irregular"):
        # Irregular weak digestion in a Vata person = Vishama; otherwise the
        # slow/heavy weak digestion of Kapha (and the common Ama-forming case) = Manda.
        return "vishama" if dosha == "vata" else "manda"
    return "sama"


# Atidurbala (extreme depletion) is listed among the Shamana-only criteria in
# `shodhana_eligibility.shamana_only_criteria`. BMI < 17 is the WHO threshold for
# moderate-to-severe thinness and is the only objective depletion signal the
# profile carries.
_ATIDURBALA_BMI = 17.0

# Conditions that forbid Shodhana at any strength, in any setting.
_SHODHANA_ABSOLUTE_CONTRA = {
    "anemia", "rectal_bleeding", "bleeding_disorder", "hemophilia",
    "severe_cardiac", "heart_failure", "active_fever",
}


def _determine_shodhana_or_shamana(user_profile: dict, pk_prefs: dict, protocols: dict) -> dict:
    """
    Classically: Shodhana (purification) only if Bala is adequate, Agni is correctable,
    Ama is cleared, and no absolute contraindications. Ref: CS Sutrasthana 15.

    Returns one of three verdicts, which are NOT interchangeable:

      shodhana        clinically eligible, clinical setting — full classical protocol
      mridu_shodhana  clinically eligible, home setting — the mild home protocol the KB
                      sanctions (`home_panchakarma_protocol`): Triphala/Eranda purgation,
                      Matra Basti, Pratimarsha Nasya
      shamana         clinically INELIGIBLE — no Shodhana at any strength, in any setting

    The clinical criteria are evaluated before the setting is considered. Returning
    early on `setting == "home"` meant a home user's age, Ama, Ojas, Bala, pregnancy
    and contraindications were never examined at all: a 78-year-old with severe Ama
    got mild Virechana with no assessment, because "home" and "too depleted to purify"
    both produced the string "shamana" and nothing downstream could tell them apart.
    """
    setting     = pk_prefs.get("setting", "home")
    experience  = pk_prefs.get("detox_experience", "none")  # none | some | experienced

    # ── Clinical criteria — evaluated for EVERY setting ───────────────────────
    # Two tiers, because the KB draws the line in two places:
    #   blocking     forbids Shodhana at ANY strength → Shamana
    #   restricting  forbids FULL Shodhana but permits the mild protocol the KB
    #                sanctions (Matra Basti, Pratimarsha Nasya, mild Virechana)
    blocking: list[str] = []
    restricting: list[str] = []

    age = int(user_profile.get("age") or 30)
    if age < 7 or age > 70:
        blocking.append(f"Age {age} outside Shodhana range (7–70 years)")
    elif age < 12:
        # `pradhana_karma.vamana.contraindications.absolute` bars children under 12
        # outright, and Virechana bars "very young". 7–11 is inside the eligibility
        # window but outside the window for the forceful Karmas, so it restricts.
        restricting.append(
            f"Age {age} — Vamana is contraindicated under 12 and strong Virechana in the very young. "
            "Mridu (mild) Shodhana only, under Vaidya supervision."
        )

    if user_profile.get("pregnancy_or_nursing", False):
        blocking.append("Pregnancy / nursing — Shodhana contraindicated")

    ama = user_profile.get("ama_indicator", "none")
    # `shamana_only_criteria` bars "High Ama **without prior Deepana-Pachana** —
    # Shodhana drives Ama deeper into Srotas". The qualifier is the whole criterion.
    # It was read as an absolute bar, and the plan the bar produced then scheduled
    # three to seven days of Deepana-Pachana anyway: the correction ran, and the
    # verdict taken *before* the correction still stood. A Kapha patient with high
    # Ama, high Ojas, Uttama Bala, no conditions and three prior courses — the
    # textbook Vamana candidate, since high Ama is the substance Vamana exists to
    # expel — was told he was clinically ineligible for purification.
    #
    # The criterion directly beneath it in the same list, "Manda Agni **without
    # correction**", carries the identical qualifier and is already implemented
    # correctly here as `agni_correction_needed`. High Ama now follows it: a
    # mandatory precondition that the Deepana-Pachana phase discharges, not a bar.
    # It raises that phase's floor and gates progression on the KB's own
    # `signs_ama_cleared`; it does not decide eligibility.
    ama_correction_mandatory = ama in ("high", "severe")

    # Low Ojas restricts to the Brimhana (nourishing) routes rather than blocking
    # outright. `contraindication_matrix.atidurbala` allows exactly Matra Basti,
    # Pratimarsha Nasya and Abhyanga for the depleted — and Matra Basti IS the
    # nourishing Basti, the classical treatment for that state. Barring it would
    # withhold the indicated therapy from the patients it was written for.
    # Expulsive routes (Vamana, Virechana, Raktamokshana) stay barred: those
    # deplete, which is the objection to Shodhana here in the first place.
    ojas = user_profile.get("ojas_level", "medium")
    brimhana_only = ojas == "low"
    if brimhana_only:
        restricting.append(
            "Low Ojas — Brimhana (nourishing) routes only: Matra Basti, Pratimarsha Nasya, "
            "Abhyanga. No expulsive Karma, and Rasayana required before any future Shodhana."
        )

    # Atidurbala — `contraindication_matrix.atidurbala` blocks Vamana, strong
    # Virechana and Niruha Basti outright; only Matra Basti, Pratimarsha Nasya,
    # Abhyanga and Shamana remain.
    bmi = user_profile.get("bmi")
    if isinstance(bmi, (int, float)) and 0 < bmi < _ATIDURBALA_BMI:
        blocking.append(
            f"Atidurbala (BMI {bmi:.1f}) — Shodhana would cause Dhatu Kshaya. "
            "Brimhana required first."
        )

    # Bala (strength) from fitness_level — CS Sutrasthana 15 (Bala Pareeksha).
    # Manda Bala restricts rather than blocks: `contraindication_matrix.atidurbala`
    # withholds Vamana, strong Virechana and Niruha Basti from the depleted while
    # explicitly *allowing* Matra Basti, Pratimarsha Nasya and Abhyanga. Manda Bala
    # is low reserve, not Atidurbala, so treating it as an absolute bar would deny
    # the mild protocol to the users the KB wrote that protocol for.
    fitness = user_profile.get("fitness_level", "intermediate")
    bala_type, bala_note = _FITNESS_TO_BALA.get(fitness, ("madhyama", "Madhyama Bala"))
    if bala_type == "manda" and experience == "none":
        restricting.append(
            "Manda Bala (beginner fitness) without prior PK experience — "
            "full Shodhana carries Ativyapada risk. Mridu (mild) Shodhana only."
        )

    # Precise, case-insensitive matching (was `k in c`, which was case-sensitive —
    # a capitalised "Anemia" silently bypassed this contraindication set).
    flagged = [c for c in (user_profile.get("medical_history") or [])
               if any(term_in_condition(c, k) for k in _SHODHANA_ABSOLUTE_CONTRA)]
    if flagged:
        blocking.append(f"Medical contraindication: {', '.join(flagged)}")

    # Manda Agni is correction-first, not an absolute block:
    # `contraindication_matrix.manda_agni` blocks strong Virechana and early Niruha
    # Basti and requires Dipana (Trikatu / Chitrakadi Vati) for 5–7 days.
    agni = _AGNI_CANON.get(
        str(user_profile.get("agni_type")
            or _derive_agni(user_profile.get("digestion_quality"),
                            user_profile.get("vikriti_dominant") or user_profile.get("dominant_dosha"))).lower(),
        "sama",
    )
    agni_correction_needed = agni == "manda"

    ama_info = protocols.get("shodhana_eligibility", {}).get("ama_correction_first", {})

    # ── Verdict ───────────────────────────────────────────────────────────────
    if blocking:
        return {
            "type": "shamana",
            "shodhana_eligible": False,
            "clinically_ineligible": True,
            "reasons": blocking,
            "blocking_reasons": blocking,
            "restricting_reasons": restricting,
            "brimhana_only": brimhana_only,
            "bala": bala_type,
            "bala_note": bala_note,
            "agni": agni,
            "agni_correction_needed": agni_correction_needed,
            # A blocked patient still needs Ama cleared — it is the reason many of
            # them are blocked — so the correction herbs travel with the verdict.
            "ama_correction_needed": ama != "none",
            "ama_correction_mandatory": ama_correction_mandatory,
            "ama_correction_herbs": ama_info.get("herbs", []),
            "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
            "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
        }

    # Every grade of Ama needs correcting before Shodhana; the grades differ in how
    # long it takes and whether the course may start without it, not in whether the
    # correction happens. Restricting this to mild/moderate is what left high Ama
    # with a phase floor of zero on the one path where it mattered most.
    needs_ama = ama != "none"

    if setting == "home" or restricting:
        reasons = list(restricting)
        if setting == "home":
            reasons.append(
                "Home setting — full Shodhana (Vamana / Niruha Basti) requires Vaidya supervision. "
                "Mridu (mild) Shodhana applied per the classical home protocol."
            )
        if ama_correction_mandatory:
            reasons.append(
                f"{ama.title()} Ama — the mild cleanse proceeds only once Deepana-Pachana has "
                "cleared it. Do not begin Snehana until the signs of cleared Ama have appeared."
            )
        elif needs_ama or agni_correction_needed:
            reasons.append("Deepana-Pachana scheduled before the mild cleanse.")
        return {
            "type": "mridu_shodhana",
            "shodhana_eligible": False,   # not FULL Shodhana
            "clinically_ineligible": False,
            "reasons": reasons,
            "blocking_reasons": [],
            "restricting_reasons": restricting,
            "brimhana_only": brimhana_only,
            "bala": bala_type,
            "bala_note": bala_note,
            "agni": agni,
            "agni_correction_needed": agni_correction_needed,
            "ama_correction_needed": needs_ama,
            "ama_correction_mandatory": ama_correction_mandatory,
            "ama_correction_herbs": ama_info.get("herbs", []) if needs_ama else [],
            "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
            "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
        }

    shodhana_reasons = ["Patient meets all Shodhana eligibility criteria (CS Sutrasthana 15)"]
    if ama_correction_mandatory:
        # Stated on the verdict, not only in the phase, because this is the one
        # eligibility criterion the patient can still fail *after* the plan is
        # issued — the days are a guide, the signs are the gate.
        shodhana_reasons.append(
            f"{ama.title()} Ama — Shodhana proceeds only once Deepana-Pachana has cleared it. "
            "Do not begin Snehana until the signs of cleared Ama have appeared, however many "
            "days that takes."
        )
    if experience == "experienced":
        shodhana_reasons.append("Prior PK experience (3+ courses) — full classical protocol applicable")
    elif experience == "some":
        shodhana_reasons.append("Some PK experience — standard protocol with careful monitoring")

    return {
        "type": "shodhana",
        "shodhana_eligible": True,
        "clinically_ineligible": False,
        "reasons": shodhana_reasons,
        "blocking_reasons": [],
        "restricting_reasons": [],
        "brimhana_only": False,
        "bala": bala_type,
        "bala_note": bala_note,
        "agni": agni,
        "agni_correction_needed": agni_correction_needed,
        "ama_correction_needed": needs_ama,
        "ama_correction_mandatory": ama_correction_mandatory,
        "ama_correction_herbs": ama_info.get("herbs", []) if needs_ama else [],
        "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
        "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
    }


# Per-Karma contraindications now come from `panchakarma_clinical.json`, which is
# the single source. There used to be two — the prose absolutes in
# `panchakarma_protocols.json` and a hardcoded dict here — and they disagreed:
# the dict omitted Manda Agni, Rajayakshma and active diarrhoea for Virechana,
# omitted children under 12, severe hypertension and Atidurbala for Vamana, omitted
# first-trimester pregnancy and extreme emaciation for Basti, and promoted
# haemorrhoids to hard when the KB marks it relative — silently substituting Basti,
# the worse choice for haemorrhoids, for a patient who only needed a milder dose.
# Neither could be corrected without the other drifting.
_KARMA_FALLBACK: dict[str, tuple[str, str]] = {
    "vamana":        ("nasya",     "Vamana contraindicated — Pratimarsha Nasya + mild Virechana substituted"),
    "virechana":     ("basti",     "Virechana contraindicated — Basti (enema route) substituted to avoid GI stress"),
    "basti":         ("nasya",     "Basti contraindicated — Nasya + Shamana substituted"),
    "nasya":         ("nasya",     ""),
    # The reason names the route, not the drug: the Aushadha for the substituted
    # Karma is chosen separately from the compendium, and naming one here was a
    # second source that could contradict it.
    "raktamokshana": ("virechana", "Raktamokshana contraindicated — Virechana substituted to clear Rakta by the Pitta route"),
}


def _karma_contraindications(karma_key: str) -> dict:
    """hard/soft token→mechanism maps for one Pradhana Karma, plus its fallback."""
    entry = pk_clinical.get("pradhana_karma", {}).get(karma_key, {})
    fallback, reason = _KARMA_FALLBACK.get(karma_key, ("nasya", "Therapy substituted due to contraindication"))
    return {
        "hard": entry.get("hard", {}),
        "soft": entry.get("soft", {}),
        "fallback": fallback,
        "fallback_reason": reason,
    }


def _therapy_contraindications(therapy_id: str) -> dict:
    """hard/soft maps for one therapy row, resolving `inherits` and `inherits_karma`.

    Fifteen of the twenty-three therapy rows carried no contraindications at all —
    Swedana, Abhyanga, Shirodhara and Udvartana among them — and the eight that did
    were never read by any code. Inheritance keeps the clinic and home variants of a
    procedure from drifting apart, which is how `virechana_home` came to carry none
    while `virechana_clinic` carried two.
    """
    entry = pk_clinical.get("therapies", {}).get(therapy_id) or {}
    hard: dict = {}
    soft: dict = {}

    if parent := entry.get("inherits"):
        inherited = _therapy_contraindications(parent)
        hard.update(inherited["hard"])
        soft.update(inherited["soft"])
    if karma := entry.get("inherits_karma"):
        inherited = _karma_contraindications(karma)
        hard.update(inherited["hard"])
        soft.update(inherited["soft"])

    hard.update(entry.get("hard") or {})
    soft.update(entry.get("soft") or {})

    # An override to null lifts an inherited bar for a genuinely different procedure:
    # Pratimarsha Nasya is two drops of plain oil and is the one nasal route the
    # pregnancy matrix lists as ALLOWED, so it must not inherit Navana Nasya's bar.
    for term, value in (entry.get("overrides") or {}).items():
        if value is None:
            hard.pop(term, None)
            soft.pop(term, None)

    return {"hard": hard, "soft": soft}


# The Brimhana routes — the only Pradhana Karma a depleted patient may receive.
# `contraindication_matrix.atidurbala` names exactly these as still allowed when
# Vamana, strong Virechana and Niruha Basti are withheld.
_BRIMHANA_KARMAS = {"basti_matra", "nasya"}

_BRIMHANA_SUBSTITUTE = {
    "basti":         ("basti_matra", "Matra Basti (nourishing oil enema) replaces Niruha — Niruha is Lekhana and depletes further"),
    "vamana":        ("nasya",       "Vamana withheld — emesis depletes Ojas. Pratimarsha Nasya substituted"),
    "virechana":     ("nasya",       "Virechana withheld — purgation depletes Ojas. Pratimarsha Nasya substituted"),
    "raktamokshana": ("nasya",       "Raktamokshana withheld — blood loss depletes Ojas. Pratimarsha Nasya substituted"),
}


def _restrict_to_brimhana(pradhana: dict, eligibility: dict) -> tuple[dict, list[str]]:
    """Force the Karma onto a Brimhana (nourishing) route when Ojas is depleted.

    Low Ojas is not a reason to withhold Panchakarma entirely — Matra Basti is the
    classical treatment for exactly that state — but it is a reason to withhold
    every route that expels. Without this, a low-Ojas Pitta patient was routed to
    Virechana by the dosha mapping and the depletion finding never reached the
    therapy: the eligibility block said "Brimhana required" and the schedule said
    "castor oil".
    """
    if not eligibility.get("brimhana_only"):
        return pradhana, []
    primary = pradhana.get("primary")
    if primary in _BRIMHANA_KARMAS or primary is None:
        return pradhana, []
    fallback, why = _BRIMHANA_SUBSTITUTE.get(primary, ("nasya", "Expulsive Karma withheld — Ojas depleted"))
    return (
        {
            **pradhana,
            "primary": fallback,
            "reason": f"⚠ {primary.title()} withheld (low Ojas). {why}.",
            "brimhana_substitution": True,
            "original_karma": primary,
        },
        [f"BRIMHANA RESTRICTION: {primary} → {fallback} (low Ojas — expulsive Karma depletes further)"],
    )


def _match_contraindications(medical_history: list[str], terms: dict) -> list[tuple[str, str]]:
    """(patient condition, stated mechanism) for every term that matches.

    The mechanism travels with the match because "CAUTION: diabetes — modify dose
    per Vaidya guidance" tells a patient nothing about what to modify or why. Every
    term in `panchakarma_clinical.json` carries the reason it is there.
    """
    hits: list[tuple[str, str]] = []
    for condition in medical_history:
        for term, mechanism in terms.items():
            # Synonym-aware: the safety gate has to ask the vocabulary whether two
            # names are the same disease, not compare the strings. See
            # `condition_matches_term` — three contraindications, one of them a hard
            # bar on bloodletting, had never fired for exactly this reason.
            if condition_matches_term(condition, term):
                hits.append((condition, mechanism))
                break
    return hits


# ── LLM triage for unrecognised diagnoses ─────────────────────────────────────
# `services/condition_triage.py` explains why this layer exists and why the
# enricher could not do the job. Here is the contract it is held to:
#
#   RESTRICT ONLY.  Triage findings are merged UNDER the authored KB entries, and
#     the merge only ever adds tokens. There is no representation for removing a
#     contraindication, so no answer from a language model can lift a bar a vaidya
#     wrote — the worst it can do is add one that was not needed.
#   FAIL CLOSED.  A condition the KB does not recognise and triage could not assess
#     withholds Shodhana. Before this existed, that same case proceeded to full
#     Vamana: fifteen of fifteen dangerous unmapped diagnoses — chemotherapy, active
#     tuberculosis, DVT, cardiac stent, gestational diabetes — received the
#     byte-identical plan a healthy forty-year-old gets.

_TRIAGE_KARMA_KEYS = ("vamana", "virechana", "basti", "nasya", "raktamokshana")


def _triage_karma_terms(condition_triage: dict | None) -> dict[str, dict[str, dict]]:
    """Triage findings reshaped into the hard/soft token→mechanism maps the gate reads.

    The token is the patient's own condition string, which is what makes this work
    without a new matcher: `_match_contraindications` already matches a condition
    against a token, and here they are the same word.
    """
    out: dict[str, dict[str, dict]] = {k: {"hard": {}, "soft": {}} for k in _TRIAGE_KARMA_KEYS}
    for condition, finding in (condition_triage or {}).items():
        if not isinstance(finding, dict) or finding.get("status") != "ok":
            continue
        for severity in ("hard", "soft"):
            for karma, mechanism in (finding.get(severity) or {}).items():
                if karma in out:
                    out[karma][severity][condition] = mechanism
    return out


def _triage_eligibility_findings(unmapped: list[str], condition_triage: dict | None) -> dict:
    """What the triage says about Shodhana as a whole, per unrecognised condition."""
    blocking: list[str] = []
    restricting: list[str] = []
    assessed: list[dict] = []

    for condition in unmapped:
        finding = (condition_triage or {}).get(condition)
        display = condition.replace("_", " ")

        if isinstance(finding, dict) and finding.get("status") == "not_a_diagnosis":
            # A symptom, not a diagnosis. It is not an eligibility finding and must
            # not withhold anything — the plan handles symptoms elsewhere — but it
            # is still recorded, because the patient wrote it down, and a plan that
            # neither uses an answer nor mentions it reads as though it never asked.
            assessed.append({"condition": condition, "status": "not_a_diagnosis",
                             "outcome": "not_a_diagnosis",
                             "note": finding.get("reason") or "",
                             "reviewed": False, "source": "llm_triage"})
            continue

        if not isinstance(finding, dict) or finding.get("status") != "ok":
            reason = (finding or {}).get("reason") if isinstance(finding, dict) else None
            blocking.append(
                f"'{display}' is not in this engine's disease vocabulary and could not be "
                f"assessed{f' — {reason}' if reason else ''}. Shodhana is withheld rather than "
                "performed on a diagnosis nothing has checked: every contraindication gate "
                "matches on recognised conditions, so an unrecognised one passes them all by "
                "default rather than clearing them. A Vaidya can assess this in person."
            )
            assessed.append({"condition": condition,
                             "status": (finding or {}).get("status", "unavailable"),
                             "outcome": "shodhana_withheld"})
            continue

        verdict = finding.get("shodhana")
        if verdict == "contraindicated":
            mech = "; ".join((finding.get("hard") or {}).values()) or finding.get("note") or ""
            blocking.append(
                f"'{display}' — assessed as contraindicating Shodhana"
                f"{f': {mech}' if mech else ''}. Assessment is AI-generated and unreviewed; "
                "confirm with a Vaidya."
            )
        elif verdict == "mridu_only":
            restricting.append(
                f"'{display}' — assessed as tolerating only Mridu (mild) Shodhana. "
                "Assessment is AI-generated and unreviewed; confirm with a Vaidya."
            )
        assessed.append({
            "condition": condition,
            "status": "ok",
            "outcome": verdict,
            "classical_analogue": finding.get("classical_analogue"),
            "dosha": finding.get("dosha"),
            "srotas": finding.get("srotas"),
            "monitoring": finding.get("monitoring"),
            "confidence": finding.get("confidence"),
            "karma_restrictions": {
                **{k: {"severity": "hard", "mechanism": m} for k, m in (finding.get("hard") or {}).items()},
                **{k: {"severity": "soft", "mechanism": m} for k, m in (finding.get("soft") or {}).items()},
            },
            "reviewed": False,
            "source": "llm_triage",
        })

    return {"blocking": blocking, "restricting": restricting, "assessed": assessed}


def _validate_karma_safety(pradhana: dict, medical_history: list[str],
                           triage_terms: dict | None = None) -> dict:
    """
    Post-selection safety gate: checks if chosen Pradhana Karma is contraindicated
    by the user's medical conditions. Hard contraindications trigger substitution.
    Ref: CS Kalpasthana 12, Siddhisthana 1.

    `triage_terms` carries findings for diagnoses the KB does not recognise. They
    are merged UNDER the authored entries — additively, and losing every collision —
    so the LLM layer can only ever narrow what this gate permits.
    """
    def contraindications(key: str) -> dict:
        kb = _karma_contraindications(key)
        extra = (triage_terms or {}).get(key) or {}
        return {
            **kb,
            "hard": {**(extra.get("hard") or {}), **kb["hard"]},
            "soft": {**(extra.get("soft") or {}), **kb["soft"]},
        }

    primary = pradhana.get("primary", "virechana")
    karma_key = "basti" if primary == "basti_matra" else primary
    contra = contraindications(karma_key)

    hard_hits = _match_contraindications(medical_history, contra["hard"])
    soft_hits = _match_contraindications(medical_history, contra["soft"])

    warnings: list[str] = []

    if hard_hits:
        old_primary = pradhana["primary"]
        flagged = [c for c, _ in hard_hits]

        # The fallback has to be checked too. Ulcerative colitis is a hard
        # contraindication for BOTH Virechana and Basti, and the substitution was
        # a single unchecked hop: the engine withdrew the purgative and handed the
        # same patient an enema, reporting it as a safety substitution. Walk the
        # chain until something is actually safe, or admit that nothing is.
        chosen, chain = None, [contra["fallback"]]
        for candidate in (contra["fallback"], "nasya", "basti_matra"):
            key = "basti" if candidate == "basti_matra" else candidate
            if candidate == old_primary:
                continue
            if not _match_contraindications(
                medical_history, contraindications(key)["hard"]
            ):
                chosen = candidate
                break
            if candidate not in chain:
                chain.append(candidate)

        if chosen is None:
            # No Karma is safe for this patient. Returning primary=None routes the
            # plan to the Shamana arm rather than picking the least-bad expulsion.
            pradhana = {
                **pradhana,
                "primary": None,
                "reason": (
                    f"⚠ No Pradhana Karma is safe with {', '.join(flagged)}. "
                    f"Every route ({', '.join(chain)}) is contraindicated. Shamana only."
                ),
                "safety_substitution": True,
                "original_karma": old_primary,
                "contraindication_mechanisms": [
                    {"condition": c, "mechanism": m} for c, m in hard_hits
                ],
            }
            warnings.append(
                f"NO SAFE KARMA: every Pradhana route is contraindicated by "
                f"{', '.join(flagged)} — plan falls back to Shamana"
            )
        else:
            fallback_reason = (
                contraindications(
                    "basti" if old_primary == "basti_matra" else old_primary
                )["fallback_reason"]
                if chosen == contra["fallback"]
                else f"{chosen.replace('_', ' ').title()} substituted — the usual fallback is contraindicated too"
            ) or "Therapy substituted due to contraindication"
            pradhana = {
                **pradhana,
                "primary": chosen,
                "reason": (
                    f"⚠ {old_primary.title()} CONTRAINDICATED: {', '.join(flagged)}. "
                    f"{fallback_reason}."
                ),
                "safety_substitution": True,
                "original_karma": old_primary,
                "contraindication_mechanisms": [
                    {"condition": c, "mechanism": m} for c, m in hard_hits
                ],
            }
            warnings.append(
                f"SAFETY SUBSTITUTION: {old_primary} → {chosen} "
                f"(contraindicated by: {', '.join(flagged)})"
            )
        warnings += [f"{c}: {m}" for c, m in hard_hits if m]

    if soft_hits:
        warnings += [
            f"CAUTION — {c}: {m}" if m
            else f"CAUTION: {c} — modify dose/protocol per Vaidya guidance"
            for c, m in soft_hits
        ]

    return pradhana, warnings


# ── Declared-capability gate ───────────────────────────────────────────────────
# Every Pradhana row in `panchakarma_therapies.json` states what the patient has to
# be able to supply: `diet_strictness` and `herb_requirement`.
# `filter_and_score_therapies` reads both fields — but it is only ever called with
# `"purvakarma"` and `"paschat"`, so all nine `pradhana` rows sit outside the only
# gate that reads them. Both preferences were therefore honoured on the supporting
# therapies and ignored on the cleanse: a patient who answered "lifestyle changes
# only" had Udvartana and the Kitchari mono-diet withheld from the rotating pool and
# was then handed a seven-stage Samsarjana Krama opening on Peya — a 1:14 rice-water
# fast — with no part of the plan acknowledging the answer.
#
# Which rows belong to which Karma. `basti_matra` is the home adaptation of Basti
# and shares its row; the mapping is here rather than derived from the id prefix
# because `basti_niruha` and `basti_anuvasana` are two halves of one course while
# `basti_home` is a different therapy that happens to share the stem.
_KARMA_ROWS: dict[str, tuple[str, ...]] = {
    "vamana":        ("vamana",),
    "virechana":     ("virechana_clinic", "virechana_home"),
    "basti":         ("basti_niruha", "basti_anuvasana"),
    "basti_matra":   ("basti_home",),
    "nasya":         ("nasya_clinic", "nasya_home"),
    "raktamokshana": ("raktamokshana",),
}

_DIET_RANK = {"lifestyle_only": 0, "partial": 1, "strict": 2}


def _capability_shortfall(row: dict, pk_prefs: dict) -> str:
    """Why this patient's own declared capabilities cannot support this row, or "".

    Clinician-administered rows are exempt from both checks: the clinic serves the
    diet and stocks the pharmacy, so neither answer describes anything the patient
    has to do. `filter_and_score_therapies` already draws this exact line for the
    time budget — "Clinic-only rows are exempt; self-care is not, wherever the
    patient happens to be" — and the two gates would contradict each other if this
    one drew it anywhere else.
    """
    if "home" not in (row.get("setting_required") or []):
        return ""

    diet_ab = pk_prefs.get("diet_adherence_ability", "partial")
    # Only `lifestyle_only` gates here, and the asymmetry with the pool filter (which
    # also excludes `strict` from a `partial` answer) is deliberate. `partial` is a
    # statement about difficulty; `lifestyle_only` is a statement about refusal, and
    # a Shodhana whose Samsarjana Krama will not be followed is the specific thing
    # that causes post-purification complications. Dropping a supporting therapy over
    # a difficulty rating costs the patient a massage; dropping the Karma over one
    # would cost them the treatment, and a preference must not do that.
    if diet_ab == "lifestyle_only" and _DIET_RANK.get(row.get("diet_strictness"), 0) > 0:
        return (
            f"it needs a {row.get('diet_strictness')} therapeutic diet — the Samsarjana Krama "
            "re-entry is part of the treatment, not an optional extra, and you have said you "
            "can make lifestyle changes only"
        )

    if pk_prefs.get("access_to_ayurvedic_herbs") == "no" \
            and row.get("herb_requirement") == "specific_ayurvedic":
        return "it needs specific Ayurvedic formulations you have said you cannot obtain"

    return ""


def _validate_karma_capability(pradhana: dict, karma_setting: str, pk_prefs: dict,
                               therapies: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Withdraw a Karma the patient has said they cannot carry out, and say so.

    Runs AFTER `_validate_karma_safety`, never before: a clinical contraindication
    and a declared preference are not the same kind of finding, and a substitution
    made for a preference must not be able to reinstate a route safety withdrew.

    `therapies` is the list the rest of the plan was built from. It matters that it
    is passed rather than read from the module: in production the route hands the
    engine `kb_cache.panchakarma_protocols` from Mongo, and a gate reading the
    bundled file instead would be deciding from data the schedule never saw.
    """
    primary = pradhana.get("primary")
    if not primary:
        return pradhana, []

    by_id = {t["id"]: t for t in (therapies if therapies is not None else pk_therapies)}

    def shortfall(karma: str) -> str:
        rows = [by_id[r] for r in _KARMA_ROWS.get(karma, ()) if r in by_id]
        rows = [r for r in rows
                if {karma_setting, "both"} & set(r.get("setting_required") or [])]
        if not rows:
            # No row delivers this Karma where the patient is. Silence here would
            # have let the substitution chain answer a home patient's withdrawn
            # Virechana with clinical Niruha Basti, which has no home row at all.
            return f"there is no {karma.replace('_', ' ')} route for a {karma_setting} setting"
        # A Karma survives if ANY of its rows does — Basti is one course delivered
        # by two rows, and Virechana has a clinic form and a home form.
        reasons = [_capability_shortfall(r, pk_prefs) for r in rows]
        return "" if any(not r for r in reasons) else reasons[0]

    why = shortfall(primary)
    if not why:
        return pradhana, []

    original = primary
    chosen = None
    for candidate in (_KARMA_FALLBACK.get(primary, ("nasya", ""))[0], "nasya", "basti_matra"):
        # The fallback table names the classical route, not the setting's form of
        # it. `_select_pradhana_karma` applies the home adaptations on the way in
        # and the substitution chain has to apply the same ones, or a preference
        # substitution quietly promotes a home patient to a clinical procedure.
        if karma_setting == "home":
            candidate = {"vamana": "nasya", "basti": "basti_matra"}.get(candidate, candidate)
        if candidate == original:
            continue
        if not shortfall(candidate):
            chosen = candidate
            break

    if chosen is None:
        return {
            **pradhana,
            "primary": None,
            "reason": (
                f"No Pradhana Karma is possible with what you have told us you can do: "
                f"{why}. Shodhana is not withheld for a clinical reason — this plan takes the "
                "Shamana route instead."
            ),
            "capability_substitution": True,
            "original_karma": original,
        }, [
            f"NO KARMA AVAILABLE: every Pradhana route needs something you have said you "
            f"cannot do — {why}. The plan falls back to Shamana."
        ]

    return {
        **pradhana,
        "primary": chosen,
        "reason": (
            f"{original.replace('_', ' ').title()} withdrawn — {why}. "
            f"{chosen.replace('_', ' ').title()} substituted; it asks less of you and treats the "
            "same imbalance by a gentler route."
        ),
        "capability_substitution": True,
        "original_karma": original,
    }, [
        f"PREFERENCE SUBSTITUTION: {original} → {chosen} — {why}"
    ]


# ── Pradhana Karma Selection ───────────────────────────────────────────────────

def _select_pradhana_karma(
    vikriti_dom: str,
    vikriti_sec: str | None,
    setting: str,
    protocols: dict,
) -> dict:
    """
    Classical mapping: Vata → Basti, Pitta → Virechana, Kapha → Vamana.
    Ref: CS Sutrasthana 15, AH Sutrasthana 14.
    """
    mapping = protocols.get("dosha_pradhana_karma_mapping", {})

    # Bidoshic: try combined key
    selected: dict = {}
    if vikriti_sec:
        for key in (f"{vikriti_dom}_{vikriti_sec}", f"{vikriti_sec}_{vikriti_dom}"):
            if key in mapping:
                selected = mapping[key]
                break
    if not selected:
        selected = mapping.get(vikriti_dom, mapping.get("sama", {}))

    primary = selected.get("primary", "virechana")
    secondary = selected.get("secondary")
    reason = selected.get("reason", "")

    # Home adaptations
    home_note = ""
    if setting == "home":
        if primary == "vamana":
            primary = "nasya"
            home_note = " [Home adaptation: Vamana requires clinical Vaidya; substituted with Pratimarsha Nasya + mild Triphala Virechana]"
        elif primary == "basti":
            primary = "basti_matra"
            home_note = " [Home adaptation: Matra Basti (50–80 ml warm medicated oil, retained overnight) instead of Niruha Basti]"

    protocol_key = "basti" if primary == "basti_matra" else primary
    pradhana_data = protocols.get("pradhana_karma", {}).get(protocol_key, {})

    return {
        "primary": primary,
        "secondary": secondary,
        "reason": reason + home_note,
        "sequence": selected.get("sequence", ""),
        "clinical_note": selected.get("clinical_note", ""),
        "protocol": pradhana_data,
    }


# ── Purvakarma Duration ────────────────────────────────────────────────────────

def _purvakarma_days(vikriti_dom: str, total_days: int, protocols: dict) -> int:
    """Classical Snehana duration by Prakriti/Vikriti. Vata=7, Pitta=5, Kapha=3."""
    dur_map = (
        protocols.get("purvakarma_protocols", {})
        .get("snehana", {})
        .get("types", {})
        .get("internal", {})
        .get("duration_by_prakriti", {})
    )
    classical = dur_map.get(vikriti_dom, 5)
    # Never consume more than 40% of total days on Purvakarma
    return min(classical, max(2, int(total_days * 0.40)))


# ── Basti Subtype ─────────────────────────────────────────────────────────────

def _basti_subtype(setting: str, available_days: int) -> dict:
    """Select Yoga / Kala / Karma / Matra Basti based on setting and days available."""
    if setting == "home":
        # Dose and timing come from the KB's own `matra_basti` subtype, which carries
        # both. They were restated here as literals, naming two oils while the actual
        # oil is chosen from the compendium — a third description of the same thing.
        kb = (pk_protocols.get("pradhana_karma", {}).get("basti", {})
              .get("subtypes", {}).get("matra_basti", {}))
        return {
            "subtype": "matra_basti",
            "name": "Matra Basti (Home Oil Enema)",
            "days": min(8, available_days),
            "dose": kb.get("dose", "50–80 ml"),
            "timing": kb.get("timing", "Night, after light dinner"),
            "retention": kb.get("retention", "Retain overnight if possible"),
            "note": "Safest home Basti. Oil is absorbed — no forced expulsion needed.",
        }
    if available_days >= 16:
        return {"subtype": "kala_basti",  "name": "Kala Basti (16-Basti Schedule)",
                "days": 16, "note": "6 Niruha + 10 Anuvasana"}
    if available_days >= 8:
        return {"subtype": "yoga_basti",  "name": "Yoga Basti (8-Basti Schedule)",
                "days": 8,  "note": "3 Niruha + 5 Anuvasana — standard course"}
    return     {"subtype": "yoga_basti",  "name": "Yoga Basti (abbreviated)",
                "days": min(8, available_days), "note": "Abbreviated course"}


# ── Aushadha Selection ────────────────────────────────────────────────────────

def _already_taking(components: list[str], existing: list[str]) -> list[dict]:
    """Constituents the patient is already taking under another name.

    `current_ayurvedic_medicines` is declared in the schema as "Currently taken
    Ayurvedic medicines to ensure therapy safety" and was collected by no UI and
    read by no code. The interaction gate added in the previous change checks
    ALLOPATHIC medication only, so a patient already on Ashwagandha who is
    prescribed the Manovaha adjuvant — Brahmi + Ashwagandha + Jatamansi +
    Shankhpushpi — takes Ashwagandha twice and nothing notices.

    Doubling is flagged rather than withheld: the right response is usually to stop
    the one they are self-administering, not to drop the constituent from a
    prescribed formulation, and that is a decision for the patient and their Vaidya.
    """
    herbs = pk_clinical.get("herbs", {})
    hits = []
    for key in components:
        display = herbs.get(key, {}).get("display", key.replace("_", " ").title())
        stem = display.split(" (")[0].lower()
        for taken in existing:
            t = str(taken).strip().lower()
            if not t:
                continue
            # Match either way: "ashwagandha" against "Ashwagandha Churna", and
            # "Ashwagandha Churna 5g" against "ashwagandha".
            if stem in t or t in stem or key in t.replace(" ", "_"):
                hits.append({
                    "herb": display,
                    "already_taking": str(taken),
                    "note": (
                        f"You are already taking {taken}. This plan prescribes "
                        f"{display} as part of a formulation, so following both would "
                        "double the dose. Confirm with a Vaidya which to keep."
                    ),
                })
                break
    return hits


def _gate_formulation(components: list[str], conditions: list[str],
                      medications: list[str], existing_ayurvedic: list[str] | None = None) -> dict:
    """Withhold the contraindicated constituents of a compound formulation.

    The Sahayoga Dravya adjuvants and the Rasayana passed no contraindication gate
    at all: they were selected on an indication match and handed over. Shilajit went
    to patients with chronic kidney disease, Guggulu to patients on thyroxine, and
    Sarpagandha — a reserpine source, and a documented cause of drug-induced
    depression — to anyone whose recorded conditions included hypertension. The
    formulation's own `caution` field read "avoid in hypotension" and nothing read it.

    The unit is the herb, not the formulation. A contraindication against one
    constituent is a reason to withhold that constituent, not the four-herb
    preparation around it: dropping the whole thing would deny a psoriasis patient
    their Kushtha Chikitsa because one component interacts with their warfarin.
    A formulation only falls entirely when nothing safe is left in it.
    """
    herbs = pk_clinical.get("herbs", {})
    kept, withheld, cautions = [], [], []

    for key in components:
        entry = herbs.get(key)
        if not entry:
            kept.append(key)
            continue
        display = entry.get("display", key.replace("_", " ").title())
        hard = _match_contraindications(conditions, entry.get("hard") or {})
        if hard:
            withheld.append({
                "herb": display,
                "reasons": [{"condition": c, "mechanism": m} for c, m in hard],
            })
            continue
        soft = _match_contraindications(conditions, entry.get("soft") or {})
        if soft:
            cautions.append({
                "herb": display,
                "notes": [{"condition": c, "mechanism": m} for c, m in soft],
            })
        kept.append(key)

    # Drug-herb interactions, via the checker the chat agent and the interaction
    # tool already use — one interaction KB, not a second one grown here.
    #
    # A `major` interaction withholds the herb rather than warning beside it. The
    # KB's own recommendation for Haridra on Warfarin reads "AVOID turmeric/curcumin
    # supplements", and printing AVOID next to a formulation the plan still tells the
    # patient to take is the same defect as an ungated contraindication wearing a
    # warning label. Moderate and minor stay as cautions.
    interactions, interaction_withheld = [], []
    if medications and kept:
        try:
            from engine.condition_filter import ConditionFilter
            checker = ConditionFilter()
            # Pass the herb table's KEY, not its display name. The interaction KB
            # keys are compound ("turmeric_haridra_high_dose") and the checker
            # matches by substring either way round, so the bare token "haridra"
            # matches while "Haridra (Turmeric)" — the display string — matches
            # nothing. A gloss in parentheses silently disabled the whole check.
            found = checker.check_drug_herb_interactions(medications, list(kept))
            interactions = [
                {**hit, "herb": herbs.get(hit.get("herb"), {}).get("display", hit.get("herb"))}
                for hit in (found.get("interactions") or found.get("warnings") or [])
            ]
            by_key = {herbs.get(k, {}).get("display", k): k for k in kept}
        except Exception:  # noqa: BLE001 — a checker failure must not drop the plan
            interactions = []

        for hit in interactions:
            # "high" is what the checker's category path emits for blood thinners;
            # "major" is what the per-medication KB emits. Both mean withhold.
            if str(hit.get("severity", "")).lower() not in ("major", "severe", "high", "contraindicated"):
                continue
            key = by_key.get(hit.get("herb"))
            if key and key in kept:
                kept.remove(key)
                interaction_withheld.append({
                    "herb": hit.get("herb"),
                    "reasons": [{
                        "condition": f"interaction with {hit.get('medication_category', 'your medication')}",
                        "mechanism": hit.get("effect") or hit.get("recommendation") or "",
                    }],
                })
        withheld += interaction_withheld

    return {
        "kept": kept,
        "withheld": withheld,
        "cautions": cautions,
        "interactions": interactions,
        "duplicates": _already_taking(kept, existing_ayurvedic or []),
    }


def _matches_dosha(entry: dict, dosha: str) -> bool:
    """`dosha` on a compendium entry is one of vata / pitta / kapha / pitta_vata /
    pitta_rakta / all — a compound string, not a list."""
    field = entry.get("dosha", "")
    return field == "all" or field == dosha or dosha in field.split("_")


def _select_from_compendium(
    entries: list[dict], conditions: list[str], dosha: str, gender: str | None = None
) -> dict:
    """Pick the entry whose *indication* fits the patient, falling back to dosha.

    Selection used to be `next(e for e in entries if dosha matches)` — the first
    hit and nothing else. Six of the eleven external oils are Vata oils, so only
    Tila Taila, the first of them, could ever be chosen; Ksheerabala, Mahanarayana,
    Bala, Dashamoola and Dhanvantara were authored, cited and unreachable. Across
    5,400 generated plans covering every dosha, setting, goal, Koshtha and
    condition, 19 of 32 compendium entries were never selected once.

    The indication for each was already written down — in the `use` prose, which no
    matcher reads. `indications` now carries the same knowledge as tokens.

    Order: a condition-specific entry that also suits the Dosha, then any
    condition-specific entry, then the Dosha default, then the first entry. The
    Dosha still outranks a bare indication match, because an oil that aggravates
    the vitiated Dosha does not become correct through treating the complaint.
    """
    if not entries:
        return {}

    def indicated(e):
        return any(
            term_in_condition(c, t) for c in conditions for t in (e.get("indications") or [])
        ) and (e.get("gender") in (None, gender) if gender else e.get("gender") is None)

    dosha_ok = [e for e in entries if _matches_dosha(e, dosha)]
    return next(
        # 1. Suits the Dosha AND treats the condition — the answer when there is one.
        (e for e in dosha_ok if indicated(e)),
        next(
            # 2. Suits the Dosha. Ranked above a wrong-Dosha entry that happens to
            #    name the condition: Sarshapa Taila is indicated for obesity and is
            #    a Kapha oil, and giving it to an obese Pitta patient treats the
            #    complaint by aggravating the Dosha. Vikriti is what a Panchakarma
            #    plan is built on; the complaint is the reason for building it.
            iter(dosha_ok),
            next((e for e in entries if indicated(e)), entries[0]),
        ),
    )


def _select_aushadha(
    vikriti_dom: str,
    medical_history: list[str],
    pradhana_karma: str,
    setting: str,
    protocols: dict,
    koshtha: str = "sama",
    gender: str | None = None,
    bala: str = "madhyama",
    medications: list[str] | None = None,
    pregnancy: bool = False,
    existing_ayurvedic: list[str] | None = None,
) -> dict:
    medications = medications or []
    existing_ayurvedic = existing_ayurvedic or []
    # Pregnancy is a profile flag, not a `medical_history` entry, and the herb table
    # keys on conditions — so without this the pregnancy bars on Guggulu, Vasaka,
    # Manjistha and Shatapushpa could never fire. `filter_and_score_therapies` makes
    # the same injection for the same reason.
    if pregnancy:
        medical_history = list(medical_history) + ["pregnancy"]
    aus = protocols.get("aushadha_compendium", {})
    result: dict = {}

    result["abhyanga_oil"] = _select_from_compendium(
        aus.get("oils_external", []), medical_history, vikriti_dom)
    result["internal_ghrita"] = _select_from_compendium(
        aus.get("ghrita_internal", []), medical_history, vikriti_dom)

    # Pradhana-specific Aushadha
    if pradhana_karma == "virechana":
        drugs = aus.get("virechana_drugs", [])
        # Koshtha (bowel tendency) is the primary determinant of Virechana drug strength
        # CS Kalpa Sthana 1: Krura Koshtha needs Tikshna Virechaka; Mridu Koshtha needs Mridu only
        _KOSHTHA_NOTES = {
            "krura": "Krura Koshtha — hard, infrequent bowels; strong Virechaka (Trivrit/Eranda) needed to achieve adequate Vegas",
            "sama":  "Sama Koshtha — standard dose; Eranda (castor oil) for clinic, Triphala for home",
            "mridu": "Mridu Koshtha — loose bowels; ONLY Triphala (mild); Atiyoga risk with Eranda or Trivrit",
        }
        if koshtha == "krura":
            strength = "strong" if setting == "clinic" else "moderate"
        elif koshtha == "mridu":
            strength = "mild"
        else:
            strength = "mild" if setting == "home" else "moderate"
        # Koshtha fixes the strength — that is not negotiable, since Atiyoga in a
        # Mridu Koshtha is the risk the rule exists for. Within a strength band the
        # indication decides, which is what makes Avipattikara reachable: it and
        # Eranda are both "moderate", and taking the first match meant an acidity
        # patient got castor oil while the drug authored for acidity went unused.
        band = [d for d in drugs if d.get("strength") == strength]
        result["pradhana_aushadha"] = (
            _select_from_compendium(band, medical_history, vikriti_dom)
            if band else (drugs[-1] if drugs else {})
        )
        result["koshtha_virechana_note"] = _KOSHTHA_NOTES.get(koshtha, _KOSHTHA_NOTES["sama"])

    elif pradhana_karma == "vamana":
        vam = aus.get("vamana_drugs", [])
        # Bala decides the emetic's strength — CS Sutrasthana 15, Bala Pareeksha.
        # Taking vam[0] unconditionally handed every patient Madanaphala, the strong
        # one, and left Vacha and Neem unreachable. Keying it on the setting instead
        # was no better: Vamana is clinic-only, so the mild band was still dead, and
        # "which room you are in" is not what decides how hard to purge someone.
        strength = {"uttama": "strong", "madhyama": "moderate", "manda": "mild"}.get(bala, "moderate")
        band = [d for d in vam if d.get("strength") == strength] or vam
        result["pradhana_aushadha"] = _select_from_compendium(band, medical_history, vikriti_dom)
        result["vamana_bala_note"] = (
            f"{_BALA_LABEL.get(bala, 'Madhyama Bala')} — {strength} emetic selected. "
            "Dose is titrated to Vega, not to volume; see the drug's dose note."
        )

    elif pradhana_karma in ("basti", "basti_matra"):
        # The six condition-specific Niruha formulations that used to be an if/elif
        # chain here are now KB rows with `indications`. Two things were wrong with
        # the chain beyond its being hardcoded: it matched by raw substring while
        # every safety gate in this file uses `term_in_condition`, and its oil names
        # duplicated compendium entries that carried their own `use` text — two
        # descriptions of Ksheerabala Taila that could drift apart.
        result["basti_kashayam"] = _select_from_compendium(
            aus.get("kashayam_basti", []), medical_history, vikriti_dom)
        result["basti_oil"] = _select_from_compendium(
            aus.get("oils_external", []), medical_history, vikriti_dom)

    elif pradhana_karma == "nasya":
        # Nasya oils were likewise hardcoded, including three — Anu Taila,
        # Shadbindu Taila, Brahmi Ghrita — that exist in the compendium.
        nasal = [
            o for o in aus.get("oils_external", [])
            if "nasya" in o.get("use", "").lower() or o.get("dosha") == "all"
        ] or aus.get("oils_external", [])
        result["nasya_oil"] = _select_from_compendium(nasal, medical_history, vikriti_dom)

    # ── Disease-specific adjuvant Aushadha (Sahayoga Dravya) ─────────────────
    # Seven formulations that were an if/elif chain of dict literals here, matched
    # by raw substring — `"kidney" in m` — while every safety gate in this file uses
    # `term_in_condition`. They are `aushadha_compendium.sahayoga_dravya` now: they
    # match precisely, and they can be reviewed with the rest of the compendium
    # rather than by reading Python.
    # Each is gated per constituent — see `_gate_formulation`. Until this, they
    # passed no contraindication check whatsoever.
    for adjuvant in aus.get("sahayoga_dravya", []):
        if not any(term_in_condition(c, t)
                   for c in medical_history for t in (adjuvant.get("indications") or [])):
            continue
        gate = _gate_formulation(adjuvant.get("components", []), medical_history,
                                 medications, existing_ayurvedic)
        if not gate["kept"]:
            # Nothing in the formulation is safe for this patient. Recording it is
            # the point: a silently absent adjuvant looks identical to one that was
            # never indicated, and the Vaidya needs to know it was considered.
            #
            # This branch does not fire against the herb table as it stands — every
            # one of the seven formulations contains at least one constituent with no
            # hard contraindication, so something always survives. It is kept because
            # that is a property of the current authoring, not of the design, and a
            # reviewer marking one more herb `hard` would make it reachable. Covered
            # at unit level in test_panchakarma_adjuvants rather than end to end,
            # because there is presently no profile that reaches it.
            result.setdefault("withheld_aushadha", []).append({
                "id": adjuvant["id"],
                "name": adjuvant.get("name"),
                "reason": "Every constituent is contraindicated for this patient.",
                "withheld": gate["withheld"],
            })
            continue
        result[adjuvant["id"]] = {
            **{k: v for k, v in adjuvant.items()
               if k not in ("id", "indications", "components")},
            **{k: v for k, v in (
                ("components_withheld", gate["withheld"]),
                ("component_cautions", gate["cautions"]),
                ("drug_interactions", gate["interactions"]),
                ("already_taking", gate["duplicates"]),
            ) if v},
        }

    # Rasayana (post-PK). The KB keys this block BY CONDITION —
    # `reproductive_female`, `bone_joint`, `medhya_brain` — and selection was by
    # dosha alone, so a PCOS patient and an osteoarthritis patient both received the
    # generic dosha Rasayana while Shatavari and Laksha Guggulu, authored for
    # exactly them, went unused. Three of the eight keys were reachable.
    ras = protocols.get("paschat_karma", {}).get("rasayana_integration", {}).get("rasayana_by_condition", {})
    ras_dosha_key = {
        "vata": "vata_neurological", "pitta": "pitta_inflammatory", "kapha": "kapha_metabolic",
    }.get(vikriti_dom, "general_immunity")

    # `reproductive_female` and `reproductive_male` both list infertility; gender is
    # what separates them, and without it the first would always win.
    def _rasayana_is_safe(entry: dict) -> bool:
        # ANY withheld constituent disqualifies the entry, where an adjuvant would
        # simply lose that constituent. A Rasayana is one `herb` string — "Shilajit
        # + Guggulu" — and dropping Shilajit from the component list does not change
        # the string the patient reads, so a trimmed Rasayana still tells a CKD
        # patient to take Shilajit. Nothing to trim means nothing but skip.
        gate = _gate_formulation(entry.get("components", []), medical_history,
                                 medications, existing_ayurvedic)
        return bool(gate["kept"]) and not gate["withheld"]

    # The Rasayana is gated harder than the adjuvants and skipped rather than
    # trimmed: most entries are a single herb, so withholding a constituent leaves
    # nothing, and this is the one prescription the plan tells the patient to
    # continue for MONTHS after the course ends. A hyperthyroid patient handed
    # Ashwagandha "for 3 months" is taking it long after anyone is watching.
    candidates = [
        entry for key, entry in ras.items()
        if any(term_in_condition(c, t)
               for c in medical_history for t in (entry.get("indications") or []))
        and entry.get("gender") in (None, gender)
    ]
    fallbacks = [ras.get(ras_dosha_key), ras.get("general_immunity")]

    chosen, rasayana_note = None, None
    for entry in candidates + [f for f in fallbacks if f]:
        if entry and _rasayana_is_safe(entry):
            if entry is not (candidates[0] if candidates else fallbacks[0]):
                rasayana_note = (
                    "The Rasayana indicated for your condition is contraindicated for you; "
                    "a safe alternative is given instead. Discuss the substitution with a Vaidya."
                )
            chosen = entry
            break

    if chosen:
        gate = _gate_formulation(chosen.get("components", []), medical_history,
                                 medications, existing_ayurvedic)
        result["rasayana"] = {
            **{k: v for k, v in chosen.items() if k not in ("components", "indications")},
            **({"cautions": gate["cautions"]} if gate["cautions"] else {}),
            **({"drug_interactions": gate["interactions"]} if gate["interactions"] else {}),
            **({"already_taking": gate["duplicates"]} if gate["duplicates"] else {}),
            **({"substitution_note": rasayana_note} if rasayana_note else {}),
        }
    else:
        # Every Rasayana in the KB is contraindicated. Saying so is the answer;
        # picking the least-bad one to fill the field is not.
        result["rasayana"] = {
            "herb": None,
            "unavailable_reason": (
                "No Rasayana in the formulary is safe alongside your recorded conditions "
                "and medications. A Vaidya must select one individually — do not substitute "
                "an over-the-counter tonic."
            ),
        }

    return result


# ── Samsarjana Krama ──────────────────────────────────────────────────────────

def _samsarjana_krama(pradhana_karma: str, protocols: dict) -> list[dict]:
    """Post-PK dietary re-entry stages — different per Pradhana Karma type.

    Nasya and Raktamokshana get none. Samsarjana Krama exists to rekindle an Agni
    left weak by an emptied Koshtha; neither of those empties one, and the
    post-Virechana ladder that used to be the catch-all opens with "Laja Peya —
    replaces fluids lost in purgation". Handed to a patient whose Virechana had just
    been withheld for low Ojas, that described a procedure they had specifically not
    undergone, and put them on a hypocaloric ladder for the depletion it was meant
    to protect them from.
    """
    sk = protocols.get("paschat_karma", {}).get("samsarjana_krama", {})
    if pradhana_karma == "vamana":
        return sk.get("post_vamana", {}).get("stages", [])
    if pradhana_karma == "virechana":
        return sk.get("post_virechana", {}).get("stages", [])
    if pradhana_karma in ("basti", "basti_matra"):
        return sk.get("post_basti", {}).get("post_course", [])
    return []


# ── Shamana (Palliative) Protocol ─────────────────────────────────────────────
# Reached when `_determine_shodhana_or_shamana` returns a clinically ineligible
# verdict. Shamana is not "Shodhana with the cleanse removed" — it is a distinct
# classical treatment arm (CS Sutrasthana 15): correct Agni, pacify the vitiated
# Dosha in place, then rebuild. None of it expels anything, so nothing here may
# emit a Pradhana Karma instruction at any strength.

# Snehapana is Shodhanartha Sneha — an escalating dose titrated to Samyak Snigdha
# so that Doshas liquefy and move toward expulsion. In a plan with no expulsion
# step that is the wrong procedure: it mobilises Doshas with nowhere to send them.
# Shamana uses Shamana-matra Sneha, a small fixed dose, described separately below.
#
# Samsarjana Krama is excluded for the matching reason: it is the graded re-entry
# from a Koshtha emptied by Shodhana. Zeroing the `samsarjana_krama` block was not
# enough — the same procedure also sits in the therapy KB as a schedulable row, so
# it kept appearing on the calendar as "Strict Samsarjana Krama (Dietary Re-entry)".
# Blocking the summary and leaving the day is how prose defects survive a fix.
_SHAMANA_EXCLUDED_THERAPIES = {
    "snehapana_home", "snehapana_clinic",
    "samsarjana_krama_strict", "samsarjana_krama_mild",
}

# The Deepana-Pachana phase excludes the same oleation rows for its own reason:
# `ama_correction_first` places the herbs "before starting Snehana", so Snehapana
# inside that phase oils an Ama-laden Srotas — the exact sequencing the phase exists
# to prevent. The two sets coincide today; they are named separately because the
# reasons are different and either could change alone.
_DEEPANA_EXCLUDED_THERAPIES = {"snehapana_home", "snehapana_clinic"}

def _shamana_regimen(vikriti_dom: str) -> dict:
    """The Ahara and Vihara a Shamana plan prescribes, from the procedures KB.

    This was a dict literal here. It is dietary and lifestyle instruction given to a
    patient — data, not control flow — and holding it in Python meant it could not be
    translated, reviewed as a document, or checked against the rest of the KB.
    """
    regimen = pk_procedures.get("shamana_regimen", {})
    return regimen.get(vikriti_dom) or regimen.get("vata") or {}


def _deepana_pachana_action(elig: dict, protocols: dict) -> dict:
    """The pinned daily action for the Agni-correction phase."""
    ama_info = protocols.get("shodhana_eligibility", {}).get("ama_correction_first", {})
    herbs = elig.get("ama_correction_herbs") or ama_info.get("herbs", [])
    signs = elig.get("ama_correction_signs") or ama_info.get("signs_ama_cleared", [])
    action = _render_procedure("deepana_pachana", {
        "herb_name": herbs[0] if herbs else "Trikatu (Ginger + Black Pepper + Pippali)",
        "alternatives": ", ".join(herbs[1:3]) if len(herbs) > 1 else "Chitrakadi Vati",
        "diet": ama_info.get("diet_during",
                             "Light, warm, easily digestible food. Avoid heavy, cold, raw and fermented."),
        "signs": "; ".join(signs) if signs else "the tongue coating clears and appetite returns",
    })
    return {**action, "id": "deepana_pachana_main", "is_deepana_pachana": True}


def _brimhana_action(vikriti_dom: str, aushadha: dict) -> dict:
    """The pinned daily action for the Brimhana (nourishing) phase."""
    ras = aushadha.get("rasayana") or {}
    action = _render_procedure("brimhana", {
        "herb_name": ras.get("herb", "Chyawanprash"),
        "dose": ras.get("dose", "1 tsp twice daily with warm milk"),
        "duration": ras.get("duration", "3 months"),
        "timing": ras.get("timing", "Daily, with warm milk"),
    })
    return {**action, "id": "brimhana_main", "is_brimhana": True}


# ── Goal ──────────────────────────────────────────────────────────────────────
# `panchakarma_goal` is offered in the UI, validated by the schema, echoed into
# `user_summary` — and was read by no engine code. Picking "Stress Relief" instead
# of "Weight Loss" changed nothing about the plan produced.
#
# Each goal moves something the classical texts would move for that aim: which
# therapies the pool prefers, how long the in-plan Rasayana tail runs, and for a
# seasonal cleanse, whether the Karma follows the Vikriti or the Ritu calendar.
_GOAL_PROFILES: dict[str, dict] = {
    "detox": {
        "label": "Detox",
        "boost": {},
        "rasayana_tail": 3,
        "karma_source": "vikriti",
        "note": "Standard Shodhana-forward course: the Karma follows your Vikriti.",
    },
    "rejuvenation": {
        "label": "Rejuvenation (Rasayana)",
        # Brimhana therapies — the nourishing ones — lead the pool.
        "boost": {"abhyanga_clinic": 3, "abhyanga_self": 3, "shirodhara": 3,
                  "rasayana_herbs": 4, "yoga_nidra": 2, "udvartana": -2, "udvartana_home": -2},
        "rasayana_tail": 7,
        "karma_source": "vikriti",
        "note": (
            "Rasayana-weighted: Shodhana is the preliminary here, not the aim. Nourishing "
            "therapies lead, and the Rasayana phase runs at its full in-plan length — "
            "Rasayana works over months, so treat the plan's end as its beginning."
        ),
    },
    "stress_relief": {
        "label": "Stress Relief (Manovaha Srotas)",
        "boost": {"shirodhara": 5, "yoga_nidra": 4, "gentle_pranayama": 4,
                  "abhyanga_clinic": 2, "abhyanga_self": 2,
                  "udvartana": -3, "udvartana_home": -3, "bashpa_sweda_clinic": -1},
        "rasayana_tail": 5,
        "karma_source": "vikriti",
        "note": (
            "Manovaha Srotas focus: Shirodhara (Murdha Taila), Yoga Nidra and Anulom Vilom "
            "lead. Stimulating and Ruksha therapies such as Udvartana are demoted — they "
            "raise Vata, which is what an anxious Manas least needs."
        ),
    },
    "seasonal_cleanse": {
        "label": "Seasonal Cleanse (Ritu Shodhana)",
        "boost": {},
        "rasayana_tail": 3,
        "karma_source": "ritu",
        "note": (
            "Ritu Shodhana: the Karma follows the season's own indication from the "
            "Ritu-Shodhana calendar rather than your Vikriti — which is what a seasonal "
            "cleanse means. Doshas accumulate on a seasonal cycle and are expelled on one."
        ),
    },
    "specific_condition": {
        "label": "Specific Condition",
        "boost": {},
        "rasayana_tail": 5,
        "karma_source": "vikriti",
        "note": (
            "Condition-led: the Karma follows your Vikriti, and the Aushadha is selected "
            "against your recorded conditions — see the Aushadha section for the "
            "Srotas-specific formulations added for them."
        ),
    },
}


def _goal_profile(pk_prefs: dict) -> dict:
    goal = pk_prefs.get("panchakarma_goal") or "detox"
    return {**_GOAL_PROFILES.get(goal, _GOAL_PROFILES["detox"]), "goal": goal}


def _apply_seasonal_karma(pradhana: dict, ritu_ctx: dict, setting: str, protocols: dict) -> tuple[dict, str | None]:
    """Point the Karma at the season's indication for a Ritu Shodhana cleanse."""
    seasonal = ritu_ctx.get("primary_shodhana")
    if not seasonal or seasonal == pradhana.get("primary"):
        return pradhana, None

    # Raktamokshana has no home form; a seasonal cleanse must not become the reason
    # a home user is scheduled for bloodletting.
    if setting == "home" and seasonal in ("raktamokshana", "vamana"):
        return pradhana, (
            f"{ritu_ctx.get('ritu_name', ritu_ctx.get('ritu', 'This season'))} indicates "
            f"{seasonal.title()}, which has no home form. The Karma follows your Vikriti instead — "
            "book a clinic if you want the seasonal cleanse."
        )

    data = protocols.get("pradhana_karma", {}).get(seasonal, {})
    return (
        {
            **pradhana,
            "primary": seasonal,
            "reason": (
                f"Ritu Shodhana — {ritu_ctx.get('ritu_name', ritu_ctx.get('ritu', ''))} indicates "
                f"{seasonal.title()}. {ritu_ctx.get('reason', '')}"
            ).strip(),
            "protocol": data or pradhana.get("protocol", {}),
            "seasonal_selection": True,
            "vikriti_karma": pradhana.get("primary"),
        },
        None,
    )


# ── Phase Sequencers ──────────────────────────────────────────────────────────
# Each phase used to be laid out by repeating pool[0] on every day. A 21-day Vata
# plan therefore scheduled Niruha Basti — the depleting one — eight days running,
# under a card reading "Yoga Basti (8-Basti Schedule) — 3 Niruha + 5 Anuvasana".
# It delivered 8 Niruha and 4 Anuvasana: exactly inverted, and the number on the
# card and the calendar beneath it were different plans.


def _render_procedure(key: str, fields: dict, extra_steps: list[str] | None = None) -> dict:
    """Build a pinned day action from `panchakarma_procedures.json`.

    Steps whose placeholders cannot be filled are dropped rather than printed with a
    brace in them, and a test asserts every placeholder in the file is one some call
    site supplies — so a dropped step means a bug caught in CI, not a silently
    shorter instruction reaching a patient.
    """
    spec = pk_procedures.get(key)
    if not spec:
        return {}

    def fill(text: str) -> str | None:
        try:
            return text.format(**fields).strip()
        except (KeyError, IndexError):
            return None

    steps = [t for t in (fill(s) for s in spec.get("steps", [])) if t]
    steps += [t for t in (extra_steps or []) if t]

    name = fill(spec.get("name", "")) or spec.get("name", "")
    return {
        "name": name,
        "duration_minutes": spec.get("duration_minutes"),
        "benefits": spec.get("benefits", ""),
        "timing": fill(spec.get("timing", "")) or spec.get("timing", ""),
        "pradhana_notes": " ".join(steps),
        "steps": steps,
    }


def _aushadha_name(value, default: str) -> str:
    """Compendium selections are dicts; several call sites still accept a bare string.

    The dict branches used to discard the value and return a hardcoded default, so
    every Basti day printed "Tila Taila" no matter which oil had been selected —
    a condition-specific choice made correctly and thrown away one line before it
    reached the patient.
    """
    if isinstance(value, str):
        return value or default
    if isinstance(value, dict):
        return value.get("name") or default
    return default


def _basti_sequence(subtype: str, days: int, protocols: dict) -> list[dict]:
    """The per-day Anuvasana/Niruha pattern for a Basti course.

    Yoga Basti's day-by-day schedule is authored in
    `pradhana_karma.basti.subtypes.yoga_basti.schedule` and is used verbatim when it
    fits. Kala (6 Niruha of 16) and Karma (12 of 30) give totals but no pattern, so
    they are generated by the rule the authored schedule itself follows: Niruha on
    the even days up to twice the Niruha count, Anuvasana everywhere else. That
    starts the course on oil, alternates through the middle, and closes on oil —
    Anuvasana before and after each Niruha is the classical safeguard, because
    Niruha alone is Lekhana and Vata rises without the Sneha around it. A test
    checks the rule reproduces the authored schedule exactly.
    """
    subtypes = protocols.get("pradhana_karma", {}).get("basti", {}).get("subtypes", {})
    entry = subtypes.get(subtype, {})

    authored = entry.get("schedule")
    if authored and len(authored) >= days:
        return [
            {"type": d.get("type", "anuvasana"), "note": d.get("note", "")}
            for d in authored[:days]
        ]

    # Niruha count from the subtype's own totals, scaled if the course is short.
    total = entry.get("total_days") or days
    niruha_total = {"yoga_basti": 3, "kala_basti": 6, "karma_basti": 12}.get(subtype, 3)
    if isinstance(total, int) and total > 0 and days < total:
        niruha_total = max(1, round(niruha_total * days / total))

    sequence = []
    for day in range(1, days + 1):
        is_niruha = day % 2 == 0 and day <= niruha_total * 2
        sequence.append({
            "type": "niruha" if is_niruha else "anuvasana",
            "note": (
                "Start with oil — lubricates and prepares" if day == 1
                else "End with oil — soothes and nourishes" if day == days
                else "Decoction expels Doshas" if is_niruha
                else ""
            ),
        })
    return sequence


def _basti_day_action(day_index: int, sequence: list[dict], aushadha: dict,
                      basti_info: dict, protocols: dict) -> dict:
    """The pinned action for one day of a Basti course — the day's own procedure."""
    step = sequence[day_index] if day_index < len(sequence) else {"type": "anuvasana", "note": ""}
    basti_kb = protocols.get("pradhana_karma", {}).get("basti", {})
    common = {
        "oil_name": _aushadha_name(aushadha.get("basti_oil"), "Tila Taila"),
        "position": f"Day {day_index + 1} of {len(sequence)} — {basti_info.get('name', 'Basti course')}",
        "sequence_note": step.get("note", ""),
    }

    if step["type"] == "niruha":
        formula = basti_kb.get("niruha_basti", {}).get("classical_formula", {})
        action = _render_procedure("basti_niruha", {
            **common,
            "kashayam_name": _aushadha_name(aushadha.get("basti_kashayam"), "Dashamoola Kashayam"),
            "total_volume": formula.get("total_volume", "~550 ml"),
            "temperature": formula.get("temperature", "warm — 38°C"),
            "mix_order": " → ".join(i["item"] for i in formula.get("ingredients", []))
                         or "Madhu → Saindhava → Sneha → Kalka → Kashayam",
        })
        return {**action, "id": "basti_niruha_day", "is_pradhana_karma": True}

    action = _render_procedure("basti_anuvasana", {
        **common,
        "anuvasana_formula": basti_kb.get("anuvasana_basti", {}).get(
            "formula", "60–120 ml warm medicated oil"),
    })
    return {**action, "id": "basti_anuvasana_day", "is_pradhana_karma": True}


def _samsarjana_day_action(day_index: int, stages: list[dict], total_days: int) -> dict | None:
    """The Samsarjana stage that belongs on one Paschat day.

    The engine already computed the staged re-entry — Peya → Vilepi → Yusha → rice
    — and then scheduled a row called "Strict Samsarjana Krama (Dietary Re-entry)"
    identically on eight consecutive days. The whole clinical content of Samsarjana
    is that it is graded; a flat repeat of its name is the one form that carries none
    of it. Agni is at its lowest immediately after Shodhana, so the early stages get
    one day each and the last stage absorbs whatever days remain.
    """
    if not stages:
        return None
    stage = stages[min(day_index, len(stages) - 1)]
    is_last = day_index >= len(stages) - 1
    holding = is_last and total_days > len(stages)
    number = stage.get("stage", day_index + 1)

    action = _render_procedure("samsarjana", {
        "stage": number,
        "food": stage.get("food", "Light, warm, easily digestible food"),
        "recipe": stage.get("recipe", ""),
        "note": stage.get("note", ""),
    })
    if holding:
        # "Move to the next stage" is wrong on the last one — there is no next stage.
        hold = pk_procedures.get("samsarjana", {}).get("final_stage_step", "")
        action["steps"] = [x for x in action["steps"] if not x.startswith("Move to the next stage")]
        if hold:
            action["steps"].append(hold)
        action["pradhana_notes"] = " ".join(action["steps"])

    return {**action, "id": f"samsarjana_stage_{number}", "is_samsarjana": True,
            "timing": stage.get("timing", action.get("timing", "All meals today"))}


_TIME_BUDGET_MINUTES = {"15 min": 15, "30 min": 30, "1 hour": 60, "2+ hours": 120}


def _trim_day_to_time_budget(schedule: list[dict], pk_prefs: dict, pkt: list) -> list[str]:
    """Cap each day's self-care minutes at the budget the patient gave.

    The field is described as "Time available daily for therapies" and was applied
    per-therapy: a 30-minute budget admitted four 15-minute therapies. Since every
    self-care row in the KB is 15 minutes or less, no budget ever excluded anything,
    and the question could not change a plan whatever the answer.

    Clinician-administered rows are exempt — the clinic allots that time, not the
    patient. The Karma itself is never trimmed: it is the appointment, not an extra.
    """
    budget = _TIME_BUDGET_MINUTES.get(pk_prefs.get("self_care_time_per_day", "30 min"), 30)
    by_id = {t["id"]: t for t in pkt}
    dropped: set[str] = set()

    for day in schedule:
        spent, kept = 0, []
        for row in day["therapies"]:
            kb = by_id.get(row["id"], {})
            pinned = row.get("core") or any(
                row.get(k) for k in ("is_pradhana_karma", "is_deepana_pachana",
                                     "is_brimhana", "is_samsarjana")
            )
            self_care = "home" in (kb.get("setting_required") or [])
            minutes = row.get("duration_minutes") or 0
            if pinned:
                spent += minutes if self_care else 0
                kept.append(row)
                continue
            if not self_care:
                kept.append(row)
                continue
            if spent + minutes > budget and kept:
                dropped.add(row["name"])
                continue
            spent += minutes
            kept.append(row)
        day["therapies"] = kept

    return sorted(dropped)


def _therapy_row(t: dict, core: bool = False) -> dict:
    """The shape a therapy takes on a scheduled day.

    `core` marks a row the phase is defined by — the Abhyanga and Swedana of
    Purvakarma, the lead therapy of a rotation. The time budget trims around it but
    never through it: a 15-minute budget that drops Swedana leaves Purvakarma as
    half a procedure, which is the fault the pair exists to prevent.

    `cautions` is carried through deliberately. A relative contraindication that
    stays in the engine and never reaches the day is the same defect as one that
    was never checked — the patient does the therapy either way, without the
    modification that made it safe for them.
    """
    row = {
        "id": t["id"], "name": t["name"],
        "duration_minutes": t["duration_minutes"], "benefits": t["benefits"],
    }
    if core:
        row["core"] = True
    if t.get("cautions"):
        row["cautions"] = t["cautions"]
    return row


def _assemble_rotating_phase(pool, target_days, start_day, phase_name, pinned=None):
    """Lay a therapy pool across a phase, rotating so consecutive days differ.

    `assemble_phase` repeats pool[0] every single day, which is how a 21-day plan
    came to schedule the same therapy eight times in a row. Here each day takes the
    next therapy in the pool and the one after it, so a pool of four fills four
    distinct days before it repeats.
    """
    if target_days <= 0:
        return []
    schedule = []
    for i in range(target_days):
        therapies = []
        if pinned:
            therapies.append(pinned)
        if pool:
            therapies.append(_therapy_row(pool[i % len(pool)], core=True))
            if len(pool) > 1:
                therapies.append(_therapy_row(pool[(i + 1) % len(pool)]))
        schedule.append({"day": start_day + i, "phase": phase_name, "therapies": therapies})
    return schedule


def _build_shamana_plan(
    user_profile: dict,
    pk_prefs: dict,
    protocols: dict,
    pkt: list,
    elig: dict,
    vikriti_dom: str,
    aushadha: dict,
    total_days: int,
    triage_doshas: list[tuple[str, str]] | None = None,
) -> dict:
    """Assemble the three-phase Shamana arm: Agni correction → pacification → nourishment.

    Returns the phase list, the day-by-day schedule and the `shamana_protocol`
    detail block. The caller must not add a Pradhana Karma to any of it.
    """
    ama_needed  = bool(elig.get("ama_correction_needed"))
    agni_needed = bool(elig.get("agni_correction_needed"))
    deepana_needed = ama_needed or agni_needed

    # Deepana-Pachana runs 3–7 days classically (`ama_correction_first.duration_days`)
    # and is scaled to the plan, never past 40% of it.
    deepana_days = 0
    if deepana_needed:
        deepana_days = max(3, min(7, int(total_days * 0.40)))
        deepana_days = min(deepana_days, max(1, total_days - 2))

    # Brimhana closes every Shamana plan — depletion is why most users land here.
    brimhana_days = max(2, int(round((total_days - deepana_days) * 0.35)))
    shamana_days  = total_days - deepana_days - brimhana_days
    if shamana_days < 1:
        # Very short plan: the pacification body is the part that must survive.
        shamana_days = 1
        brimhana_days = max(1, total_days - deepana_days - shamana_days)

    pool = [
        t for t in (
            filter_and_score_therapies(user_profile, pk_prefs, "purvakarma", pkt, vikriti_dom,
                                       triage_doshas)
            + filter_and_score_therapies(user_profile, pk_prefs, "paschat", pkt, vikriti_dom,
                                         triage_doshas)
        )
        if t["id"] not in _SHAMANA_EXCLUDED_THERAPIES
    ]
    # No therapy from the `pradhana` phase may appear — that is the whole point.
    gentle_pool = [t for t in pool if t.get("phase") != "pradhana"]

    schedule: list[dict] = []
    phases: list[dict] = []
    day = 1

    if deepana_days:
        label = "Deepana-Pachana (Agni Correction)"
        schedule += _assemble_rotating_phase(
            gentle_pool, deepana_days, day, label,
            pinned=_deepana_pachana_action(elig, protocols),
        )
        phases.append({
            "key": "deepana_pachana", "label": "Deepana-Pachana",
            "sub": "Kindle Agni, digest Ama", "days": deepana_days,
        })
        day += deepana_days

    label = "Shamana Chikitsa (Pacification)"
    schedule += _assemble_rotating_phase(gentle_pool, shamana_days, day, label)
    phases.append({
        "key": "shamana", "label": "Shamana Chikitsa",
        "sub": f"{vikriti_dom.title()} pacification — no expulsion", "days": shamana_days,
    })
    day += shamana_days

    label = "Brimhana Rasayana (Nourishment)"
    schedule += _assemble_rotating_phase(
        gentle_pool, brimhana_days, day, label,
        pinned=_brimhana_action(vikriti_dom, aushadha),
    )
    phases.append({
        "key": "brimhana", "label": "Brimhana Rasayana",
        "sub": "Rebuild Dhatu and Ojas", "days": brimhana_days,
    })

    sd = _shamana_regimen(vikriti_dom)
    ama_info = protocols.get("shodhana_eligibility", {}).get("ama_correction_first", {})

    return {
        "schedule": schedule,
        "phases": phases,
        "days": {"deepana": deepana_days, "shamana": shamana_days, "brimhana": brimhana_days},
        "protocol": {
            "why": (
                "Shodhana (Vamana, Virechana, Basti, Nasya, Raktamokshana) is withheld for the "
                "reasons listed above. This plan treats the same imbalance by the Shamana route: "
                "correct Agni, pacify the Dosha where it sits, then rebuild what is depleted. "
                "Nothing in it expels Doshas, and no purgative, emetic or enema appears at any strength."
            ),
            "blocking_reasons": elig.get("blocking_reasons", []),
            "deepana_pachana": ({
                "needed":   True,
                "why":      ("Ama present — Shodhana would drive it deeper into the Srotas"
                             if ama_needed else
                             "Manda Agni — purification cannot occur if Agni cannot process dislodged Doshas"),
                "herbs":    elig.get("ama_correction_herbs") or ama_info.get("herbs", []),
                "duration": ama_info.get("duration_days", "3–7 days"),
                "signs_cleared": elig.get("ama_correction_signs") or ama_info.get("signs_ama_cleared", []),
                "diet":     ama_info.get("diet_during", ""),
            } if deepana_needed else {"needed": False}),
            "shamana_chikitsa": {
                "principle":   sd["principle"],
                "sneha_matra": sd["sneha_matra"],
                "ahara":       sd["ahara"],
                "vihara":      sd["vihara"],
            },
            "brimhana": {
                "why": (
                    "Every Shamana plan ends in Brimhana because depletion — of Bala, Ojas or Dhatu — "
                    "is why most patients are here. This is the phase that makes a future Shodhana possible."
                ),
                "rasayana": aushadha.get("rasayana", {}),
            },
            "reassessment": (
                "Re-assess Bala, Agni, Ama and Ojas with a Vaidya before considering Shodhana. "
                "The verdict above is a snapshot of the profile on file, not a permanent finding."
            ),
        },
    }


# ── Therapy Schedule Helpers (unchanged logic) ─────────────────────────────────

def _triage_dosha_signals(condition_triage: dict | None) -> list[tuple[str, str]]:
    """(condition, dosha) for unrecognised diagnoses the triage could place.

    A disease the KB knows contributes its Dosha to the picture through
    `disease_signal`. A disease it does not know contributed nothing at all: two
    patients with two different unmapped diagnoses received byte-identical
    schedules, because the only thing their diagnosis changed was the sentence
    naming it.

    The triage already returns a Dosha for each condition it can place, and the
    engine only ever printed it. This is the one field of the three it returns
    that the knowledge base can act on — every therapy row carries `dosha_effect`,
    while none carries a Srotas tag, and nothing keys off `classical_analogue`.
    Wiring the other two means authoring clinical claims, which is a Vaidya's job,
    not a code change.

    It is a preference-strength signal only: it reorders the therapy pool and is
    outranked by the assessed Vikriti. It never selects the Karma, never lifts a
    contraindication, and is labelled as AI-derived wherever it shows.
    """
    out: list[tuple[str, str]] = []
    for condition, finding in (condition_triage or {}).items():
        if not isinstance(finding, dict) or finding.get("status") != "ok":
            continue
        dosha = finding.get("dosha")
        if dosha in ("vata", "pitta", "kapha"):
            out.append((condition, dosha))
    return out


def filter_and_score_therapies(user_profile, pk_prefs, phase, pk_therapies_list, vikriti_dom=None,
                               triage_doshas: list[tuple[str, str]] | None = None):
    scored = []
    dominant = vikriti_dom or user_profile.get("dominant_dosha", "vata") or "vata"
    setting   = pk_prefs.get("setting", "home")
    experience = pk_prefs.get("detox_experience", "none")
    herbs      = pk_prefs.get("access_to_ayurvedic_herbs", "willing_to_buy")
    diet_ab    = pk_prefs.get("diet_adherence_ability", "partial")
    time_str   = pk_prefs.get("self_care_time_per_day", "30 min")

    # Explicit map. The chain it replaces worked only because "15" was tested before
    # "1" — every one of the schema's four values contains a "1" or a "2" somewhere,
    # so any reordering would silently have given "15 min" a 60-minute budget.
    max_dur = {"15 min": 15, "30 min": 30, "1 hour": 60, "2+ hours": 120}.get(time_str, 30)

    goal = _goal_profile(pk_prefs)

    # Every filter above this line is a preference filter — setting, experience,
    # herb access, diet adherence, time. Until this gate there was not one clinical
    # filter in pool selection at all: a hypertensive diabetic and a healthy athlete
    # received the same therapy pool, and the `contraindications` field the KB rows
    # carry was read by no code.
    # The gate matches against `medical_history`, but several of the states that
    # contraindicate a therapy are not conditions a user types — they are things
    # the engine derived. Snehapana's bar on high Ama, Swedana's on Pitta and
    # Udvartana's Vata caution could never have fired against a history list, so
    # they are supplied here as findings alongside it.
    medical_history = list(user_profile.get("medical_history") or [])
    if user_profile.get("pregnancy_or_nursing"):
        medical_history.append("pregnancy")
    if (user_profile.get("ama_indicator") or "none") in ("high", "severe"):
        medical_history.append("high_ama")
    _agni = _AGNI_CANON.get(
        str(user_profile.get("agni_type")
            or _derive_agni(user_profile.get("digestion_quality"), dominant)).lower(),
        "sama",
    )
    if _agni == "manda":
        medical_history.append("manda_agni")
    if dominant in ("vata", "pitta", "kapha"):
        medical_history.append(f"{dominant}_aggravation")
    if (user_profile.get("age") or 30) > 70:
        medical_history.append("elderly")

    for t in pk_therapies_list:
        if t["phase"] != phase:
            continue
        if setting == "home"   and "home"   not in t["setting_required"]: continue
        if setting == "clinic" and "clinic" not in t["setting_required"]: continue
        if experience == "none" and t["experience_required"] in ("some", "experienced"): continue
        if experience == "some" and t["experience_required"] == "experienced": continue
        if herbs == "no" and t["herb_requirement"] == "specific_ayurvedic": continue
        if diet_ab == "lifestyle_only" and t["diet_strictness"] in ("strict", "partial"): continue
        if diet_ab == "partial" and t["diet_strictness"] == "strict": continue
        # `self_care_time_per_day` is a budget on the therapies the patient performs
        # themselves. Skipping the whole check in a clinic made the field dead for
        # clinic users while the UI still asked for it; applying it to everything
        # would have cut clinician-administered therapies whose time the clinic
        # allots, not the patient. Clinic-only rows are exempt; self-care is not,
        # wherever the patient happens to be.
        is_self_care = "home" in t["setting_required"]
        if is_self_care and t["duration_minutes"] > max_dur: continue

        contra = _therapy_contraindications(t["id"])
        if _match_contraindications(medical_history, contra["hard"]):
            continue

        soft_hits = _match_contraindications(medical_history, contra["soft"])
        if soft_hits:
            # The therapy stays, but never silently: the modification is attached
            # to the row so the schedule can print it beside the therapy name.
            t = {**t, "cautions": [{"condition": c, "mechanism": m} for c, m in soft_hits]}

        de = t.get("dosha_effect", {}).get(dominant, 0)
        score = 2 if de == -1 else 1 if de == 0 else -2
        # A therapy carrying cautions ranks below an equally-suitable one that does
        # not, so the pool prefers the option needing no modification.
        if soft_hits:
            score -= 1
        # The goal reorders what remains. Dosha suitability still dominates — a goal
        # is a preference, and a therapy that aggravates the vitiated Dosha does not
        # become right because the patient asked for stress relief.
        score += goal["boost"].get(t["id"], 0)

        # An unrecognised diagnosis the triage was able to place contributes its
        # Dosha here, at +1 — half the weight of the assessed Vikriti's -1 effect
        # (+2) and never enough to raise a therapy that aggravates the vitiated
        # Dosha (-2) above one that pacifies it. It reorders; it does not decide.
        for _cond, td in (triage_doshas or []):
            if t.get("dosha_effect", {}).get(td, 0) < 0:
                score += 1
                t = {**t, "triage_dosha_match": td}
                break

        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]


def _pradhana_day_action(pradhana_karma: str, aushadha: dict, basti_info: dict | None, setting: str, ritu: str = "") -> dict:
    """The pinned 'main karma' action for every Pradhana day.

    All of the procedural prose this used to hold inline now lives in
    `panchakarma_procedures.json`; this function only gathers the values the
    templates need.
    """
    pk = pradhana_karma
    drug = aushadha.get("pradhana_aushadha", {})
    if not isinstance(drug, dict):
        drug = {"name": str(drug)}

    if pk == "virechana":
        spec = pk_procedures.get("virechana", {})
        conditional = spec.get("conditional_steps", {})
        extra = []
        if aushadha.get("koshtha_virechana_note"):
            extra.append(conditional.get("koshtha", "").format(
                koshtha_note=aushadha["koshtha_virechana_note"]))
        if ritu == "grishma":
            extra.append(conditional.get("grishma", ""))
        action = _render_procedure("virechana", {
            "drug_name": drug.get("name", "Virechana drug"),
            "dose": drug.get("dose", "as directed"),
        }, extra_steps=extra)
        return {**action, "id": "virechana_main", "is_pradhana_karma": True}

    if pk == "vamana":
        action = _render_procedure("vamana", {
            "drug_name": drug.get("name", "Madanaphala Phanta"),
            "dose": drug.get("dose", "as directed by the Vaidya"),
            "dose_note": drug.get("dose_note", ""),
        })
        return {**action, "id": "vamana_main", "is_pradhana_karma": True}

    if pk == "nasya":
        action = _render_procedure("nasya", {
            "oil_name": _aushadha_name(aushadha.get("nasya_oil"), "the prescribed nasal oil"),
        })
        return {**action, "id": "nasya_main", "is_pradhana_karma": True}

    if pk == "basti_matra":
        action = _render_procedure("basti_matra", {
            "oil_name": _aushadha_name(aushadha.get("basti_oil"), "warm sesame oil"),
        })
        return {**action, "id": "basti_matra_main", "is_pradhana_karma": True}

    if pk == "basti":
        # A multi-day Basti course is rendered per day by `_basti_day_action`; this
        # is the single-entry fallback for a course of one.
        return _basti_day_action(0, [{"type": "anuvasana", "note": ""}], aushadha,
                                 basti_info or {}, pk_protocols)

    if pk == "raktamokshana":
        action = _render_procedure("raktamokshana", {})
        return {**action, "id": "rakta_main", "is_pradhana_karma": True}

    return {}


def assemble_phase(pool, target_days, start_day, phase_name, always_both=False):
    """Lay the pool's first two therapies across a phase.

    `always_both` puts both on every day rather than alternating. Purvakarma needs
    it: Snehana and Swedana are a pair performed daily, not two options to trade off
    — Swedana is what opens the Srotas the oil has just loosened, so a day with the
    oil and no sudation is half a procedure.
    """
    if not pool:
        return []
    primary   = pool[0]
    secondary = pool[1] if len(pool) > 1 else None
    schedule  = []
    for i in range(target_days):
        day_therapies = [_therapy_row(primary, core=True)]
        if secondary and (always_both or i % 2 == 0):
            day_therapies.append(_therapy_row(secondary, core=always_both))
        schedule.append({"day": start_day + i, "phase": phase_name, "therapies": day_therapies})
    return schedule


# ── Main Entry Point ──────────────────────────────────────────────────────────

def generate_panchakarma_plan(user_profile: dict, pk_prefs: dict, pk_therapies_db=None,
                             condition_triage: dict | None = None) -> dict:
    """
    Full Panchakarma plan generator using classical protocol KB.
    Clinical decisions: Shodhana/Shamana, Pradhana Karma per Vikriti,
    Purvakarma duration, Basti subtype, Aushadha, Samsarjana Krama, Ritu context.
    """
    protocols  = pk_protocols
    pkt        = pk_therapies_db if pk_therapies_db is not None else pk_therapies
    total_days = int(pk_prefs.get("available_time_days", 7) or 7)
    _raw_setting = pk_prefs.get("setting", "home")
    # "both" = clinic-level decisions, home-level therapy pool for days when not at clinic
    setting    = "clinic" if _raw_setting in ("clinic", "both") else "home"

    # Vikriti takes precedence over Prakriti for PK planning
    vikriti_dom = (
        user_profile.get("vikriti_dominant")
        or user_profile.get("dominant_dosha")
        or "vata"
    )
    # Vikriti secondary must come ONLY from the current-imbalance assessment — never
    # fall back to the Prakriti secondary. Conflating them made a Kapha-vikriti patient
    # with a Pitta *constitution* wrongly resolve to the bidoshic pitta_kapha → Virechana
    # instead of the correct Kapha → Vamana (CS Sutrasthana 15). Absent a true secondary
    # Vikriti, treat as single-dosha and use the dominant-dosha Pradhana Karma.
    vikriti_sec = user_profile.get("vikriti_secondary")
    medical_history = user_profile.get("medical_history") or []

    # ── Rare / Unmapped Disease Detection ────────────────────────────────────
    # Any condition not in _DISEASE_DOSHA_SIGNAL is invisible to the rule engine.
    # We detect these, apply conservative safety defaults for severe conditions,
    # and flag them so the LLM enricher can run Nidana-Samprapti reasoning.
    from engine.dosha_analyzer import disease_signal
    # vocab-aware: a condition is "unmapped" only if it resolves to no central entry
    # even after synonym/classical-name normalization.
    unmapped_conditions = [c for c in medical_history if disease_signal(c) is None]

    # Severe/systemic disease keywords → force Shamana regardless of other criteria
    _SEVERE_KEYWORDS = {
        "cancer", "carcinoma", "sarcoma", "myeloma", "lymphoma", "leukemia",
        "tumor", "malignant", "metastatic", "amyloid", "huntington", "als",
        "als_", "motor_neuron", "failure", "transplant", "dialysis",
        "immunodeficiency", "hiv", "multiple_myeloma", "goodpasture",
    }
    # Severity is checked across EVERY condition, not only the unmapped ones. Being
    # mapped means the engine knows which Dosha the disease disturbs; it says nothing
    # about whether the patient can withstand Shodhana. "dialysis", "kidney_failure"
    # and "renal_failure" all normalise to chronic_kidney_disease and "hiv" maps to
    # itself, so every one of them cleared this check by being *recognised* — a
    # dialysis patient was routed to a full Niruha Basti course with no Vaidya-review
    # flag raised, on the strength of the vocabulary knowing the word.
    severe_conditions = [
        c for c in medical_history
        if any(kw in c.lower() for kw in _SEVERE_KEYWORDS)
    ]
    vaidya_review_required = bool(unmapped_conditions or severe_conditions)

    # Derive Agni type if not explicitly stored (from digestion quality — Charaka Sutrasthana 15).
    # Normalise to a canonical key so both dosha-keyed and classical-keyed agni_type values
    # resolve correctly (previously a stored 'vishama'/'manda'/'tikshna' silently showed as Sama Agni).
    _raw_agni = user_profile.get("agni_type") or _derive_agni(
        user_profile.get("digestion_quality"), vikriti_dom
    )
    agni_type = _AGNI_CANON.get(str(_raw_agni).lower(), "sama")
    agni_name = _AGNI_NAME.get(agni_type, "Sama Agni")

    # Bala proxy from fitness_level (CS Sutrasthana 15 — Bala Pareeksha)
    fitness = user_profile.get("fitness_level", "intermediate")
    bala_type, bala_note = _FITNESS_TO_BALA.get(fitness, ("madhyama", "Madhyama Bala"))

    # ── Clinical Decisions ────────────────────────────────────────────────────
    ritu_ctx    = _get_ritu_context(
        protocols,
        pk_prefs.get("current_season") or user_profile.get("current_season"),
    )
    eligibility = _determine_shodhana_or_shamana(user_profile, pk_prefs, protocols)

    # Severe unmapped condition override — conservative Shamana.
    # Applied before any Karma is selected, so the override cannot be outrun by a
    # Pradhana Karma that was already chosen.
    if severe_conditions and eligibility.get("type") != "shamana":
        blocking = [
            f"Severe systemic condition(s) present: {', '.join(severe_conditions)}. "
            "Conservative Shamana applied — Vaidya assessment required before any Shodhana. "
            "Ref: CS Sutrasthana 15 (Bala Pareeksha mandatory)."
        ]
        eligibility = {
            **eligibility,
            "type": "shamana",
            "shodhana_eligible": False,
            "clinically_ineligible": True,
            "reasons": blocking,
            "blocking_reasons": blocking,
            "vaidya_override": True,
        }

    # ── Diagnoses the KB does not recognise ───────────────────────────────────
    # Placed beside the severe-condition override because it is the same kind of
    # finding: something about this patient that the classical criteria never saw.
    triage = _triage_eligibility_findings(unmapped_conditions, condition_triage)
    triage_terms = _triage_karma_terms(condition_triage)
    triage_doshas = _triage_dosha_signals(condition_triage)

    if triage["blocking"] and eligibility.get("type") != "shamana":
        eligibility = {
            **eligibility,
            "type": "shamana",
            "shodhana_eligible": False,
            # Not a clinical bar: nobody found this patient unfit. The engine could
            # not read the diagnosis, which a Vaidya can resolve in one appointment.
            "clinically_ineligible": False,
            "unassessed_condition": True,
            "reasons": [*eligibility.get("reasons", []), *triage["blocking"]],
            "blocking_reasons": [*eligibility.get("blocking_reasons", []), *triage["blocking"]],
        }
    elif triage["restricting"] and eligibility.get("type") == "shodhana":
        eligibility = {
            **eligibility,
            "type": "mridu_shodhana",
            "shodhana_eligible": False,
            "reasons": [*eligibility.get("reasons", []), *triage["restricting"]],
            "restricting_reasons": [*eligibility.get("restricting_reasons", []), *triage["restricting"]],
        }

    is_shamana = eligibility.get("type") == "shamana"
    goal = _goal_profile(pk_prefs)
    goal_notes: list[str] = [goal["note"]]

    # `contraindication_matrix.acute_fever` is the one row whose "allowed" list is
    # not a therapy: "nothing — wait for fever to resolve completely". Every other
    # finding narrows the plan; this one postpones it. Handing a febrile patient a
    # seven-day schedule answers a question they should not be asking yet, so the
    # plan is still produced — it is what to do afterwards — behind a notice saying
    # not to start.
    deferral = None
    _fever_hits = [
        c for c in medical_history
        if any(term_in_condition(c, t) for t in ("active_fever", "fever", "jwara"))
    ]
    if _fever_hits:
        deferral = {
            "reason": f"Active fever ({', '.join(_fever_hits)})",
            "notice": (
                "Do not begin this plan while the fever is present. Panchakarma during Jwara "
                "drives the Dosha inward and worsens the illness — the classical instruction is "
                "to wait rather than to substitute something milder. Start once the fever has "
                "fully resolved and appetite has returned, and re-generate the plan then: the "
                "assessment below reflects your profile during an acute illness."
            ),
            "resume_when": "Fever fully resolved, appetite returned, no residual weakness.",
            "source": "contraindication_matrix.acute_fever — blocked: all_shodhana",
        }

    # Mridu Shodhana takes the home-adaptation branch wherever the patient is.
    # A Manda Bala patient who books a clinic is still a Manda Bala patient: the
    # verdict has to reach Karma selection, Basti subtype AND drug strength, or
    # "mild" is a label on a plan that schedules Vamana with a clinic-strength
    # purgative. This is the setting the *therapy* is chosen for; `setting` stays
    # the setting the patient is actually in, which still governs the therapy pool.
    karma_setting = "home" if eligibility.get("type") == "mridu_shodhana" else setting

    # A Shamana plan has no Pradhana Karma at all — not a substituted one, not a
    # milder one. Selecting a Karma here and relying on later code not to print it
    # is exactly how a 78-year-old with severe Ama and a cancer diagnosis came to be
    # handed a castor-oil purgation schedule under a badge reading "Shamana".
    if is_shamana:
        pradhana = {
            "primary": None,
            "secondary": None,
            "reason": "No Pradhana Karma — patient is not eligible for Shodhana at any strength.",
            "sequence": "",
            "clinical_note": "",
            "protocol": {},
        }
        safety_warnings: list[str] = []
    else:
        pradhana = _select_pradhana_karma(vikriti_dom, vikriti_sec, karma_setting, protocols)
        if goal["karma_source"] == "ritu":
            pradhana, seasonal_note = _apply_seasonal_karma(pradhana, ritu_ctx, karma_setting, protocols)
            if seasonal_note:
                goal_notes.append(seasonal_note)
        pradhana, safety_warnings = _restrict_to_brimhana(pradhana, eligibility)
        # Safety gate: substitute karma if hard contraindicated by medical history
        pradhana, karma_warnings = _validate_karma_safety(pradhana, medical_history, triage_terms)
        safety_warnings += karma_warnings

        # Second gate, and second only: what the patient has told us they can supply.
        # It runs after the clinical one so that a preference can never reinstate a
        # route safety has already withdrawn.
        pradhana, capability_warnings = _validate_karma_capability(
            pradhana, karma_setting, pk_prefs, pkt)
        safety_warnings += capability_warnings

        # Either gate can conclude that no Karma remains. That is a Shamana verdict
        # arrived at from the other direction, and it has to reach the plan the same
        # way — otherwise the schedule is built for a Karma of None.
        if pradhana["primary"] is None:
            is_shamana = True
            no_karma_reason = pradhana["reason"].lstrip("⚠ ")
            # A patient who cannot follow the diet is not clinically ineligible for
            # purification, and the plan must not tell them they are — changing the
            # answer is enough, where a clinical bar needs a Vaidya. The distinction
            # travels in `reasons`, which the view renders; `clinically_ineligible`
            # is set correctly beside it but is currently read by nothing, here or
            # in the client, and this is not the change that should wire it up.
            by_preference = bool(pradhana.get("capability_substitution"))
            eligibility = {
                **eligibility,
                "type": "shamana",
                "shodhana_eligible": False,
                "clinically_ineligible": not by_preference,
                "reasons": [*eligibility.get("reasons", []), no_karma_reason],
                "blocking_reasons": [*eligibility.get("blocking_reasons", []), no_karma_reason],
            }

    if severe_conditions:
        safety_warnings.append(
            f"⚠ VAIDYA REVIEW REQUIRED: Severe systemic conditions ({', '.join(severe_conditions)}) "
            "require clinical assessment before PK. Plan uses conservative Shamana protocol."
        )

    # ── Phase Duration Splits ─────────────────────────────────────────────────
    # Deepana-Pachana precedes Snehana whenever Ama is present or Agni is Manda —
    # `ama_correction_first` is explicit that the herbs run "3-7 days ... before
    # starting Snehana". It used to produce a banner and no days, so a patient with
    # moderate Ama was told Ama must be cleared first and then handed a schedule
    # that began with Snehana on day 1.
    deepana_days = 0
    duration_notice = None
    # Every notice quotes the number the PATIENT gave. `total_days` is adjusted more
    # than once on the way through — once at the phase floor, once against the sum
    # of the phases — and a notice reading "extended from 8" to someone who asked
    # for 7 reports an intermediate the patient never saw.
    requested_days = total_days
    if is_shamana:
        purva_days = pradhana_days = paschat_days = 0
        basti_info = None
    else:
        # Every phase has a floor and a ceiling, both classical, and the course
        # length is what they sum to — not a budget divided up. Splitting the
        # requested days instead produced two opposite failures at once: a 21-day
        # Virechana course was 5 days of preparation, ONE day of Karma and FIFTEEN
        # days of Paschat, while a 3-day request silently returned a 5-day schedule
        # with `total_days` still reading 3.
        #
        # Paschat's floor is the one that is easy to miss: the Samsarjana ladder has
        # as many days as it has stages, and post-Vamana has seven. A Paschat phase
        # shorter than that cannot deliver the re-entry it names.
        _stages = _samsarjana_krama(pradhana["primary"], protocols)
        # In-plan only; the Rasayana itself runs for months after. The rejuvenation
        # goal is the one that earns a longer tail here, because for that goal the
        # Rasayana IS the treatment and the Shodhana was the preparation.
        _RASAYANA_TAIL = goal["rasayana_tail"]
        paschat_min = max(2, len(_stages))
        paschat_max = paschat_min + _RASAYANA_TAIL

        is_basti = pradhana["primary"] in ("basti", "basti_matra")
        deepana_needed = bool(
            eligibility.get("ama_correction_needed") or eligibility.get("agni_correction_needed")
        )
        # `ama_correction_first.duration_days` gives "3-7 days of Deepana-Pachana
        # herbs before starting Snehana". Mild and moderate Ama, and Manda Agni, take
        # the floor of that range; high and severe take the middle, because for them
        # the phase is not preparation that improves the result — it is the
        # precondition the Shodhana verdict is conditional on. On a long course the
        # proportional term raises both to the same number; the floors are what
        # separate them when the course is short.
        deepana_min = (5 if eligibility.get("ama_correction_mandatory") else 3) if deepana_needed else 0
        purva_min = 2

        floor = deepana_min + purva_min + 1 + paschat_min
        if total_days < floor:
            duration_notice = (
                f"Extended from {requested_days} to {floor} days. "
                + (f"Deepana-Pachana needs {deepana_min} days, " if deepana_needed else "")
                + f"Purvakarma at least {purva_min}, the Karma its own day, and Samsarjana Krama "
                f"{paschat_min} — its re-entry has {paschat_min} stages and cannot be delivered in "
                "fewer. Compressing any of them is what causes post-Shodhana complications."
            )
            total_days = floor

        if deepana_needed:
            # The floor is the same number the phase was costed at above. Hardcoding
            # 3 here while the floor said 5 would have reserved five days for the
            # phase and then scheduled three of them.
            deepana_days = min(max(deepana_min, min(7, int(total_days * 0.25))),
                               total_days - (floor - deepana_min))

        shodhana_days = total_days - deepana_days
        purva_days = max(purva_min, _purvakarma_days(vikriti_dom, shodhana_days, protocols))

        budget = shodhana_days - purva_days

        # The Basti subtype is chosen from the days actually available, and then the
        # phase is exactly as long as the subtype it names. Picking the subtype from
        # an unbounded budget and clipping the phase afterwards produced an 11-day
        # course labelled "Kala Basti (16-Basti Schedule)" — the card and the calendar
        # disagreeing for the third time in this file.
        if is_basti:
            basti_info = _basti_subtype(karma_setting, max(1, budget - paschat_min))
            pradhana_days = basti_info["days"]
        else:
            basti_info = None
            karma_natural = 5 if pradhana["primary"] == "nasya" else 1
            pradhana_days = max(1, min(karma_natural, budget - paschat_min))
        paschat_days  = max(paschat_min, min(budget - pradhana_days, paschat_max))

        # The phases sum to the course length; the request does not set it. Both
        # directions must be reported — the requested figure was previously printed
        # on the card whichever way the schedule had actually gone.
        natural_total = deepana_days + purva_days + pradhana_days + paschat_days
        if natural_total < total_days:
            duration_notice = (
                f"This course runs {natural_total} days, not the {requested_days} you have available. "
                f"{(pradhana['primary'] or '').replace('_', ' ').title()} takes {pradhana_days} "
                f"day{'s' if pradhana_days != 1 else ''}, and Purvakarma and Samsarjana Krama have "
                "classical lengths that padding would not improve. Continue the Rasayana afterwards — "
                "it is meant to run for months, well past the end of this plan."
            )
        elif natural_total > total_days:
            # The phases named have to account for the days added. Deepana-Pachana
            # was left out of this breakdown, so a patient who asked for 3 days and
            # was extended to 14 read "Purvakarma 3, Virechana 1, Samsarjana 5" and
            # was five days short of the number in the same sentence. High Ama makes
            # that phase the largest single addition, so the gap is now the rule.
            duration_notice = (
                f"Extended from {requested_days} to {natural_total} days. "
                + (f"Deepana-Pachana needs {deepana_days} to clear Ama before Snehana, "
                   if deepana_days else "")
                + f"Purvakarma needs {purva_days} for your Vikriti, "
                f"{(pradhana['primary'] or '').replace('_', ' ').title()} needs {pradhana_days}, "
                f"and the Samsarjana Krama re-entry has {paschat_min} stages. "
                "Compressing any of them is what causes post-Shodhana complications."
            )
        total_days = natural_total

    # Koshtha: check user_profile first, then pk_prefs (PreferencesModal asks it for PK context)
    koshtha = user_profile.get("koshtha") or pk_prefs.get("koshtha") or "sama"

    # ── Aushadha & Samsarjana ─────────────────────────────────────────────────
    aushadha = _select_aushadha(
        vikriti_dom, medical_history, pradhana["primary"] or "shamana", karma_setting, protocols,
        koshtha, gender=(user_profile.get("gender") or None), bala=bala_type,
        medications=(user_profile.get("current_medications") or []),
        pregnancy=bool(user_profile.get("pregnancy_or_nursing")),
        existing_ayurvedic=(pk_prefs.get("current_ayurvedic_medicines") or []),
    )

    # `access_to_ayurvedic_herbs` reached the therapy pool and stopped there. Every
    # Pradhana row the KB marks `specific_ayurvedic` is clinician-administered and
    # every home Karma row is `readily_available`, so the answer never costs the
    # patient the cleanse itself — which is why it is not an eligibility input. What
    # it does cost them is the compendium: Madanaphala Phanta, Brahmi Ghrita and
    # Dashamoola Kashayam were named to a patient who had just said they cannot
    # obtain Ayurvedic formulations, with nothing in the plan acknowledging it.
    #
    # Named, not withheld. Substituting on a procurement answer would change the
    # drug for a non-clinical reason, and the compendium's entries are chosen for
    # the Dosha, the Koshtha and the Bala; a patient who finds a supplier after all
    # should receive the formulation their profile actually indicates.
    procurement_notice = None
    if pk_prefs.get("access_to_ayurvedic_herbs") == "no":
        named = sorted({
            v["name"] for v in aushadha.values()
            if isinstance(v, dict) and v.get("name")
        })
        if named:
            procurement_notice = (
                "You have said you cannot obtain specific Ayurvedic formulations. This plan "
                f"still names {', '.join(named)}, because they are what your Vikriti and Koshtha "
                "indicate and substituting on availability would change the medicine for a reason "
                "that is not clinical. "
                + ("The clinic supplies the ones used during your therapies; the Rasayana "
                   "continues at home for months after this plan ends, so that one you will need "
                   "to source." if karma_setting == "clinic" else
                   "You will need to source these, or ask a Vaidya for a substitution — do not "
                   "begin the Karma without the drug it calls for.")
            )

    # Every Aushadha gate — the herb table, the therapy contraindications, the
    # per-Karma matrix — matches CONDITION TOKENS. An unmapped condition matches
    # none of them, so it passes all of them: a Wilson's disease patient (copper
    # accumulation) clears the Shilajit check because "wilsons_disease" is not a
    # token any entry lists, and a Sjögren's patient clears Ashwagandha's autoimmune
    # caution because the caution is keyed on "autoimmune". The gate did not decide
    # they were safe; it never saw them.
    #
    # Saying so is the honest output. Withholding every medicine on an unrecognised
    # word would strip the plan for a large, ordinary set of diagnoses, and claiming
    # a clean check is worse than either.
    if unmapped_conditions:
        aushadha["unverified_against"] = {
            "conditions": unmapped_conditions,
            "notice": (
                f"The medicines above were selected for your Vikriti and your recognised "
                f"conditions. They have NOT been checked against "
                f"{', '.join(unmapped_conditions)} — that diagnosis is outside this "
                "formulary's vocabulary, so every contraindication check passed it by "
                "default rather than clearing it. Confirm each medicine with a Vaidya "
                "before taking any of them."
            ),
        }
    # Samsarjana Krama is the graded re-entry from a Shodhana-emptied Koshtha. With
    # no Shodhana there is nothing to re-enter from, and printing its stages would
    # put a mono-diet ladder in a plan whose whole purpose is to stop depleting.
    samsarjana = [] if is_shamana else _samsarjana_krama(pradhana["primary"], protocols)

    # The Samsarjana ladder is the strictest diet in the feature — post-Vamana it
    # opens on Peya, rice boiled at 1:14 and strained. `diet_adherence_ability` was
    # read only by the therapy pool, so a patient who answered "lifestyle changes
    # only" had the Kitchari mono-diet withheld from their rotating therapies and
    # was handed the seven-stage ladder anyway, unremarked.
    #
    # Where the Karma is clinician-administered the ladder is too, and the answer
    # describes nothing the patient has to arrange — but it is still an answer they
    # gave, and a plan that neither honours it nor mentions it reads as though the
    # question was never asked.
    samsarjana_notice = None
    if samsarjana and _DIET_RANK.get(pk_prefs.get("diet_adherence_ability", "partial"), 1) < 2:
        who = ("These meals are prepared and served by the clinic — this phase is administered, "
               "not self-managed." if karma_setting == "clinic" else
               "You prepare these yourself, and the stages are the treatment.")
        samsarjana_notice = (
            f"You have told us your dietary adherence is "
            f"'{pk_prefs.get('diet_adherence_ability', 'partial').replace('_', ' ')}'. {who} "
            "The Samsarjana Krama is not the negotiable part of a Panchakarma: Agni is at its "
            "weakest in the days straight after purification, and returning to ordinary food "
            "before the ladder is finished is the specific thing that causes the complications "
            "the phase exists to prevent. If you cannot commit to it, say so before the Karma "
            "day rather than during the re-entry."
        )

    # ── Snehana Protocol ──────────────────────────────────────────────────────
    snehana_int = (
        protocols.get("purvakarma_protocols", {})
        .get("snehana", {}).get("types", {}).get("internal", {})
    )
    snehana_ext = (
        protocols.get("purvakarma_protocols", {})
        .get("snehana", {}).get("types", {}).get("external", {})
    )

    # Dose schedule clipped to actual Purvakarma days. Empty under Shamana: the
    # escalating ladder is Shodhanartha Sneha, given to liquefy Doshas so they can
    # be expelled. In a plan with no expulsion step it mobilises them with nowhere
    # to go. Shamana-matra Sneha replaces it (see shamana_protocol.shamana_chikitsa).
    dose_schedule = [] if is_shamana else snehana_int.get("dose_schedule", [])[:purva_days]
    # Kapha: classical Avara Snehana — max 60ml; avoid heavy oleation for already-heavy Kapha
    # Sarshapa Taila (mustard oil) or Trikatu-infused Ghrita preferred over plain Ghrita
    if vikriti_dom == "kapha":
        dose_schedule = [
            {**d, "dose_ml": min(d.get("dose_ml", 30), 60),
             "time": d.get("time", "Empty stomach at sunrise"),
             "vehicle": "Warm ginger water (Kapha: avoid plain warm water — use Ushna Dravya)"}
            for d in dose_schedule
        ]
    # The ladder is meant to end on a reduced dose — the KB's day 7 reads "Reduce
    # dose on final day", halving the 120ml peak to 60. Slicing the first N entries
    # dropped that step whenever the course was shorter than seven days, handing the
    # patient from a climbing dose straight into the Karma.
    #
    # Only from three days up: a two-day course has no plateau to step down from,
    # and forcing one there flattens the ladder to 30ml twice, which is not oleation
    # at all — worse than the missing step-down it was meant to fix.
    if len(dose_schedule) >= 3:
        peak = max(d["dose_ml"] for d in dose_schedule)
        dose_schedule = dose_schedule[:-1] + [{
            **dose_schedule[-1],
            "dose_ml": max(30, peak // 2),
            "time": "Reduce dose on final day",
        }]

    # Snehapana is titrated to Samyak Snigdha lakshana, not to a day count. When the
    # course is shorter than classical for this Vikriti, that gap has to reach the
    # patient: inadequate Snehana before Shodhana is the textbook cause of
    # post-Shodhana complications, and `purvakarma_classical_snehana_days` reported
    # the classical figure as a bare number beside a phase half its length — a card
    # reading 7 above a two-day schedule.
    classical_snehana = snehana_int.get("duration_by_prakriti", {}).get(vikriti_dom, 5)
    snehana_truncated = bool(dose_schedule) and purva_days < classical_snehana
    snehana_adequacy = {
        "classical_days":  classical_snehana,
        "scheduled_days":  purva_days if not is_shamana else 0,
        "truncated":       snehana_truncated,
        "signs":           snehana_int.get("signs_adequate_snehana", []),
        "instruction": (
            (
                f"This course schedules {purva_days} days of Snehapana; {classical_snehana} is "
                f"classical for {vikriti_dom.title()} Vikriti. Snehapana is judged by the signs "
                "of Samyak Snigdha, never by the calendar — do not proceed to the main Karma "
                "until they are present. If they are not, extend Snehana and move the Karma back "
                "by the same number of days. Proceeding without adequate oleation is the "
                "textbook cause of post-Shodhana complications."
            ) if snehana_truncated else (
                "Confirm the signs of Samyak Snigdha before the main Karma. Snehapana is judged "
                "by the signs, not by the calendar — if they are absent on the last scheduled "
                "day, extend Snehana and move the Karma back with it."
            )
        ) if dose_schedule else "",
    }
    if snehana_truncated:
        safety_warnings.append(
            f"SNEHANA SHORTER THAN CLASSICAL: {purva_days} days scheduled vs "
            f"{classical_snehana} for {vikriti_dom.title()} Vikriti — confirm Samyak Snigdha "
            "lakshana before the Karma, and extend if absent."
        )

    # Dosha-specific Snehana oil
    snehana_oils = snehana_int.get("oleation_agents_by_dosha", {}).get(
        vikriti_dom, snehana_int.get("oleation_agents_by_dosha", {}).get("vata", {})
    )
    abhyanga_oils = snehana_ext.get("oils_by_dosha", {}).get(
        vikriti_dom, snehana_ext.get("oils_by_dosha", {}).get("vata", {})
    )

    # ── Daily Schedule Assembly ───────────────────────────────────────────────
    shamana_build: dict = {}
    if is_shamana:
        shamana_build = _build_shamana_plan(
            user_profile, pk_prefs, protocols, pkt, eligibility, vikriti_dom, aushadha, total_days,
            triage_doshas,
        )
        schedule = shamana_build["schedule"]
        phases   = shamana_build["phases"]
        sd       = shamana_build["days"]
        purva_days, pradhana_days, paschat_days = 0, 0, sd["brimhana"]
    else:
        purva_pool   = filter_and_score_therapies(user_profile, pk_prefs, "purvakarma", pkt,
                                                  vikriti_dom, triage_doshas)
        paschat_pool = filter_and_score_therapies(user_profile, pk_prefs, "paschat",    pkt,
                                                  vikriti_dom, triage_doshas)
        # No `pradhana` pool: that phase's content is the pinned Karma action, and
        # drawing a pool for it is what let an empty pool delete the cleanse day.

        schedule = []
        phases = []
        offset = 1
        if deepana_days:
            # Snehana is what Deepana-Pachana precedes ("3-7 days ... before starting
            # Snehana"), so the oleation rows cannot appear inside the phase that
            # exists to come first. Oiling an Ama-laden Srotas is the specific error.
            deepana_pool = [t for t in purva_pool if t["id"] not in _DEEPANA_EXCLUDED_THERAPIES]
            schedule.extend(_assemble_rotating_phase(
                deepana_pool, deepana_days, offset, "Deepana-Pachana (Agni Correction)",
                pinned=_deepana_pachana_action(eligibility, protocols),
            ))
            phases.append({"key": "deepana_pachana", "label": "Deepana-Pachana",
                           "sub": "Kindle Agni, digest Ama — before Snehana", "days": deepana_days})
            offset += deepana_days

        purva_start   = offset
        pradhana_start = offset + purva_days
        paschat_start  = offset + purva_days + pradhana_days

        # Purvakarma is Snehana + Swedana every day, in that order — Swedana after
        # Abhyanga is what opens the Srotas the oil has loosened (CS Sutrasthana 14).
        # Taking pool[0] and pool[1] gave the two highest-scoring rows, which for a
        # Vata patient were both Abhyanga: two oil massages a day and no sudation at
        # all, in the phase whose definition is the pair.
        purva_abhyanga = next((t for t in purva_pool if "abhyanga" in t["id"]), None)
        purva_swedana  = next((t for t in purva_pool if "sweda" in t["id"]), None)
        purva_extras   = [t for t in purva_pool if t not in (purva_abhyanga, purva_swedana)]
        schedule.extend(assemble_phase(
            [t for t in (purva_abhyanga, purva_swedana) if t] or purva_pool,
            purva_days, purva_start, "Purvakarma (Preparation)",
            always_both=True,
        ))
        # Shirodhara, Udvartana and the like rotate on top rather than displacing
        # the pair — they are adjuncts to Purvakarma, not substitutes for it.
        #
        # A therapy the goal weights heavily is the reason the patient chose that
        # goal, so it runs every day rather than taking its turn in the rotation:
        # Shirodhara once in five days is not a stress-relief protocol, it is a
        # stress-relief mention.
        _GOAL_DAILY_THRESHOLD = 4
        goal_daily = next(
            (t for t in purva_extras if goal["boost"].get(t["id"], 0) >= _GOAL_DAILY_THRESHOLD),
            None,
        )
        rotating = [t for t in purva_extras if t is not goal_daily]
        if purva_extras:
            for i, day_entry in enumerate(d for d in schedule if "Purvakarma" in d.get("phase", "")):
                if goal_daily:
                    day_entry["therapies"].append(_therapy_row(goal_daily, core=True))
                if rotating:
                    day_entry["therapies"].append(_therapy_row(rotating[i % len(rotating)]))

        # The Pradhana phase is built from its day count, never from pool
        # availability. Its content is the pinned Karma action, and the pool only
        # ever supplied supporting rows that the pinning replaces — but
        # `assemble_phase` returns nothing for an empty pool, so the Karma DAY
        # disappeared while the phase strip above still claimed it.
        #
        # `detox_experience: "none"` is the schema default and empties the clinic
        # Pradhana pool (every clinical Karma row requires prior experience), so the
        # commonest profile in the product got a plan that skipped from Day 5 to
        # Day 7 with the cleanse itself missing and no indication anything was gone.
        schedule.extend(
            {"day": pradhana_start + i, "phase": "Pradhana Karma (Main Cleanse)", "therapies": []}
            for i in range(pradhana_days)
        )

        # Samsarjana rows are dropped from the Paschat pool because the staged action
        # below replaces them; leaving them in meant the phase had nothing else and
        # the days after the stages ran out were empty.
        paschat_rest = [t for t in paschat_pool if not t["id"].startswith("samsarjana")]
        schedule.extend(_assemble_rotating_phase(
            paschat_rest, paschat_days, paschat_start, "Paschat Karma (Rejuvenation)"))

        # Purvakarma: the Snehapana dose escalates 30 → 60 → 90 → 120ml and steps
        # back down on the last day. The plan carried that ladder in a summary block
        # while every Purvakarma day on the calendar read the same, so the day a
        # patient was on told them nothing about the dose they were due.
        for i, day_entry in enumerate(d for d in schedule if "Purvakarma" in d.get("phase", "")):
            if i < len(dose_schedule):
                day_entry["snehapana"] = dose_schedule[i]
            day_entry["snehana_signs"] = snehana_int.get("signs_adequate_snehana", [])

        # The pinned action IS the Pradhana Karma, fully described. The therapy pool
        # holds a row for every Karma in the KB and was never filtered by the one
        # selected, so a Virechana day also listed "Clinical Nasya", and a patient
        # whose Virechana had been withheld for low Ojas still had "Virechana
        # (Clinical Purgation)" on the calendar beside the Nasya that replaced it.
        # A substitution that leaves the original on the schedule is not a substitution.
        #
        # Basti is the one Karma that runs for days rather than one, and its days are
        # not interchangeable: the course alternates oil and decoction to a pattern
        # the KB authors day by day. One pinned action repeated across it produced
        # eight identical Niruha days under a card promising three.
        pradhana_entries = [d for d in schedule if "Pradhana" in d.get("phase", "")]
        if pradhana["primary"] in ("basti", "basti_matra") and basti_info:
            basti_sequence = _basti_sequence(basti_info["subtype"], pradhana_days, protocols)
            basti_info = {**basti_info, "sequence": basti_sequence}
            for i, day_entry in enumerate(pradhana_entries):
                if pradhana["primary"] == "basti_matra":
                    # Matra Basti is a single repeated oil administration by design —
                    # no Niruha, nothing to alternate. Its day action is already right.
                    day_entry["therapies"] = [_pradhana_day_action(
                        pradhana["primary"], aushadha, basti_info, karma_setting, ritu_ctx.get("ritu", ""))]
                else:
                    day_entry["therapies"] = [
                        _basti_day_action(i, basti_sequence, aushadha, basti_info, protocols)
                    ]
        else:
            pk_action = _pradhana_day_action(pradhana["primary"], aushadha, basti_info, karma_setting, ritu_ctx.get("ritu", ""))
            if pk_action:
                for day_entry in pradhana_entries:
                    day_entry["therapies"] = [pk_action]

        # Paschat: Samsarjana Krama is graded — Peya → Vilepi → Yusha → rice. The
        # stages were computed and then a row named "Strict Samsarjana Krama" was
        # scheduled identically on every day of the phase. The grading is the entire
        # clinical content; a flat repeat of the name carries none of it.
        # Once the stages are exhausted the phase is Rasayana, not a fourth day of
        # "Stage 3". `rasayana_integration.timing` puts Rasayana at day 3-5 after the
        # Karma, which is exactly where the ladder ends.
        for i, day_entry in enumerate(d for d in schedule if "Paschat" in d.get("phase", "")):
            if samsarjana and i < len(samsarjana):
                pinned = _samsarjana_day_action(i, samsarjana, paschat_days)
            else:
                pinned = _brimhana_action(vikriti_dom, aushadha)
            if pinned:
                day_entry["therapies"].insert(0, pinned)

        phases += [
            {"key": "purvakarma", "label": "Purvakarma",
             "sub": "Snehana + Swedana (Preparation)", "days": purva_days},
            {"key": "pradhana", "label": "Pradhana Karma",
             "sub": (pradhana["primary"] or "").replace("_", " "), "days": pradhana_days},
            {"key": "paschat", "label": "Paschat Karma",
             "sub": "Samsarjana Krama + Rasayana", "days": paschat_days},
        ]

    time_dropped = _trim_day_to_time_budget(schedule, pk_prefs, pkt)
    if time_dropped:
        goal_notes.append(
            f"Trimmed to your {pk_prefs.get('self_care_time_per_day', '30 min')} daily self-care "
            f"budget: {', '.join(time_dropped)} left out. Raise the budget to include them — "
            "clinic-administered therapies are unaffected."
        )

    # ── Ritu Compatibility Warning ────────────────────────────────────────────
    # Only meaningful when a Karma was selected; the Ritu calendar schedules
    # Shodhana, and a Shamana plan performs none.
    pk_primary = pradhana["primary"]
    ritu_avoid = ritu_ctx.get("avoid", [])
    ritu_warning = None
    if pk_primary and any(pk_primary in a for a in ritu_avoid):
        ritu_warning = (
            f"⚠ {pk_primary.title()} is not ideal in {ritu_ctx.get('ritu_name', ritu_ctx.get('ritu', ''))}. "
            f"Preferred therapy this season: {ritu_ctx.get('primary_shodhana', 'virechana').title()}. "
            f"Proceed with extra caution and increased Purvakarma."
        )

    return {
        "plan_id": f"pk_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        # ── Classical clinical decisions (new) ────────────────────────────────
        "clinical_decisions": {
            "vikriti_dominant":       vikriti_dom,
            "vikriti_secondary":      vikriti_sec,
            "shodhana_or_shamana":    eligibility,
            "ritu_context":           ritu_ctx,
            "ritu_warning":           ritu_warning,
            "pradhana_karma_selected": pradhana,
            "basti_subtype":          basti_info,
            "safety_warnings":        safety_warnings,
            "deferral":               deferral,
            "goal":                   {"id": goal["goal"], "label": goal["label"], "notes": goal_notes},
            "unmapped_conditions":    unmapped_conditions,
            "condition_triage":       triage["assessed"],
            # Which unrecognised diagnoses actually steered the therapy pool, and
            # by how much. A signal that changes the plan and is not stated is a
            # signal nobody can argue with — and this one is AI-derived.
            "triage_dosha_influence": [
                {"condition": c, "dosha": d, "effect": "therapy pool re-ranked toward "
                 f"{d.title()}-pacifying therapies (below your assessed Vikriti)",
                 "source": "llm_triage", "reviewed": False}
                for c, d in triage_doshas
            ],
            "vaidya_review_required": vaidya_review_required,
        },

        # ── Phase breakdown ───────────────────────────────────────────────────
        # `phases` is the authoritative ordered list — the Shamana arm has three
        # differently named phases, and the three fixed *_days keys below cannot
        # describe them. They are kept for the callers that still read them.
        "phase_breakdown": {
            "phases":                          phases,
            "deepana_pachana_days":            deepana_days,
            "duration_notice":                 duration_notice,
            "purvakarma_days":                 purva_days,
            "purvakarma_classical_snehana_days": snehana_int.get("duration_by_prakriti", {}).get(vikriti_dom, 5),
            "pradhana_karma_days":             pradhana_days,
            "paschat_karma_days":              paschat_days,
            "total_days":                      total_days,
        },

        # ── Snehana (Purvakarma) protocol ─────────────────────────────────────
        "snehana_protocol": {
            "internal_ghrita":    snehana_oils,
            "dose_schedule":      dose_schedule,
            "signs_adequate":     snehana_int.get("signs_adequate_snehana", []),
            "diet_during":        snehana_int.get("diet_during_snehana", ""),
            "abhyanga_oil":       abhyanga_oils,
            "abhyanga_technique": snehana_ext.get("technique", ""),
            "adequacy":           snehana_adequacy,
        },

        # ── Shamana arm detail (present only when Shodhana is withheld) ───────
        "shamana_protocol": shamana_build.get("protocol") if is_shamana else None,

        # ── Aushadha (medicines/oils) ─────────────────────────────────────────
        "aushadha": aushadha,
        "procurement_notice": procurement_notice,

        # ── Post-PK dietary re-entry ──────────────────────────────────────────
        "samsarjana_krama": samsarjana,
        "samsarjana_notice": samsarjana_notice,

        # ── Daily therapy schedule ────────────────────────────────────────────
        "daily_schedule": schedule,

        # ── User context ──────────────────────────────────────────────────────
        "user_summary": {
            "vikriti_dominant":  vikriti_dom,
            "vikriti_secondary": vikriti_sec,
            "agni_type":         agni_type,
            "agni_name":         agni_name,
            "bala":              bala_type,
            "bala_note":         bala_note,
            "ama_indicator":     user_profile.get("ama_indicator", "none"),
            "ojas_level":        user_profile.get("ojas_level", "medium"),
            "koshtha":           koshtha,
            "setting":           setting,
            "experience":        pk_prefs.get("detox_experience", "none"),
            "duration_days":     total_days,
            "goal":              pk_prefs.get("panchakarma_goal", "detox"),
        },

        "disclaimer": (
            "SHAMANA PROTOCOL: Shodhana is withheld — see the reasons above. This plan contains "
            "no Vamana, Virechana, Basti, Nasya or Raktamokshana at any strength. Re-assess with a "
            "qualified Vaidya (BAMS/MD Ayurveda) before considering purification."
            if is_shamana else
            "HOME PROTOCOL: Full Shodhana (Vamana, Niruha Basti) requires clinical supervision. "
            "This plan uses safe home adaptations (Matra Basti, mild Virechana, Pratimarsha Nasya)."
            if setting == "home" else
            "CLINIC PROTOCOL: To be administered under a qualified Vaidya (BAMS/MD Ayurveda)."
        ),
        "enriched": False,
    }
