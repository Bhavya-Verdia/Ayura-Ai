"""The day around the meals: meal times, the wake-up and bedtime drinks, the spice
guide and the dosha tips (`services/diet_day_frame`).

Before this they were fixed per-dosha tables that no screen read: golden milk at
bedtime for a vegan Vata, honey-ginger-lemon water every morning for a diabetic,
Jain or acidity Kapha, hing for a coeliac, fenugreek seed in pregnancy — and a 16:8
window shown beside a 7 AM breakfast and a bedtime milk.
"""
import itertools

import pytest

import services.diet_llm_generator as gen
from services import diet_brief_builder as bb
from services.diet_allowed_foods import allowed_foods
from services.diet_brief_builder import build_brief
from services.diet_day_frame import _BEDTIME, _SPICES, _TIPS, _WAKE_UP, day_frame
from services.diet_energy import energy_target
from tests.diet_fake_llm import make_fake

_BASE = {"id": "u1", "age": 35, "gender": "female", "height_cm": 160, "weight_kg": 60,
         "bmi_category": "normal", "activity_level": "moderate", "agni_type": "sama"}


def _frame(profile=None, prefs=None):
    profile = {**_BASE, **(profile or {})}
    prefs = prefs or {}
    screen = allowed_foods(profile, prefs)
    ids = {f["id"] for f in screen["allowed"]}
    return day_frame(profile, prefs, ids, energy_target(profile, prefs), screen["excluded"]), ids


def _named_foods(frame):
    """Every food id the frame puts in front of the patient."""
    out = {c["food"] for r in frame["rituals"] for c in r["components"]}
    spice_ids = {name: fid for d in _SPICES.values() for name, _, fid, _ in d}
    out |= {spice_ids[s["name"]] for s in frame["spice_guide"] if spice_ids[s["name"]]}
    for options in (o for d in _TIPS.values() for o in d):
        for sentence, ids in options:
            if sentence in frame["ayurvedic_tips"]:
                out |= set(ids)
    return out


_PROFILES = [
    {"medical_history": ["diabetes"]}, {"medical_history": ["acidity"]},
    {"medical_history": ["celiac"]}, {"medical_history": ["kidney_disease"]},
    {"pregnancy_or_nursing": True}, {"age": 12}, {"age": 78}, {},
]
_PREFS = [
    {}, {"dietary_type": "vegan"}, {"food_allergies": ["dairy"]},
    {"food_allergies": ["soy", "nuts_tree"]}, {"dietary_restrictions": ["jain"]},
    {"food_intolerances": ["lactose"]}, {"intermittent_fasting": "16:8"},
]


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_nothing_on_the_card_is_off_the_patients_food_list(dosha):
    for profile, prefs in itertools.product(_PROFILES, _PREFS):
        frame, ids = _frame({**profile, "dominant_dosha": dosha}, prefs)
        off = _named_foods(frame) - ids
        assert not off, (dosha, profile, prefs, off)


def test_a_vegan_vata_is_not_given_golden_milk_at_bedtime():
    frame, _ = _frame({"dominant_dosha": "vata"}, {"dietary_type": "vegan"})
    assert "milk_full_fat" not in _named_foods(frame)
    assert "soy milk" in frame["meal_timing"]["bedtime_drink"].lower()
    assert any(w["item"].startswith("Warm milk") for w in frame["withheld_guidance"])
    assert "ghee" not in frame["ayurvedic_tips"].lower()


def test_a_diabetic_kapha_is_not_told_to_take_honey():
    frame, _ = _frame({"dominant_dosha": "kapha", "medical_history": ["diabetes"]})
    assert "honey" not in frame["meal_timing"]["wake_up_drink"].lower()
    assert "honey" not in frame["ayurvedic_tips"].lower()
    assert "honey" not in _named_foods(frame)


def test_a_coeliac_is_told_which_hing_to_buy():
    frame, _ = _frame({"dominant_dosha": "vata", "medical_history": ["celiac"]})
    hing = next(s for s in frame["spice_guide"] if s["name"] == "Asafoetida")
    assert "gluten-free" in hing["note"]
    frame, _ = _frame({"dominant_dosha": "vata"})
    assert "note" not in next(s for s in frame["spice_guide"] if s["name"] == "Asafoetida")


def test_fenugreek_seed_is_withheld_in_pregnancy():
    frame, _ = _frame({"dominant_dosha": "kapha", "pregnancy_or_nursing": True})
    assert "Fenugreek" not in {s["name"] for s in frame["spice_guide"]}
    assert any(w["item"] == "Fenugreek" for w in frame["withheld_guidance"])


def test_a_kidney_plan_gets_no_bedtime_milk():
    frame, _ = _frame({"dominant_dosha": "vata", "medical_history": ["kidney_disease"]})
    assert not {"milk_full_fat", "soy_milk", "almond_milk", "oat_milk"} & _named_foods(frame)


