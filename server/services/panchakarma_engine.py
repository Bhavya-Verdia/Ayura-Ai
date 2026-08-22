import json
from datetime import datetime, timezone
from pathlib import Path

from engine.condition_vocab import term_in_condition

BASE_DIR = Path(__file__).resolve().parent.parent
THERAPIES_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_therapies.json"
PROTOCOLS_PATH = BASE_DIR / "data" / "knowledge_base" / "panchakarma_protocols.json"

pk_therapies: list[dict] = []
pk_protocols: dict = {}

if THERAPIES_PATH.exists():
    with open(THERAPIES_PATH, "r", encoding="utf-8") as _f:
        pk_therapies = json.load(_f)

if PROTOCOLS_PATH.exists():
    with open(PROTOCOLS_PATH, "r", encoding="utf-8") as _f:
        pk_protocols = json.load(_f)


# ── Ritu (Season) ─────────────────────────────────────────────────────────────

def _current_ritu() -> str:
    month = datetime.now().month
    if month in (1, 2):  return "shishira"
    if month in (3, 4):  return "vasanta"
    if month in (5, 6):  return "grishma"
    if month in (7, 8):  return "varsha"
    if month in (9, 10): return "sharad"
    return "hemanta"


def _get_ritu_context(protocols: dict) -> dict:
    ritu = _current_ritu()
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
    # High or Severe Ama: Shodhana drives Ama deeper into Srotas (CS Sutrasthana 15)
    if ama in ("high", "severe"):
        blocking.append("High Ama present — Deepana-Pachana must precede Shodhana; Ama must be cleared first")

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
            "ama_correction_herbs": ama_info.get("herbs", []),
            "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
            "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
        }

    needs_ama = ama in ("mild", "moderate")

    if setting == "home" or restricting:
        reasons = list(restricting)
        if setting == "home":
            reasons.append(
                "Home setting — full Shodhana (Vamana / Niruha Basti) requires Vaidya supervision. "
                "Mridu (mild) Shodhana applied per the classical home protocol."
            )
        if needs_ama or agni_correction_needed:
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
            "ama_correction_herbs": ama_info.get("herbs", []) if needs_ama else [],
            "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
            "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
        }

    shodhana_reasons = ["Patient meets all Shodhana eligibility criteria (CS Sutrasthana 15)"]
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
        "ama_correction_herbs": ama_info.get("herbs", []) if needs_ama else [],
        "ama_correction_duration": ama_info.get("duration_days", "3–7 days"),
        "ama_correction_signs": ama_info.get("signs_ama_cleared", []),
    }


# ── Per-Karma Safety Matrix ───────────────────────────────────────────────────
# Classical absolute contraindications per Pradhana Karma.
# "hard" = substitute to safer karma. "soft" = warn but allow with modification.
_KARMA_CONTRAINDICATIONS: dict[str, dict[str, set[str]]] = {
    "vamana": {
        "hard": {
            "epilepsy", "severe_cardiac", "heart_disease", "heart_failure",
            "atrial_fibrillation", "bleeding_disorder", "hemophilia",
            "esophageal", "hiatal_hernia", "abdominal_surgery_recent",
        },
        "soft": {
            "hypertension",   # use very mild Madanaphala dose
            "anxiety", "ptsd",  # psychological fragility — pre-Shodhana Sattvavajaya needed
            "underweight",    # Atidurbala risk
        },
        "fallback": "nasya",  # substitute when hard contraindicated
        "fallback_reason": "Vamana contraindicated — Pratimarsha Nasya + mild Virechana substituted",
    },
    "virechana": {
        "hard": {
            "ulcerative_colitis", "ibd_crohns", "rectal_bleeding",
            "bleeding_disorder", "anemia", "hemorrhoids",
            "liver_failure", "hepatitis_chronic",  # damaged liver can't handle purgatives
        },
        "soft": {
            "liver_disease", "fatty_liver",   # use very mild Triphala only
            "hypertension",                   # avoid strong purgatives
            "diabetes_type1",                 # monitor glucose carefully
        },
        "fallback": "basti",
        "fallback_reason": "Virechana contraindicated — Basti (enema route) substituted to avoid GI stress",
    },
    "basti": {
        "hard": {
            "active_fever", "rectal_bleeding", "ulcerative_colitis",
            "ibd_crohns", "rectal_prolapse", "severe_ascites",
        },
        "soft": {
            "diabetes_type1",           # monitor glucose; use oil Anuvasana only
            "chronic_kidney_disease",   # Matra Basti only — avoid Niruha
        },
        "fallback": "nasya",
        "fallback_reason": "Basti contraindicated — Nasya + Shamana substituted",
    },
    "nasya": {
        "hard": set(),  # very few absolute contraindications
        "soft": {"acute_sinusitis", "active_fever"},
        "fallback": "nasya",
        "fallback_reason": "",
    },
    "raktamokshana": {
        "hard": {"anemia", "bleeding_disorder", "hemophilia", "anticoagulants"},
        "soft": {"hypertension"},
        "fallback": "virechana",
        "fallback_reason": "Raktamokshana contraindicated — Virechana (blood-purifying Tikta Ghrita) substituted",
    },
}


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


