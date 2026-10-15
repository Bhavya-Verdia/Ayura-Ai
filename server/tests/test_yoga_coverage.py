"""What a per-condition probe, a medicines probe, a 600-plan sweep and eight live
plans read whole found in the yoga feature.

Medicines were read by neither yoga nor gym; ankylosing spondylitis, lumbar
spondylosis and atrial fibrillation reached no mechanism; the gym's
before-you-train notes never reached yoga; nothing mentioned menstruation; the
second trimester was served supine poses and every pregnant woman a flat-on-
the-back Savasana; and the AI narrative passed no gate.
"""
import re

import pytest

import services.yoga_plan_engine as Y
from engine.movement_risk import condition_risk_tags, medication_risk_tags
from services.gym_condition_guidance import CONDITION_GUIDANCE, guidance_for
from services.yoga_plan_enricher import gate_yoga_enrichment

_POSES = {p["id"]: p for p in Y.yoga_poses}
_PREFS = dict(yoga_goal="flexibility", yoga_experience="advanced", time_available_minutes=45,
              time_of_day_preference="morning")


def _p(**over):
    base = dict(id="t", age=40, gender="female", dominant_dosha="pitta", vikriti_dominant="pitta",
                medical_history=[], current_medications=[])
    base.update(over)
    return base


def _served(plan):
    return [p for d in plan["weekly_schedule"] for k in ("warmup", "main_sequence", "cooldown")
            for p in d["session"][k]]


# ── Mechanisms ────────────────────────────────────────────────────────────────

def test_ankylosing_and_lumbar_spondylosis_reach_a_mechanism():
    assert {"spinal_flexion", "neck_load"} <= condition_risk_tags(["ankylosing_spondylitis"])
    assert "spinal_extension" in condition_risk_tags(["lumbar_spondylosis"])
    plan = Y.generate_yoga_plan(_p(gender="male", medical_history=["ankylosing_spondylitis"]), _PREFS)
    for p in _served(plan):
        assert not set(_POSES[p["pose_id"]].get("risk_tags") or []) & {"spinal_flexion", "neck_load"}


def test_atrial_fibrillation_is_treated_as_a_heart_condition():
    plan = Y.generate_yoga_plan(_p(age=60, medical_history=["atrial_fibrillation"]), _PREFS)
    assert all(d["session"]["surya_namaskar"] is None for d in plan["weekly_schedule"])
    assert any(g["key"] == "cardiac" for g in plan["condition_guidance"])


# ── Medicines ─────────────────────────────────────────────────────────────────

def test_an_anticoagulant_removes_every_head_loaded_pose():
    plan = Y.generate_yoga_plan(_p(current_medications=["Acitrom 2"]), _PREFS)
    assert not any("neck_load" in (_POSES[p["pose_id"]].get("risk_tags") or []) for p in _served(plan))
    assert any(g["key"] == "med_bleeding" for g in plan["condition_guidance"])


def test_a_sedative_after_65_is_a_fall_risk_and_before_it_is_not():
    assert "fall_risk" in medication_risk_tags({"sedatives"}, 70)
    assert "fall_risk" not in medication_risk_tags({"sedatives"}, 40)


def test_blood_pressure_tablets_bring_the_standing_up_note():
    plan = Y.generate_yoga_plan(_p(current_medications=["amlodipine"]), _PREFS)
    assert [g["key"] for g in plan["condition_guidance"]] == ["med_orthostatic"]


def test_insulin_without_recorded_diabetes_still_gets_the_glucose_note():
    keys = [g["key"] for g in guidance_for(["med:insulin_or_sulfonylurea"], "yoga")]
    assert keys == ["med_hypoglycaemia"]
    keys = [g["key"] for g in guidance_for(["diabetes_type1", "med:insulin_or_sulfonylurea"], "yoga")]
    assert keys == ["diabetes"]


def test_the_gym_reads_medicines_too():
    from services.gym_plan_engine import _avoided_risks
    assert "neck_load" in _avoided_risks(_p(current_medications=["warfarin"]))


# ── Guidance wording ──────────────────────────────────────────────────────────

_GYM_WORDS = re.compile(r"\b(weights?(?!-bearing)|lift\w*|training|train\b|bars?\b|machines?|reps?)\b", re.I)