def test_every_spice_and_drink_names_a_real_food():
    from services import diet_nutrition as dn
    ids = set(dn.all_ids())
    for d in list(_WAKE_UP.values()) + list(_BEDTIME.values()):
        for drink in d:
            assert {c["food"] for c in drink["components"]} <= ids, drink["name"]
    for d in _SPICES.values():
        for name, _, fid, _ in d:
            assert fid is None or fid in ids, name


# ── The eating window ────────────────────────────────────────────────────────

def test_a_16_8_window_sets_the_times_and_keeps_calories_inside_it():
    frame, _ = _frame({"dominant_dosha": "vata"}, {"intermittent_fasting": "16:8"})
    mt = frame["meal_timing"]
    assert frame["eating_window"] == "16:8"
    assert mt["breakfast"].startswith("10:00") and "6:00" in mt["dinner"]
    assert mt["bedtime_drink"] is None and "6:00 PM" in mt["after_window"]
    assert [r["slot"] for r in frame["rituals"]] == ["wake_up"]
    assert frame["rituals"][0]["macros_approx"]["calories"] < 5


def test_the_brief_states_the_window_and_its_times():
    brief = build_brief({**_BASE, "dominant_dosha": "kapha"}, {"intermittent_fasting": "16:8"})
    assert "EATING WINDOW 16:8" in brief and "10:00 AM" in brief and "6:00 PM" in brief
    assert "adjust meal timing accordingly" not in brief


@pytest.mark.parametrize("profile", [
    {"medical_history": ["diabetes"]}, {"pregnancy_or_nursing": True},
    {"bmi_category": "underweight"}, {"age": 74}, {"age": 15}])
def test_a_long_window_is_withheld_from_those_who_are_not_fasted(profile):
    """A diabetic who declared 16:8 and no fasting day used to get the window: the
    check read through `fasting_withheld_reason`, which is None without a fasting day."""
    p = {**_BASE, "dominant_dosha": "pitta", **profile}
    prefs = {"intermittent_fasting": "16:8"}
    frame, _ = _frame(p, prefs)
    assert frame["eating_window"] is None
    assert "not applied" in frame["meal_timing"]["window_notice"]
    assert "EATING WINDOW 16:8" not in build_brief(p, prefs)


def test_a_child_is_given_no_window_at_all():
    frame, _ = _frame({"dominant_dosha": "pitta", "age": 12}, {"intermittent_fasting": "12:12"})
    assert frame["eating_window"] is None


def test_twelve_hours_overnight_is_an_ordinary_night_for_an_adult_diabetic():
    frame, _ = _frame({"dominant_dosha": "pitta", "medical_history": ["diabetes"]},
                      {"intermittent_fasting": "12:12"})
    assert frame["eating_window"] == "12:12"


def test_the_old_unscreened_tables_are_gone():
    for name in ("MEAL_TIMING", "DOSHA_SPICES", "AYUR_TIPS"):
        assert not hasattr(bb, name), name


# ── Counted, on both paths ───────────────────────────────────────────────────

@pytest.fixture
def _no_rag(monkeypatch):
    async def none(*a, **k):
        return []
    monkeypatch.setattr(gen.rag_pipeline, "query", none)


@pytest.mark.asyncio
async def test_the_llm_plan_carries_the_screened_frame_on_every_day(monkeypatch, _no_rag):
    monkeypatch.setattr(gen.llm_client, "generate", make_fake([]))
    plan = await gen.generate_diet_plan_llm({**_BASE, "dominant_dosha": "kapha"},
                                            {"dietary_restrictions": ["jain"]})
    assert "honey" not in plan["meal_timing"]["wake_up_drink"].lower()
    assert plan["daily_rituals"] and plan["withheld_guidance"]
    for w in plan["diet_weeks"]:
        for day in w["daily_plan"].values():
            assert [r["slot"] for r in day["rituals"]] == [r["slot"] for r in plan["daily_rituals"]]


@pytest.mark.asyncio
async def test_the_fallback_plan_carries_it_too(monkeypatch):
    async def none(*a, **k):
        return None

    async def same(raw, *a, **k):
        return raw

    async def empty(*a, **k):
        return {}
    monkeypatch.setattr(gen, "generate_diet_plan_llm", none)
    monkeypatch.setattr("services.diet_plan_enricher.enrich_diet_plan", same)
    monkeypatch.setattr("services.ahara_safety.classify_condition_apathya_llm", empty)
    plan = await gen.build_diet_plan({**_BASE, "dominant_dosha": "vata"}, {"dietary_type": "vegan"})
    assert plan["generation_method"] == "rule_engine"
    assert "milk_full_fat" not in {c["food"] for r in plan["daily_rituals"] for c in r["components"]}
    day = plan["diet_weeks"][0]["daily_plan"]["Monday"]
    assert {r["slot"] for r in day["rituals"]} == {"wake_up", "bedtime"}