def _validate_karma_safety(pradhana: dict, medical_history: list[str]) -> dict:
    """
    Post-selection safety gate: checks if chosen Pradhana Karma is contraindicated
    by the user's medical conditions. Hard contraindications trigger substitution.
    Ref: CS Kalpasthana 12, Siddhisthana 1.
    """
    primary = pradhana.get("primary", "virechana")
    karma_key = "basti" if primary == "basti_matra" else primary
    contra = _KARMA_CONTRAINDICATIONS.get(karma_key, {})
    hard_set = contra.get("hard", set())
    soft_set = contra.get("soft", set())

    hard_flagged = [m for m in medical_history if any(term_in_condition(m, k) for k in hard_set)]
    soft_flagged = [m for m in medical_history if any(term_in_condition(m, k) for k in soft_set)]

    warnings: list[str] = []

    if hard_flagged:
        fallback = contra.get("fallback", "nasya")
        fallback_reason = contra.get("fallback_reason", "Therapy substituted due to contraindication")
        old_primary = pradhana["primary"]
        pradhana = {
            **pradhana,
            "primary": fallback,
            "reason": (
                f"⚠ {old_primary.title()} CONTRAINDICATED: {', '.join(hard_flagged)}. "
                f"{fallback_reason}."
            ),
            "safety_substitution": True,
            "original_karma": old_primary,
        }
        warnings.append(
            f"SAFETY SUBSTITUTION: {old_primary} → {fallback} "
            f"(contraindicated by: {', '.join(hard_flagged)})"
        )

    if soft_flagged:
        warnings.append(
            f"CAUTION: {', '.join(soft_flagged)} — modify dose/protocol per Vaidya guidance"
        )

    return pradhana, warnings


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
        return {
            "subtype": "matra_basti",
            "name": "Matra Basti (Home Oil Enema)",
            "days": min(8, available_days),
            "dose": "50–80 ml warm sesame oil or Bala Taila",
            "timing": "Night, after light dinner. Retain overnight.",
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

def _select_aushadha(
    vikriti_dom: str,
    medical_history: list[str],
    pradhana_karma: str,
    setting: str,
    protocols: dict,
    koshtha: str = "sama",
) -> dict:
    aus = protocols.get("aushadha_compendium", {})
    result: dict = {}

    # Abhyanga oil
    oils = aus.get("oils_external", [])
    result["abhyanga_oil"] = next(
        (o for o in oils if o.get("dosha") == vikriti_dom or vikriti_dom in o.get("dosha", "")),
        oils[0] if oils else {}
    )

    # Internal Snehana ghrita
    ghrita = aus.get("ghrita_internal", [])
    result["internal_ghrita"] = next(
        (g for g in ghrita if g.get("dosha") == vikriti_dom or vikriti_dom in g.get("dosha", "")),
        ghrita[0] if ghrita else {}
    )

    # Pradhana-specific Aushadha
    med_lower = [m.lower() for m in medical_history]

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
        result["pradhana_aushadha"] = next(
            (d for d in drugs if d.get("strength") == strength), drugs[-1] if drugs else {}
        )
        result["koshtha_virechana_note"] = _KOSHTHA_NOTES.get(koshtha, _KOSHTHA_NOTES["sama"])

    elif pradhana_karma == "vamana":
        vam = aus.get("vamana_drugs", [])
        result["pradhana_aushadha"] = vam[0] if vam else {}

    elif pradhana_karma in ("basti", "basti_matra"):
        kash = aus.get("kashayam_basti", [])
        if any("ankylos" in m or "spondyl" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Rasna Saptak + Bala Kashayam", "use": "Asthi-Majja Gata Vata — AS / Spondylosis"}
            result["basti_oil"]      = "Ksheerabala Taila — nourishes Asthi-Majja Dhatu"
        elif any("sciatica" in m or "neuropath" in m or "parkinson" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Bala + Dashamoola Kashayam", "use": "Neurological Vata disorders — Gridhrasi / Kampavata"}
            result["basti_oil"]      = "Mahanarayana Taila — penetrates Majja Dhatu, Vata Nadi Shodhana"
        elif any("arthritis" in m or "rheuma" in m or "joint" in m or "gout" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Dashamoola + Rasna + Eranda Kashayam", "use": "Amavata / Sandhivata / Vatarakta"}
            result["basti_oil"]      = "Ksheerabala Taila 101 — Sandhi (joint) Brimhana, Vata Shodhana"
        elif any("ibs" in m or "constipation" in m or "bloat" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Dashamoola + Bilva Kashayam", "use": "Grahani / Pakwashaya Vata — IBS, chronic constipation"}
            result["basti_oil"]      = "Tila Taila (sesame) — Pachana, Vata Anulomana"
        elif any("pcos" in m or "endometri" in m or "fibroid" in m or "dysmenorrh" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Dashamoola + Shatavari + Ashoka Kashayam", "use": "Artavavaha Srotas Shuddhi — gynaecological Vata-Kapha"}
            result["basti_oil"]      = "Shatavari Ghrita + Tila Taila — Artava Dhatu Brimhana"
        elif any("kidney" in m or "renal" in m or "uti" in m for m in med_lower):
            result["basti_kashayam"] = {"name": "Gokshura + Varuna Kashayam", "use": "Mutravaha Srotas — kidney / UTI Vata pacification"}
            result["basti_oil"]      = "Matra Basti — mild sesame oil only (Niruha avoided in renal disease)"
        else:
            result["basti_kashayam"] = kash[0] if kash else {"name": "Dashamoola Kashayam", "use": "General Vata Basti"}
            result["basti_oil"]      = "Tila Taila or Bala Taila — general Vata Basti"

    elif pradhana_karma == "nasya":
        if any("migraine" in m or "headache" in m or "sinus" in m for m in med_lower):
            result["nasya_oil"] = "Shadbindu Taila (Kapha/sinus) or Ksheerabala Taila 101 (Vata migraine)"
        elif any("anxiety" in m or "insomni" in m or "depression" in m or "ptsd" in m for m in med_lower):
            result["nasya_oil"] = "Brahmi Ghrita (Manovaha Srotas, Majja Dhatu nourishment) — 4–8 drops each nostril"
        elif any("hair" in m or "alopec" in m for m in med_lower):
            result["nasya_oil"] = "Bhringaraja + Ksheerabala Taila — Shiro Brimhana, Keshavardhana"
        else:
            nasya_map = {
                "vata":  "Anu Taila — lubricating, warming, Vata Anulomana",
                "pitta": "Brahmi Ghrita or Shatavari Ghrita — cooling, Pitta Shamana",
                "kapha": "Shadbindu Taila — stimulating, Kapha Sthana Shuddhi in head",
            }
            result["nasya_oil"] = nasya_map.get(vikriti_dom, "Anu Taila")

    # ── Disease-specific adjuvant Aushadha (Sahayoga Dravya) ─────────────────
    # Skin conditions — Kushtha group
    if any("psoriasis" in m or "eczema" in m or "urticaria" in m or "vitiligo" in m or "rosacea" in m or "acne" in m for m in med_lower):
        result["kushtha_aushadha"] = {
            "name": "Tikta Ghrita + Khadiradi Vati + Manjistha Churna",
            "use": "Rakta-Pitta Shuddhi (blood purification) — classical Kushtha Chikitsa",
            "classical_ref": "CS Chikitsa 7 — Tikta Ghrita for all Mahakushtha",
            "additional": "Nimbadi Churna 3g BD or Sariva (Hemidesmus) decoction 100ml AM"
        }
        result["skin_pathya"] = "Avoid incompatible foods (Viruddha Ahara). No milk+fish, no hot water after honey."

    # Metabolic conditions
    if any("diabetes" in m or "obesity" in m or "hypothyroid" in m or "cholesterol" in m or "metabolic" in m for m in med_lower):
        result["medovaha_aushadha"] = {
            "name": "Guduchi + Haridra + Amalaki (Triphala Churna) + Shilajit",
            "use": "Medovaha Srotas Shuddhi — Prameha / Sthoulya / Galaganda Chikitsa",
            "classical_ref": "CS Chikitsa 6 — Shilajit is Pramehaghna; Guduchi for Medhya + Tridoshahara",
            "dosage": "Triphala Churna 3g at bedtime with warm water; Guduchi Kwatha 30ml AM empty stomach"
        }

    # Gynaecological conditions
    if any("pcos" in m or "endometri" in m or "fibroid" in m or "dysmenorrh" in m or "amenorrh" in m or "menorrh" in m or "infertilit" in m for m in med_lower):
        result["artava_aushadha"] = {
            "name": "Shatavari + Ashoka Twak + Dashamoola + Shatapushpa",
            "use": "Artavavaha Srotas — Artava Dushti, Vata-Kapha Artava Vikara",
            "classical_ref": "CS Chikitsa 30 — Shatavari for Artava Kshaya; Ashoka for Raktasthambhana",
            "dosage": "Shatavari Kalpa 5g in warm milk BD; Dashamoola Kashayam 30ml before food"
        }

    # Mental health / Manovaha Srotas
    if any("anxiety" in m or "depression" in m or "ptsd" in m or "insomni" in m or "adhd" in m or "ocd" in m or "bipolar" in m for m in med_lower):
        result["manovaha_aushadha"] = {
            "name": "Brahmi + Ashwagandha + Jatamansi + Shankhpushpi",
            "use": "Manovaha Srotas Shuddhi — Vataja/Kaphaja Manas Vikara",
            "classical_ref": "CS Chikitsa 9 — Medhya Rasayana; AH Uttara 1 — Unmada Chikitsa",
            "dosage": "Brahmi Ghrita 5g with warm milk AM; Ashwagandha Churna 3g PM; Jatamansi decoction for sleep"
        }

    # Respiratory / Pranavaha Srotas
    if any("asthma" in m or "copd" in m or "bronchit" in m or "rhinit" in m or "sinusit" in m for m in med_lower):
        result["pranavaha_aushadha"] = {
            "name": "Vasaka + Kantakari + Sitopaladi Churna (Kapha) / Talisadi Churna (Vata-Kapha)",
            "use": "Pranavaha Srotas Shuddhi — Shwasa / Kasa / Pratishyaya Chikitsa",
            "classical_ref": "CS Chikitsa 17 — Vasaka for Kaphaja Shwasa; AH Chikitsa 3",
            "dosage": "Sitopaladi Churna 3g with honey TDS; Vasaka Swarasa 10ml AM; steam inhalation with Ajwain"
        }

    # Digestive / Hepatic conditions
    if any("ibs" in m or "liver" in m or "fatty" in m or "hepatit" in m or "peptic" in m or "ulcer" in m or "crohn" in m or "pancreat" in m for m in med_lower):
        result["annavaha_aushadha"] = {
            "name": "Kutaja + Bilva + Dadima + Amalaki + Guduchi Sattva",
            "use": "Annavaha / Purishavaha Srotas — Grahani / Yakrit Vikara Chikitsa",
            "classical_ref": "CS Chikitsa 15 — Kutaja is Grahi, Sangrahiya; Guduchi for Yakrit Shodhana",
            "dosage": "Kutajarishta 15ml after food BD; Guduchi Kwatha 30ml AM; Tikta Ghrita 5g before food for liver"
        }

    # Cardiovascular / Raktavaha Srotas
    if any("hypertension" in m or "heart" in m or "cardiac" in m or "varicose" in m or "cholesterol" in m for m in med_lower):
        result["raktavaha_aushadha"] = {
            "name": "Arjuna Twak Churna + Punarnava + Sarpagandha (for hypertension only if BP normal post-PK)",
            "use": "Raktavaha Srotas — Hridaya Roga, Rakta Dushti, Vata-Pitta Shonita Vikara",
            "classical_ref": "CS Chikitsa 26 — Arjuna Hridya; AH Chikitsa 6 — Punarnava Raktapitta",
            "caution": "Sarpagandha only under qualified Vaidya supervision; avoid in hypotension"
        }

    # Rasayana (post-PK)
    ras = protocols.get("paschat_karma", {}).get("rasayana_integration", {}).get("rasayana_by_condition", {})
    ras_key = {"vata": "vata_neurological", "pitta": "pitta_inflammatory", "kapha": "kapha_metabolic"}.get(vikriti_dom, "general_immunity")
    result["rasayana"] = ras.get(ras_key, ras.get("general_immunity", {}))

    return result


# ── Samsarjana Krama ──────────────────────────────────────────────────────────

def _samsarjana_krama(pradhana_karma: str, protocols: dict) -> list[dict]:
    """Post-PK dietary re-entry stages — different per Pradhana Karma type."""
    sk = protocols.get("paschat_karma", {}).get("samsarjana_krama", {})
    if pradhana_karma == "vamana":
        return sk.get("post_vamana", {}).get("stages", [])
    if pradhana_karma == "virechana":
        return sk.get("post_virechana", {}).get("stages", [])
    if pradhana_karma in ("basti", "basti_matra"):
        return sk.get("post_basti", {}).get("post_course", [])
    return sk.get("post_virechana", {}).get("stages", [])


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

_SHAMANA_BY_DOSHA = {
    "vata": {
        "principle": "Snigdha–Ushna Shamana — unctuous, warm, grounding. Vata is Ruksha, Sheeta and Chala; it is pacified by its opposites.",
        "sneha_matra": "Shamana-matra Sneha: 10–15 ml warm Tila Taila or Bala Taila with warm water, once daily before food. A pacifying dose — not the escalating Snehapana ladder, which prepares for an expulsion this plan does not perform.",
        "ahara": "Warm, moist, well-cooked, mildly oily. Madhura–Amla–Lavana Rasa. Moong dal khichdi with ghee, root vegetables, warm milk with nutmeg. Avoid raw salads, dried and frozen food, carbonated drinks.",
        "vihara": "Regular hours above all. Early sleep, no travel, no fasting, no vigorous exercise. Warm oil to the soles and scalp before bed.",
    },
    "pitta": {
        "principle": "Sheeta–Madhura–Tikta Shamana — cooling, sweet and bitter. Pitta is Ushna, Tikshna and Drava; it is pacified by cool and mild.",
        "sneha_matra": "Shamana-matra Sneha: 10 ml Tikta Ghrita or Shatavari Ghrita with warm water in the morning. A pacifying dose — not the escalating Snehapana ladder, which prepares for an expulsion this plan does not perform.",
        "ahara": "Cool to lukewarm, sweet, bitter and astringent. Rice, coconut, cucumber, coriander, sweet fruit, ghee. Avoid sour, fermented, salty, pungent, chilli, alcohol and the midday sun.",
        "vihara": "Cool the evening, not the day. Moonlight, cool baths, Sheetali pranayama. Avoid arguments, deadlines late at night, and exercise in heat.",
    },
    "kapha": {
        "principle": "Ruksha–Ushna–Laghu Shamana — drying, warming, light. Kapha is Guru, Snigdha and Sheeta; it is pacified by dry, warm and light.",
        "sneha_matra": "Shamana-matra Sneha: Kapha needs the least oleation. 5–10 ml Sarshapa Taila (mustard) or Trikatu-infused ghee, or omit internal Sneha entirely and keep only external Udvartana. Never the escalating Snehapana ladder.",
        "ahara": "Warm, dry, light, well-spiced. Barley, millet, steamed greens, ginger, black pepper, honey (never heated). Avoid dairy, wheat, sugar, cold drinks, curd and daytime sleep.",
        "vihara": "Movement is the medicine. Rise before sunrise, brisk walking, dry brushing before bathing, no daytime sleep at all.",
    },
}


def _deepana_pachana_action(elig: dict, protocols: dict) -> dict:
    """The pinned daily action for the Agni-correction phase."""
    herbs = elig.get("ama_correction_herbs") or (
        protocols.get("shodhana_eligibility", {})
        .get("ama_correction_first", {}).get("herbs", [])
    )
    ama_info = protocols.get("shodhana_eligibility", {}).get("ama_correction_first", {})
    signs = elig.get("ama_correction_signs") or ama_info.get("signs_ama_cleared", [])
    primary = herbs[0] if herbs else "Trikatu (Ginger + Black Pepper + Pippali)"
    return {
        "id": "deepana_pachana_main",
        "name": f"Deepana-Pachana — {primary}",
        "duration_minutes": None,
        "benefits": "Kindles Agni and digests Ama. Until Ama is digested no other therapy can reach the Dhatus.",
        "is_deepana_pachana": True,
        "timing": "Morning, empty stomach",
        "pradhana_notes": (
            f"{primary} on an empty stomach with warm water. "
            f"Alternatives if unavailable: {', '.join(herbs[1:3]) if len(herbs) > 1 else 'Chitrakadi Vati'}. "
            f"Diet: {ama_info.get('diet_during', 'Light, warm, easily digestible food. Avoid heavy, cold, raw and fermented.')} "
            f"Ama is cleared when: {'; '.join(signs) if signs else 'the tongue coating clears and appetite returns'}. "
            "Do not progress to the next phase before those signs appear — the days below are a guide, not a deadline."
        ),
    }


def _brimhana_action(vikriti_dom: str, aushadha: dict) -> dict:
    """The pinned daily action for the Brimhana (nourishing) phase."""
    ras = aushadha.get("rasayana") or {}
    herb = ras.get("herb", "Chyawanprash")
    dose = ras.get("dose", "1 tsp twice daily with warm milk")
    return {
        "id": "brimhana_main",
        "name": f"Brimhana Rasayana — {herb}",
        "duration_minutes": None,
        "benefits": "Rebuilds Dhatu and Ojas. This is the phase that makes a future Shodhana possible.",
        "is_brimhana": True,
        "timing": ras.get("timing", "Daily, with warm milk"),
        "pradhana_notes": (
            f"{herb} — {dose}. Continue for {ras.get('duration', '3 months')} beyond the end of this plan; "
            "Rasayana works over months, not days. "
            "Nourishing food, unhurried meals, sleep before 10pm, and no fasting of any kind. "
            "Re-assess Bala, Agni, Ama and Ojas with a Vaidya before considering Shodhana."
        ),
    }


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
            primary = pool[i % len(pool)]
            therapies.append({
                "id": primary["id"], "name": primary["name"],
                "duration_minutes": primary["duration_minutes"], "benefits": primary["benefits"],
            })
            if len(pool) > 1:
                secondary = pool[(i + 1) % len(pool)]
                therapies.append({
                    "id": secondary["id"], "name": secondary["name"],
                    "duration_minutes": secondary["duration_minutes"], "benefits": secondary["benefits"],
                })
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
            filter_and_score_therapies(user_profile, pk_prefs, "purvakarma", pkt, vikriti_dom)
            + filter_and_score_therapies(user_profile, pk_prefs, "paschat", pkt, vikriti_dom)
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

    sd = _SHAMANA_BY_DOSHA.get(vikriti_dom, _SHAMANA_BY_DOSHA["vata"])
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

def filter_and_score_therapies(user_profile, pk_prefs, phase, pk_therapies_list, vikriti_dom=None):
    scored = []
    dominant = vikriti_dom or user_profile.get("dominant_dosha", "vata") or "vata"
    setting   = pk_prefs.get("setting", "home")
    experience = pk_prefs.get("detox_experience", "none")
    herbs      = pk_prefs.get("access_to_ayurvedic_herbs", "willing_to_buy")
    diet_ab    = pk_prefs.get("diet_adherence_ability", "partial")
    time_str   = pk_prefs.get("self_care_time_per_day", "30 min")

    max_dur = 15 if "15" in time_str else 60 if "1" in time_str else 120 if "2" in time_str else 30

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
        if t["duration_minutes"] > max_dur and setting != "clinic": continue

        de = t.get("dosha_effect", {}).get(dominant, 0)
        score = 2 if de == -1 else 1 if de == 0 else -2
        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]


def _pradhana_day_action(pradhana_karma: str, aushadha: dict, basti_info: dict | None, setting: str, ritu: str = "") -> dict:
    """Builds a pinned 'main karma' action injected as the first therapy on every Pradhana day."""
    pk = pradhana_karma

    if pk == "virechana":
        drug = aushadha.get("pradhana_aushadha", {})
        drug_name = drug.get("name", "Virechana drug") if isinstance(drug, dict) else str(drug)
        dose      = drug.get("dose", "as directed") if isinstance(drug, dict) else ""
        kn        = aushadha.get("koshtha_virechana_note", "")
        notes = (
            f"Take {drug_name} ({dose}) in the evening after a light dinner. "
            "Stay home — purgation begins in 4–8 hours. Keep warm water available. "
            "Count Vegas (episodes): 5–10 for mild home Virechana; 20–30 for full clinical. "
            "After completion rest in supine position; sip warm water if thirsty."
        )
        if kn:
            notes += f" | Koshtha note: {kn}"
        if ritu == "grishma":
            notes += " | Grishma Ritu (Summer): Bala is reduced in summer heat — use mild dose only. Trivrit Churna is contraindicated; Eranda (castor oil) or Triphala only. Avoid vigorous Swedana on Virechana day."
        return {
            "id": "virechana_main",
            "name": f"Virechana — {drug_name}",
            "duration_minutes": None,
            "benefits": "Expels excess Pitta from Pakvashaya (colon). Clears Raktavaha and Pittavaha Srotas.",
            "is_pradhana_karma": True,
            "timing": "Evening — after light dinner",
            "pradhana_notes": notes,
        }

    if pk == "vamana":
        return {
            "id": "vamana_main",
            "name": "Vamana — Therapeutic Emesis",
            "duration_minutes": None,
            "benefits": "Expels accumulated Kapha from Amashaya (stomach). Clears Pranavaha and Annavaha Srotas.",
            "is_pradhana_karma": True,
            "timing": "Morning — under Vaidya supervision (clinic only)",
            "pradhana_notes": (
                "Performed by a qualified Vaidya. Morning, empty stomach, after Purvakarma is complete. "
                "Madanaphala Phanta administered. Patient drinks 6–8 glasses warm milk/sugarcane juice beforehand. "
                "Count Vegas: 8–12 for Samyak Yoga (adequate purification). "
                "Atiyoga (>12 Vegas or bleeding): stop immediately — give Ghrita + warm milk. "
                "Complete rest for 24 hours post-procedure."
            ),
        }

    if pk == "nasya":
        oil = aushadha.get("nasya_oil", "Anu Taila")
        oil_str = oil if isinstance(oil, str) else oil.get("name", "Anu Taila")
        return {
            "id": "nasya_main",
            "name": f"Navana Nasya — {oil_str}",
            "duration_minutes": 15,
            "benefits": "Clears Kapha and Vata from Urdhvanga (head, neck, sinuses). Reaches Manovaha Srotas via Sringataka Marma.",
            "is_pradhana_karma": True,
            "timing": "Morning — 30 min after face Abhyanga and steam",
            "pradhana_notes": (
                f"Warm face with steam or hot towel for 5 min. Lie supine, head tilted back slightly. "
                f"Administer 6–8 drops {oil_str} in each nostril. Sniff gently upward. "
                "Remain supine for 5 min. Spit out any drainage — do not swallow. "
                "Avoid eating for 30 min after. Repeat daily for all Nasya phase days."
            ),
        }

    if pk == "basti_matra":
        oil = aushadha.get("basti_oil", "Sesame oil (Tila Taila)")
        oil_str = oil if isinstance(oil, str) else "Sesame oil"
        return {
            "id": "basti_matra_main",
            "name": f"Matra Basti — {oil_str}",
            "duration_minutes": 10,
            "benefits": "Lubricates Pakwashaya, nourishes Vata-dominant Srotas. Safest home Basti — no forced expulsion.",
            "is_pradhana_karma": True,
            "timing": "Night — after light dinner",
            "pradhana_notes": (
                f"Night, after light dinner. Warm 50–80 ml {oil_str} to body temperature (38°C). "
                "Use enema bulb (Netra). Lie on left side. Administer slowly over 1–2 min. "
                "Remain lying — retain overnight if possible; oil is absorbed, no Vega (expulsion) needed. "
                "Repeat nightly for all Basti phase days."
            ),
        }

    if pk == "basti":
        kashayam = aushadha.get("basti_kashayam", {})
        oil      = aushadha.get("basti_oil", "Tila Taila")
        kash_name = kashayam.get("name", "Dashamoola Kashayam") if isinstance(kashayam, dict) else str(kashayam)
        oil_str   = oil if isinstance(oil, str) else "Tila Taila"
        bs_name   = (basti_info or {}).get("name", "Yoga Basti")
        bs_note   = (basti_info or {}).get("note", "")
        return {
            "id": "basti_main",
            "name": f"Basti — {bs_name}",
            "duration_minutes": 60,
            "benefits": "Vata Shodhana from Pakvashaya — the seat of Vata. Ardhachikitsa (half of all treatment for Vata).",
            "is_pradhana_karma": True,
            "timing": "Morning (Niruha) + Evening (Anuvasana) per Basti day schedule",
            "pradhana_notes": (
                f"{bs_name} ({bs_note}). "
                f"Niruha Basti (decoction): {kash_name} + {oil_str} + Madhu + Saindhava per classical formula. "
                "Administered by Vaidya — patient lies on left side, Netra inserted, enema given slowly. "
                "Retain 30–60 min; expulsion occurs naturally. Rest 1–2 hours post-Niruha. "
                f"Anuvasana Basti (oil): {oil_str} 60–120 ml same evening — retained overnight."
            ),
        }

    if pk == "raktamokshana":
        return {
            "id": "rakta_main",
            "name": "Raktamokshana — Blood Purification",
            "duration_minutes": 30,
            "benefits": "Purifies Rakta Dhatu — removes Pitta-Rakta vitiation from Raktavaha Srotas.",
            "is_pradhana_karma": True,
            "timing": "Morning — under Vaidya supervision",
            "pradhana_notes": (
                "Performed by qualified Vaidya. Jalaukavacharana (leech therapy) or Shringa (cupping) per indication. "
                "Morning, light stomach. Leeches applied to affected site; removed when engorged (20–30 min). "
                "Post-procedure: wash site with Haridra (turmeric) water; monitor 2 hours. "
                "Avoid sour/pungent food for 3 days post-procedure."
            ),
        }

    return {}


def assemble_phase(pool, target_days, start_day, phase_name):
    if not pool:
        return []
    primary   = pool[0]
    secondary = pool[1] if len(pool) > 1 else None
    schedule  = []
    for i in range(target_days):
        day_therapies = [{
            "id": primary["id"], "name": primary["name"],
            "duration_minutes": primary["duration_minutes"], "benefits": primary["benefits"],
        }]
        if secondary and i % 2 == 0:
            day_therapies.append({
                "id": secondary["id"], "name": secondary["name"],
                "duration_minutes": secondary["duration_minutes"], "benefits": secondary["benefits"],
            })
        schedule.append({"day": start_day + i, "phase": phase_name, "therapies": day_therapies})
    return schedule


# ── Main Entry Point ──────────────────────────────────────────────────────────

def generate_panchakarma_plan(user_profile: dict, pk_prefs: dict, pk_therapies_db=None) -> dict:
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
    severe_unmapped = [
        c for c in unmapped_conditions
        if any(kw in c.lower() for kw in _SEVERE_KEYWORDS)
    ]
    vaidya_review_required = len(unmapped_conditions) > 0

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
    ritu_ctx    = _get_ritu_context(protocols)
    eligibility = _determine_shodhana_or_shamana(user_profile, pk_prefs, protocols)

    # Severe unmapped condition override — conservative Shamana.
    # Applied before any Karma is selected, so the override cannot be outrun by a
    # Pradhana Karma that was already chosen.
    if severe_unmapped and eligibility.get("type") != "shamana":
        blocking = [
            f"Severe systemic condition(s) detected outside classical disease mapping: "
            f"{', '.join(severe_unmapped)}. Conservative Shamana applied — Vaidya assessment required "
            "before any Shodhana. Ref: CS Sutrasthana 15 (Bala Pareeksha mandatory)."
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

    is_shamana = eligibility.get("type") == "shamana"

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
        pradhana, safety_warnings = _restrict_to_brimhana(pradhana, eligibility)
        # Safety gate: substitute karma if hard contraindicated by medical history
        pradhana, karma_warnings = _validate_karma_safety(pradhana, medical_history)
        safety_warnings += karma_warnings

    if severe_unmapped:
        safety_warnings.append(
            f"⚠ VAIDYA REVIEW REQUIRED: Unmapped severe conditions ({', '.join(severe_unmapped)}) "
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
    if is_shamana:
        purva_days = pradhana_days = paschat_days = 0
        basti_info = None
    else:
        # A Shodhana course has a floor: Purvakarma cannot be shorter than 2 days,
        # the Karma needs its own day, and Samsarjana Krama is 2 days at the very
        # least. Below that the phase minimums simply overran the budget in silence —
        # a 3-day request returned a 5-day schedule while `total_days` still read 3,
        # so the duration on the card and the calendar under it were different plans.
        _MIN_SHODHANA_DAYS = 5
        if total_days < _MIN_SHODHANA_DAYS:
            duration_notice = (
                f"Extended from {total_days} to {_MIN_SHODHANA_DAYS} days: Purvakarma, the Karma "
                "itself and Samsarjana Krama cannot be compressed further without making the "
                "course unsafe. Shortening any of them is what causes post-Shodhana complications."
            )
            total_days = _MIN_SHODHANA_DAYS

        if eligibility.get("ama_correction_needed") or eligibility.get("agni_correction_needed"):
            # Capped so the correction can never crowd out the cleanse it prepares for.
            deepana_days = min(max(3, min(7, int(total_days * 0.25))), max(0, total_days - _MIN_SHODHANA_DAYS))

        shodhana_days = total_days - deepana_days
        purva_days = _purvakarma_days(vikriti_dom, shodhana_days, protocols)

        remaining = shodhana_days - purva_days
        if pradhana["primary"] in ("basti", "basti_matra"):
            bs = _basti_subtype(karma_setting, remaining - 2)
            pradhana_days = min(bs["days"], remaining - 2)
        else:
            # Vamana = 1 day; Virechana = 1 day; Nasya = 5–7 days
            pradhana_days = min(5 if pradhana["primary"] == "nasya" else 1, remaining - 2)
        pradhana_days = max(1, pradhana_days)
        paschat_days  = max(2, shodhana_days - purva_days - pradhana_days)

        basti_info = (
            _basti_subtype(karma_setting, remaining - 2)
            if pradhana["primary"] in ("basti", "basti_matra") else None
        )

    # Koshtha: check user_profile first, then pk_prefs (PreferencesModal asks it for PK context)
    koshtha = user_profile.get("koshtha") or pk_prefs.get("koshtha") or "sama"

    # ── Aushadha & Samsarjana ─────────────────────────────────────────────────
    aushadha = _select_aushadha(
        vikriti_dom, medical_history, pradhana["primary"] or "shamana", karma_setting, protocols, koshtha
    )
    # Samsarjana Krama is the graded re-entry from a Shodhana-emptied Koshtha. With
    # no Shodhana there is nothing to re-enter from, and printing its stages would
    # put a mono-diet ladder in a plan whose whole purpose is to stop depleting.
    samsarjana = [] if is_shamana else _samsarjana_krama(pradhana["primary"], protocols)

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
        )
        schedule = shamana_build["schedule"]
        phases   = shamana_build["phases"]
        sd       = shamana_build["days"]
        purva_days, pradhana_days, paschat_days = 0, 0, sd["brimhana"]
    else:
        purva_pool    = filter_and_score_therapies(user_profile, pk_prefs, "purvakarma", pkt, vikriti_dom)
        pradhana_pool = filter_and_score_therapies(user_profile, pk_prefs, "pradhana",   pkt, vikriti_dom)
        paschat_pool  = filter_and_score_therapies(user_profile, pk_prefs, "paschat",    pkt, vikriti_dom)

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

        schedule.extend(assemble_phase(purva_pool,    purva_days,    offset,                              "Purvakarma (Preparation)"))
        schedule.extend(assemble_phase(pradhana_pool, pradhana_days, offset + purva_days,                 "Pradhana Karma (Main Cleanse)"))
        schedule.extend(assemble_phase(paschat_pool,  paschat_days,  offset + purva_days + pradhana_days, "Paschat Karma (Rejuvenation)"))

        # The pinned action IS the Pradhana Karma, fully described. The therapy pool
        # holds a row for every Karma in the KB and was never filtered by the one
        # selected, so a Virechana day also listed "Clinical Nasya", and a patient
        # whose Virechana had been withheld for low Ojas still had "Virechana
        # (Clinical Purgation)" on the calendar beside the Nasya that replaced it.
        # A substitution that leaves the original on the schedule is not a substitution.
        pk_action = _pradhana_day_action(pradhana["primary"], aushadha, basti_info, karma_setting, ritu_ctx.get("ritu", ""))
        if pk_action:
            for day_entry in schedule:
                if "Pradhana" in day_entry.get("phase", ""):
                    day_entry["therapies"] = [pk_action]

        phases += [
            {"key": "purvakarma", "label": "Purvakarma",
             "sub": "Snehana + Swedana (Preparation)", "days": purva_days},
            {"key": "pradhana", "label": "Pradhana Karma",
             "sub": (pradhana["primary"] or "").replace("_", " "), "days": pradhana_days},
            {"key": "paschat", "label": "Paschat Karma",
             "sub": "Samsarjana Krama + Rasayana", "days": paschat_days},
        ]

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
            "unmapped_conditions":    unmapped_conditions,
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
        },

        # ── Shamana arm detail (present only when Shodhana is withheld) ───────
        "shamana_protocol": shamana_build.get("protocol") if is_shamana else None,

        # ── Aushadha (medicines/oils) ─────────────────────────────────────────
        "aushadha": aushadha,

        # ── Post-PK dietary re-entry ──────────────────────────────────────────
        "samsarjana_krama": samsarjana,

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