def test_no_gym_wording_reaches_a_yoga_plan():
    for g in CONDITION_GUIDANCE:
        note = g.get("yoga_note") or g["note"]
        assert not _GYM_WORDS.search(note), (g["key"], _GYM_WORDS.findall(note))


# ── Menstruation and pregnancy ────────────────────────────────────────────────

def test_a_woman_is_told_about_inversions_on_period_days():
    plan = Y.generate_yoga_plan(_p(), _PREFS)
    assert plan["menstruation_note"]
    assert all(p["skip_during_period"] == (p["category"] == "inversion") for p in _served(plan))
    assert Y.generate_yoga_plan(_p(gender="male"), _PREFS)["menstruation_note"] is None


def test_heavy_bleeding_adds_to_the_note():
    plan = Y.generate_yoga_plan(_p(medical_history=["menorrhagia"]), _PREFS)
    assert "heavy bleeding" in plan["menstruation_note"]


@pytest.mark.parametrize("trimester", [2, 3])
def test_no_supine_pose_from_the_second_trimester_and_savasana_is_on_the_left_side(trimester):
    plan = Y.generate_yoga_plan(_p(age=29, pregnancy_or_nursing=True, pregnancy_status="pregnant",
                                   pregnancy_trimester=trimester),
                                {**_PREFS, "yoga_experience": "intermediate"})
    served = _served(plan)
    assert not any(p["category"] == "supine" for p in served)
    finals = [p for p in served if p.get("final_relaxation")]
    assert finals and all("left side" in p["pose_name"] for p in finals)


# ── The narrative passes a gate ───────────────────────────────────────────────

def test_the_gate_withholds_an_excluded_pose_breath_and_allergen():
    prof = _p(age=58, dominant_dosha="kapha", medical_history=["hypertension", "glaucoma"], allergies=["dairy"])
    plan = Y.generate_yoga_plan(prof, _PREFS)
    out, withheld = gate_yoga_enrichment(
        {"breathing_guidance": "Begin with Anulom Vilom. Add Kapalabhati to clear Kapha. Avoid Kapalabhati if dizzy.",
         "condition_coaching": {"glaucoma": "Practise Headstand with a teacher. Keep the head above the heart."},
         "lifestyle_sync": "Drink warm milk at night. Walk after dinner."}, plan, prof, _PREFS)
    assert out["breathing_guidance"] == "Begin with Anulom Vilom. Avoid Kapalabhati if dizzy."
    assert out["condition_coaching"]["glaucoma"] == "Keep the head above the heart."
    assert out["lifestyle_sync"] == "Walk after dinner."
    assert len(withheld) == 3


def test_a_common_word_in_a_pose_name_is_not_a_pose():
    prof = _p(age=29, pregnancy_or_nursing=True, pregnancy_status="pregnant", pregnancy_trimester=2)
    plan = Y.generate_yoga_plan(prof, {**_PREFS, "yoga_experience": "intermediate"})
    out, withheld = gate_yoga_enrichment({"x": "Unwind with smooth rotation and spacious awareness."},
                                         plan, prof, _PREFS)
    assert withheld == []


def test_a_healthy_practitioner_keeps_the_advanced_pose_the_plan_allows():
    prof = _p(age=30, gender="male")
    plan = Y.generate_yoga_plan(prof, _PREFS)
    text = "Hold Headstand for ten breaths."
    assert gate_yoga_enrichment({"x": text}, plan, prof, _PREFS) == ({"x": text}, [])


def test_a_pregnant_practitioner_gets_the_pregnancy_note_and_a_nursing_one_does_not():
    prof = _p(age=29, pregnancy_or_nursing=True, pregnancy_status="pregnant", pregnancy_trimester=2)
    plan = Y.generate_yoga_plan(prof, {**_PREFS, "yoga_experience": "intermediate"})
    notes = {g["key"]: g["note"] for g in plan["condition_guidance"] or []}
    assert "left side" in notes["pregnancy"]
    nursing = Y.generate_yoga_plan(_p(pregnancy_or_nursing=True, pregnancy_status="nursing"), _PREFS)
    assert "pregnancy" not in {g["key"] for g in nursing["condition_guidance"] or []}
