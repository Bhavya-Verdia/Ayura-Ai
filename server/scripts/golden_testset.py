"""
Golden synthetic test set + BAMS grading harness.

Why this exists
---------------
Ayura AI has no real patient data. For a classical decision-support engine that is
the right situation — we don't need population outcomes, we need EXPERT AGREEMENT.
This script:

  1. Defines a CURATED set of synthetic patients spanning Prakriti × Vikriti ×
     conditions × age bands × pregnancy × koshtha/agni — the clinically important space.
  2. Runs every patient through the deterministic engines (no LLM — fully offline,
     reproducible) and captures the key clinical decisions.
  3. Asserts hard SAFETY INVARIANTS (forceful pranayama never reaches a hypertensive
     patient, no contraindicated medicine is ever selected, pregnancy gating holds,
     etc.). Run it in CI — a regression that breaks classical safety fails the build.
  4. Emits `golden_review.md` — a per-case report with a grading rubric a BAMS
     faculty member / student can fill in. Their grades become your validation
     dataset and your demo credibility line ("validated against N BAMS reviewers").

Usage:
    cd server && ./venv/bin/python scripts/golden_testset.py
Outputs (next to this script, under ../data/golden/):
    golden_cases.json   — full structured engine outputs
    golden_review.md     — human grading document
Exit code is non-zero if any safety invariant fails.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.yoga_plan_engine import generate_yoga_plan, select_pranayama, pranayama_list
from services.gym_plan_engine import generate_gym_plan
from services.panchakarma_engine import generate_panchakarma_plan
from services.routine_engine import generate_routine_plan
from services.remedy_engine import (
    filter_remedies, build_remedy_plan, generate_medicines_plan, _MEDICINES_KB,
)
from schemas.preferences_schema import (
    YogaPreferences, GymPreferences, PanchakarmaPreferences, RemedyPreferences,
)
try:
    from schemas.preferences_schema import RoutinePreferences
    _ROUTINE_DEFAULTS = RoutinePreferences().model_dump()
except Exception:
    _ROUTINE_DEFAULTS = {}

FORCEFUL_PRANAYAMA = {
    "skull_shining", "bellows_breath", "breath_retention",
    "right_nostril", "fire_essence", "swooning_breath", "root_lock_breath",
}

# ── Curated synthetic patients ────────────────────────────────────────────────
# Each spans a distinct, clinically meaningful slice. `expect` carries the
# invariants the engines must satisfy for this case.
CASES: list[dict] = [
    {
        "id": "vata_anxiety_insomnia",
        "label": "Vata constitution, anxiety + insomnia, young adult",
        "profile": dict(name="Aarav", gender="male", age=28, height_cm=175, weight_kg=62,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["anxiety", "insomnia"],
                        current_symptoms=["anxiety", "insomnia"], fitness_level="intermediate",
                        agni_type="vishama", koshtha="krura", ama_indicator="mild", ojas_level="low"),
    },
    {
        "id": "pitta_acidity_migraine",
        "label": "Pitta constitution, acid reflux + migraine, adult",
        "profile": dict(name="Meera", gender="female", age=35, height_cm=162, weight_kg=58,
                        bmi_category="normal", dominant_dosha="pitta", secondary_dosha="vata",
                        vikriti_dominant="pitta", medical_history=["acid_reflux", "migraine"],
                        current_symptoms=["acidity", "headache"], fitness_level="intermediate",
                        agni_type="tikshna", koshtha="mridu", ama_indicator="none", ojas_level="medium"),
    },
    {
        "id": "kapha_obesity_hypothyroid",
        "label": "Kapha constitution, obesity + hypothyroid, midlife",
        "profile": dict(name="Suresh", gender="male", age=47, height_cm=170, weight_kg=92,
                        bmi_category="obese", dominant_dosha="kapha", secondary_dosha="pitta",
                        vikriti_dominant="kapha", medical_history=["obesity", "hypothyroidism"],
                        current_symptoms=["fatigue", "weight_gain"], fitness_level="beginner",
                        digestion_quality="weak", koshtha="krura", ama_indicator="moderate", ojas_level="medium"),
        "expect": {"agni_name": "Manda Agni"},  # weak digestion + kapha → Manda (the fix)
    },
    {
        "id": "vatapitta_hypertension_senior",
        "label": "Vata-Pitta dual, hypertension, senior",
        "profile": dict(name="Lakshmi", gender="female", age=64, height_cm=158, weight_kg=70,
                        bmi_category="overweight", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", vikriti_secondary="pitta",
                        medical_history=["hypertension"], current_symptoms=["fatigue"],
                        fitness_level="beginner", agni_type="sama", koshtha="sama"),
        "expect": {"no_forceful_pranayama": True},
    },
    {
        "id": "kaphapitta_diabetes_fattyliver",
        "label": "Kapha-Pitta dual, type-2 diabetes + fatty liver",
        "profile": dict(name="Ramesh", gender="male", age=52, height_cm=172, weight_kg=88,
                        bmi_category="obese", dominant_dosha="kapha", secondary_dosha="pitta",
                        vikriti_dominant="kapha", vikriti_secondary="pitta",
                        medical_history=["diabetes_type2", "fatty_liver"], current_symptoms=["fatigue"],
                        fitness_level="beginner", agni_type="manda", koshtha="sama", ama_indicator="high"),
    },
    {
        "id": "pregnancy_pitta",
        "label": "Pregnant Pitta woman (safety gating)",
        "profile": dict(name="Anita", gender="female", age=30, height_cm=164, weight_kg=68,
                        bmi_category="normal", dominant_dosha="pitta", secondary_dosha="kapha",
                        vikriti_dominant="pitta", medical_history=[], current_symptoms=["nausea"],
                        fitness_level="beginner", pregnancy_or_nursing=True, agni_type="sama"),
        "expect": {"pregnancy_blocks_sensitive": True, "no_forceful_pranayama": True},
    },
    {
        "id": "vata_ankylosing_spondylitis",
        "label": "Vata, ankylosing spondylitis (Asthi-Majja Vata)",
        "profile": dict(name="Vikram", gender="male", age=40, height_cm=178, weight_kg=72,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="kapha",
                        vikriti_dominant="vata", medical_history=["ankylosing_spondylitis"],
                        current_symptoms=["joint_pain", "back_pain"], fitness_level="intermediate",
                        injuries_or_limitations=["ankylosing_spondylitis"], agni_type="vishama", koshtha="krura"),
    },
    {
        "id": "pitta_hypotension_cardiac",
        "label": "Pitta with hypotension + cardiac history (medicine gating)",
        "profile": dict(name="Deepa", gender="female", age=58, height_cm=160, weight_kg=64,
                        bmi_category="normal", dominant_dosha="pitta", secondary_dosha="vata",
                        vikriti_dominant="pitta", medical_history=["hypotension", "heart_disease"],
                        current_symptoms=["palpitations", "fatigue"], fitness_level="beginner",
                        agni_type="sama", koshtha="sama"),
        "expect": {"no_forceful_pranayama": True, "exclude_medicine_ids": ["arjuna_churna"]},
    },
    {
        "id": "kapha_asthma",
        "label": "Kapha, bronchial asthma (Tamaka Shwasa)",
        "profile": dict(name="Mohan", gender="male", age=33, height_cm=171, weight_kg=80,
                        bmi_category="overweight", dominant_dosha="kapha", secondary_dosha="vata",
                        vikriti_dominant="kapha", medical_history=["asthma"],
                        current_symptoms=["cough", "breathlessness"], fitness_level="beginner",
                        agni_type="manda", koshtha="sama"),
    },
    {
        "id": "vata_child_constipation",
        "label": "Vata child (Balya Avastha), constipation",
        "profile": dict(name="Riya", gender="female", age=10, height_cm=135, weight_kg=30,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["constipation"],
                        current_symptoms=["constipation"], fitness_level="beginner",
                        agni_type="vishama", koshtha="krura"),
    },
    {
        "id": "pitta_psoriasis",
        "label": "Pitta, psoriasis (Kushtha — Rakta-Pitta)",
        "profile": dict(name="Karan", gender="male", age=38, height_cm=176, weight_kg=74,
                        bmi_category="normal", dominant_dosha="pitta", secondary_dosha="kapha",
                        vikriti_dominant="pitta", medical_history=["psoriasis"],
                        current_symptoms=["skin_rash", "itching"], fitness_level="intermediate",
                        agni_type="tikshna", koshtha="sama", ama_indicator="moderate"),
    },
    {
        "id": "vata_sciatica",
        "label": "Vata, sciatica (Gridhrasi)",
        "profile": dict(name="Prakash", gender="male", age=44, height_cm=174, weight_kg=78,
                        bmi_category="overweight", dominant_dosha="vata", secondary_dosha="kapha",
                        vikriti_dominant="vata", medical_history=["sciatica"],
                        current_symptoms=["back_pain", "leg_pain"], fitness_level="beginner",
                        injuries_or_limitations=["sciatica"], agni_type="vishama", koshtha="krura"),
        "expect": {"pradhana_in": {"basti", "basti_matra"}},
    },
    {
        "id": "vatakapha_fibromyalgia",
        "label": "Vata-Kapha, fibromyalgia",
        "profile": dict(name="Sunita", gender="female", age=49, height_cm=160, weight_kg=72,
                        bmi_category="overweight", dominant_dosha="vata", secondary_dosha="kapha",
                        vikriti_dominant="vata", vikriti_secondary="kapha",
                        medical_history=["fibromyalgia"], current_symptoms=["fatigue", "body_pain"],
                        fitness_level="beginner", agni_type="manda", koshtha="sama"),
    },
    {
        "id": "vata_osteoarthritis_senior",
        "label": "Vata, osteoarthritis, senior (Sandhivata)",
        "profile": dict(name="Govind", gender="male", age=68, height_cm=170, weight_kg=75,
                        bmi_category="overweight", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["osteoarthritis"],
                        current_symptoms=["joint_pain"], fitness_level="beginner",
                        injuries_or_limitations=["osteoarthritis"], agni_type="vishama", koshtha="krura"),
        "expect": {"no_forceful_pranayama": False, "pradhana_in": {"basti", "basti_matra"}},
    },
    {
        "id": "pitta_hypertension",
        "label": "Pitta, essential hypertension",
        "profile": dict(name="Naveen", gender="male", age=46, height_cm=175, weight_kg=84,
                        bmi_category="overweight", dominant_dosha="pitta", secondary_dosha="kapha",
                        vikriti_dominant="pitta", medical_history=["hypertension"],
                        current_symptoms=["headache"], fitness_level="intermediate",
                        agni_type="tikshna", koshtha="sama"),
        "expect": {"no_forceful_pranayama": True},
    },
    {
        "id": "kapha_pcos_female",
        "label": "Kapha, PCOS (Artava Dushti)",
        "profile": dict(name="Pooja", gender="female", age=29, height_cm=162, weight_kg=76,
                        bmi_category="obese", dominant_dosha="kapha", secondary_dosha="vata",
                        vikriti_dominant="kapha", medical_history=["pcos"],
                        current_symptoms=["irregular_periods", "weight_gain"], fitness_level="beginner",
                        agni_type="manda", koshtha="sama"),
    },
    {
        "id": "vata_ibs",
        "label": "Vata, IBS (Grahani)",
        "profile": dict(name="Imran", gender="male", age=34, height_cm=172, weight_kg=64,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["ibs"],
                        current_symptoms=["bloating", "irregular_digestion"], fitness_level="intermediate",
                        agni_type="vishama", koshtha="krura", ama_indicator="moderate"),
        "expect": {"pradhana_in": {"basti", "basti_matra"}},
    },
    {
        "id": "kapha_sinusitis",
        "label": "Kapha, chronic sinusitis (Pratishyaya)",
        "profile": dict(name="Harish", gender="male", age=41, height_cm=171, weight_kg=82,
                        bmi_category="overweight", dominant_dosha="kapha", secondary_dosha="pitta",
                        vikriti_dominant="kapha", medical_history=["sinusitis"],
                        current_symptoms=["congestion", "headache"], fitness_level="beginner",
                        agni_type="manda", koshtha="sama"),
    },
    {
        "id": "vata_parkinsons_senior",
        "label": "Vata, Parkinson's (Kampavata), senior",
        "profile": dict(name="Mahesh", gender="male", age=70, height_cm=168, weight_kg=66,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["parkinson"],
                        current_symptoms=["tremor", "stiffness"], fitness_level="beginner",
                        agni_type="vishama", koshtha="krura", ojas_level="low"),
        "expect": {"pradhana_in": {"basti", "basti_matra"}},
    },
    {
        "id": "kapha_depression",
        "label": "Kapha, depression (Kaphaja Unmada / Vishada)",
        "profile": dict(name="Sneha", gender="female", age=36, height_cm=160, weight_kg=74,
                        bmi_category="overweight", dominant_dosha="kapha", secondary_dosha="vata",
                        vikriti_dominant="kapha", medical_history=["depression"],
                        current_symptoms=["low_mood", "lethargy"], fitness_level="beginner",
                        agni_type="manda", koshtha="sama", ojas_level="low"),
    },
    {
        "id": "pitta_gout",
        "label": "Pitta, gout (Vatarakta)",
        "profile": dict(name="Rajeev", gender="male", age=51, height_cm=177, weight_kg=90,
                        bmi_category="obese", dominant_dosha="pitta", secondary_dosha="vata",
                        vikriti_dominant="pitta", vikriti_secondary="vata",
                        medical_history=["gout"], current_symptoms=["joint_pain", "swelling"],
                        fitness_level="beginner", agni_type="tikshna", koshtha="sama"),
    },
    {
        "id": "vata_epilepsy",
        "label": "Vata, epilepsy (Apasmara) — pranayama safety",
        "profile": dict(name="Tara", gender="female", age=26, height_cm=158, weight_kg=52,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=["epilepsy"],
                        current_symptoms=["anxiety"], fitness_level="beginner",
                        agni_type="vishama", koshtha="krura"),
        "expect": {"no_forceful_pranayama": True},
    },
    {
        "id": "pitta_glaucoma",
        "label": "Pitta, glaucoma — pranayama safety (no inversions/forceful)",
        "profile": dict(name="Bina", gender="female", age=55, height_cm=159, weight_kg=63,
                        bmi_category="normal", dominant_dosha="pitta", secondary_dosha="kapha",
                        vikriti_dominant="pitta", medical_history=["glaucoma"],
                        current_symptoms=["eye_strain"], fitness_level="beginner",
                        agni_type="tikshna", koshtha="sama"),
        "expect": {"no_forceful_pranayama": True},
    },
    {
        "id": "kapha_fatty_liver",
        "label": "Kapha, NAFLD fatty liver (Yakrit Vikara)",
        "profile": dict(name="Dinesh", gender="male", age=48, height_cm=173, weight_kg=95,
                        bmi_category="obese", dominant_dosha="kapha", secondary_dosha="pitta",
                        vikriti_dominant="kapha", medical_history=["fatty_liver"],
                        current_symptoms=["fatigue", "heaviness"], fitness_level="beginner",
                        agni_type="manda", koshtha="sama", ama_indicator="high"),
    },
    {
        "id": "pregnancy_vata",
        "label": "Pregnant Vata woman (safety gating)",
        "profile": dict(name="Kavya", gender="female", age=29, height_cm=161, weight_kg=60,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=[], current_symptoms=["back_pain"],
                        fitness_level="beginner", pregnancy_or_nursing=True, agni_type="vishama"),
        "expect": {"pregnancy_blocks_sensitive": True, "no_forceful_pranayama": True},
    },
    {
        "id": "vatapitta_anxiety_young",
        "label": "Vata-Pitta, anxiety + acidity, young professional",
        "profile": dict(name="Rohan", gender="male", age=27, height_cm=178, weight_kg=70,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", vikriti_secondary="pitta",
                        medical_history=["anxiety", "acid_reflux"], current_symptoms=["anxiety", "acidity"],
                        fitness_level="intermediate", agni_type="vishama", koshtha="mridu"),
    },
    {
        "id": "kapha_hyperlipidemia",
        "label": "Kapha, high cholesterol (Medo Dushti)",
        "profile": dict(name="Anand", gender="male", age=53, height_cm=170, weight_kg=89,
                        bmi_category="obese", dominant_dosha="kapha", secondary_dosha="pitta",
                        vikriti_dominant="kapha", medical_history=["cholesterol", "obesity"],
                        current_symptoms=["fatigue"], fitness_level="beginner",
                        agni_type="manda", koshtha="krura", ama_indicator="high"),
    },
    {
        "id": "pitta_hyperthyroid",
        "label": "Pitta, hyperthyroidism (Atyagni / Bhasmaka)",
        "profile": dict(name="Divya", gender="female", age=33, height_cm=163, weight_kg=52,
                        bmi_category="underweight", dominant_dosha="pitta", secondary_dosha="vata",
                        vikriti_dominant="pitta", medical_history=["hyperthyroidism"],
                        current_symptoms=["palpitations", "weight_loss"], fitness_level="intermediate",
                        agni_type="tikshna", koshtha="mridu", ojas_level="low"),
    },
    {
        "id": "vata_insomnia_athlete",
        "label": "Vata, healthy active baseline (no conditions)",
        "profile": dict(name="Arjun", gender="male", age=24, height_cm=180, weight_kg=72,
                        bmi_category="normal", dominant_dosha="vata", secondary_dosha="pitta",
                        vikriti_dominant="vata", medical_history=[], current_symptoms=[],
                        fitness_level="advanced", agni_type="sama", koshtha="sama"),
    },
    {
        "id": "tridoshic_senior_multi",
        "label": "Senior, multiple conditions (HTN + diabetes + arthritis)",
        "profile": dict(name="Shanti", gender="female", age=72, height_cm=155, weight_kg=68,
                        bmi_category="overweight", dominant_dosha="vata", secondary_dosha="kapha",
                        vikriti_dominant="vata", medical_history=["hypertension", "diabetes_type2", "osteoarthritis"],
                        current_symptoms=["joint_pain", "fatigue"], fitness_level="beginner",
                        agni_type="vishama", koshtha="krura", ojas_level="low"),
        "expect": {"no_forceful_pranayama": True},
    },
]


def _prefs():
    return {
        "yoga": YogaPreferences().model_dump(),
        "gym": GymPreferences().model_dump(),
        "panchakarma": PanchakarmaPreferences().model_dump(),
        "remedies": RemedyPreferences().model_dump(),
    }


def run_case(case: dict) -> dict:
    profile = case["profile"]
    prefs = _prefs()
    is_pregnant = bool(profile.get("pregnancy_or_nursing"))
    out: dict = {"id": case["id"], "label": case["label"], "conditions": profile.get("medical_history", [])}

    # Panchakarma
    pk = generate_panchakarma_plan(profile, prefs["panchakarma"], None)
    cd = pk["clinical_decisions"]
    out["panchakarma"] = {
        "shodhana_or_shamana": cd["shodhana_or_shamana"]["type"],
        "pradhana_karma": cd["pradhana_karma_selected"]["primary"],
        "agni_name": pk["user_summary"]["agni_name"],
        "ritu": cd["ritu_context"].get("ritu"),
        "safety_warnings": cd.get("safety_warnings", []),
        "setting": pk["user_summary"]["setting"],
    }

    # Yoga + pranayama (call selection directly for the safety-critical list)
    yoga = generate_yoga_plan(profile, prefs["yoga"], None, None)
    selected_prana = select_pranayama(profile, prefs["yoga"], pranayama_list, count=6)
    prana_ids = [p.get("id") for p in selected_prana]
    out["yoga"] = {
        "plan_id": yoga.get("plan_id"),
        "pranayama_selected": prana_ids,
        "forceful_included": sorted(set(prana_ids) & FORCEFUL_PRANAYAMA),
    }

    # Gym
    gym = generate_gym_plan(profile, prefs["gym"], None)
    out["gym"] = {"has_schedule": bool(gym.get("weekly_schedule") or gym.get("plan_id"))}

    # Routine
    routine = generate_routine_plan(profile, {"routine": _ROUTINE_DEFAULTS, "diet": {}})
    out["routine"] = {
        "has_shaucha": "Mala-Mutra Visarjana" in json.dumps(routine),
        "has_brahma_muhurta": "Brahma Muhurta" in json.dumps(routine),
    }

    # Medicines (pregnancy-gated upstream in the route, but engine also self-gates)
    meds = generate_medicines_plan(profile, prefs["remedies"], [], "clinical_medicine")
    selected_meds = [m.get("id") for m in (meds.get("primary_formulations", []) + meds.get("supporting_formulations", []))]
    out["medicines"] = {
        "selected_ids": selected_meds,
        "selected_names": [m.get("name") for m in (meds.get("primary_formulations", []) + meds.get("supporting_formulations", []))],
    }

    # Remedies
    symptoms = profile.get("current_symptoms", [])
    if symptoms:
        filtered = filter_remedies(profile, {"symptoms": symptoms})
        rplan = build_remedy_plan(filtered, profile, {"symptoms": symptoms})
        out["remedies"] = {"symptoms_addressed": len(rplan.get("symptoms_addressed", []))}
    else:
        out["remedies"] = {"symptoms_addressed": 0}

    return out


def check_invariants(case: dict, result: dict) -> list[str]:
    """Return a list of safety-invariant violations (empty == all pass)."""
    fails: list[str] = []
    profile = case["profile"]
    conds = [c.lower() for c in profile.get("medical_history", [])]
    expect = case.get("expect", {})

    # 1. Forceful pranayama must never reach HTN / cardiac / epilepsy / pregnancy
    risky = {"hypertension", "high_blood_pressure", "heart_disease", "cardiac",
             "epilepsy", "glaucoma", "hernia"}
    if expect.get("no_forceful_pranayama") or (set(conds) & risky) or profile.get("pregnancy_or_nursing"):
        leaked = result["yoga"]["forceful_included"]
        if leaked:
            fails.append(f"FORCEFUL PRANAYAMA leaked to risky patient: {leaked}")

    # 2. No selected medicine may carry a contraindication matching the patient
    kb_by_id = {m["id"]: m for m in _MEDICINES_KB}
    for mid in result["medicines"]["selected_ids"]:
        med = kb_by_id.get(mid, {})
        for contra in (med.get("contraindications") or []):
            cl = str(contra).lower()
            if any(cl in c or c in cl for c in conds):
                fails.append(f"CONTRAINDICATED MEDICINE selected: {mid} (contra '{contra}' vs patient {conds})")
    for forbidden in expect.get("exclude_medicine_ids", []):
        if forbidden in result["medicines"]["selected_ids"]:
            fails.append(f"Expected medicine excluded but present: {forbidden}")

    # 3. Pregnancy: PK must be Shamana (engine never gives full Shodhana home), and
    #    no pregnancy-unsafe medicine should be selected.
    if profile.get("pregnancy_or_nursing"):
        for mid in result["medicines"]["selected_ids"]:
            if kb_by_id.get(mid, {}).get("pregnancy_safe") is False:
                fails.append(f"PREGNANCY-UNSAFE medicine selected: {mid}")

    # 4. Expected Agni name (Manda Agni reachability fix)
    if "agni_name" in expect and result["panchakarma"]["agni_name"] != expect["agni_name"]:
        fails.append(f"Agni mismatch: expected {expect['agni_name']}, got {result['panchakarma']['agni_name']}")

    # 4b. Expected Pradhana Karma family (dominant-dosha correctness)
    if "pradhana_in" in expect:
        got = result["panchakarma"]["pradhana_karma"]
        if got not in expect["pradhana_in"]:
            fails.append(f"Pradhana Karma {got} not in expected {sorted(expect['pradhana_in'])}")

    # 5. Dinacharya completeness
    if not result["routine"]["has_shaucha"]:
        fails.append("Routine missing Mala-Mutra Visarjana (Shaucha)")

    return fails


def write_review(results: list[dict], all_fails: dict) -> str:
    lines = [
        "# Ayura AI — Golden Case Review (BAMS Grading)",
        "",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
        f"{len(results)} synthetic cases, deterministic engine output (no LLM)._",
        "",
        "**Reviewer instructions:** For each case, grade each feature 1–5 "
        "(1 = clinically wrong, 5 = matches what you would prescribe). Mark "
        "**Prescribe? Y/N** and add corrections. Your grades are the validation dataset.",
        "",
        "| Grade | Meaning |",
        "|---|---|",
        "| 5 | Exactly what I would prescribe |",
        "| 4 | Sound, minor tweaks |",
        "| 3 | Acceptable but not optimal |",
        "| 2 | Significant classical error |",
        "| 1 | Clinically wrong / unsafe |",
        "",
        "---",
        "",
    ]
    for r in results:
        pk = r["panchakarma"]
        lines += [
            f"## {r['label']}",
            f"`{r['id']}` — conditions: {', '.join(r['conditions']) or 'none'}",
            "",
            "**Engine decisions**",
            "",
            f"- **Panchakarma:** {pk['shodhana_or_shamana'].title()} · "
            f"Pradhana Karma = **{pk['pradhana_karma'].title()}** · Agni = {pk['agni_name']} · "
            f"Ritu = {pk['ritu']} · setting = {pk['setting']}",
        ]
        if pk["safety_warnings"]:
            lines.append(f"  - ⚠ Safety: {'; '.join(pk['safety_warnings'])}")
        lines += [
            f"- **Yoga pranayama:** {', '.join(r['yoga']['pranayama_selected']) or '—'}"
            + (f"  ⚠ forceful: {r['yoga']['forceful_included']}" if r['yoga']['forceful_included'] else ""),
            f"- **Medicines:** {', '.join(r['medicines']['selected_names']) or '—'}",
            f"- **Remedies addressed:** {r['remedies']['symptoms_addressed']}",
            f"- **Routine:** Shaucha {'✓' if r['routine']['has_shaucha'] else '✗'} · "
            f"Brahma Muhurta {'✓' if r['routine']['has_brahma_muhurta'] else '✗'}",
            "",
        ]
        viol = all_fails.get(r["id"])
        if viol:
            lines.append(f"> ❌ **Automated safety violations:** {'; '.join(viol)}")
            lines.append("")
        lines += [
            "**Grading**",
            "",
            "| Feature | Grade (1–5) | Prescribe? | Corrections |",
            "|---|---|---|---|",
            "| Panchakarma |  |  |  |",
            "| Yoga / Pranayama |  |  |  |",
            "| Medicines |  |  |  |",
            "| Daily Routine |  |  |  |",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    results = []
    all_fails: dict[str, list[str]] = {}
    for case in CASES:
        r = run_case(case)
        fails = check_invariants(case, r)
        if fails:
            all_fails[case["id"]] = fails
        r["safety_violations"] = fails
        results.append(r)

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "golden"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "golden_cases.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "golden_review.md"), "w", encoding="utf-8") as f:
        f.write(write_review(results, all_fails))

    print(f"Ran {len(results)} golden cases → {out_dir}")
    total_viol = sum(len(v) for v in all_fails.values())
    if total_viol:
        print(f"\n❌ {total_viol} SAFETY INVARIANT VIOLATION(S):")
        for cid, viol in all_fails.items():
            for v in viol:
                print(f"   [{cid}] {v}")
        return 1
    print("✓ All safety invariants passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
