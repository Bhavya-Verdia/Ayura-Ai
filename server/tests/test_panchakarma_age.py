"""Age is read as a clinical input, not only as a window.

The app accepts patients from 10. Before this, a healthy ten-year-old at a normal
BMI was barred as Atidurbala by the adult cut-off of 17; a thirteen-year-old in a
clinic was planned an adult Virechana at 30-60 ml of castor oil; every dose was an
adult dose; and everyone over 70 lost Matra Basti, the Basti written for the old.
"""
import re

import pytest

from services.panchakarma_engine import (
    _ATIDURBALA_BMI_CHILD,
    _atidurbala_bmi,
    generate_panchakarma_plan,
)


def _profile(**over):
    base = dict(id="t", age=40, gender="male", bmi=22, vikriti_dominant="pitta",
                fitness_level="advanced", medical_history=[], ama_indicator="none",
                ojas_level="medium")
    base.update(over)
    return base


def _prefs(**over):
    base = dict(setting="clinic", available_time_days=14, detox_experience="some",
                panchakarma_goal="detox")
    base.update(over)
    return base


def _elig(plan):
    return plan["clinical_decisions"]["shodhana_or_shamana"]


def _karma(plan):
    return plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]


def test_the_child_thresholds_rise_to_the_adult_figure():
    for sex in (0, 1):
        values = [_ATIDURBALA_BMI_CHILD[a][sex] for a in sorted(_ATIDURBALA_BMI_CHILD)]
        assert values == sorted(values) and values[-1] < 17.0
    assert _atidurbala_bmi(18, "male") == 17.0


@pytest.mark.parametrize("age,bmi", [(10, 16.5), (12, 17.0), (14, 18.0), (16, 19.0)])
def test_a_child_at_an_ordinary_weight_is_not_atidurbala(age, bmi):
    plan = generate_panchakarma_plan(_profile(age=age, bmi=bmi, weight_kg=40), _prefs())
    assert not any("Atidurbala" in r for r in _elig(plan)["reasons"])


def test_a_thin_child_still_is():
    plan = generate_panchakarma_plan(_profile(age=10, bmi=12.8, weight_kg=26), _prefs())
    assert _elig(plan)["type"] == "shamana"
    assert any("for age 10" in r for r in _elig(plan)["reasons"])


@pytest.mark.parametrize("age", [10, 12, 13, 15])
def test_under_sixteen_is_mild_only(age):
    plan = generate_panchakarma_plan(_profile(age=age, weight_kg=45), _prefs())
    assert _elig(plan)["type"] == "mridu_shodhana"
    assert _karma(plan) not in ("vamana", "raktamokshana")


def test_sixteen_is_not_restricted_by_age():
    plan = generate_panchakarma_plan(_profile(age=16, weight_kg=60), _prefs())
    assert not any("Age 16" in r for r in _elig(plan)["reasons"])


def _numbers(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text or "")]


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_a_child_is_given_a_childs_dose_of_everything_the_plan_quantifies(dosha):
    adult = generate_panchakarma_plan(_profile(age=30, weight_kg=70, vikriti_dominant=dosha),
                                      _prefs(setting="home"))
    child = generate_panchakarma_plan(_profile(age=13, weight_kg=35, vikriti_dominant=dosha),
                                      _prefs(setting="home"))
    adj = child["clinical_decisions"]["dose_adjustment"]
    assert adj and adj["factor"] == 0.5 and "Clark" in adj["basis"]
    assert adult["clinical_decisions"]["dose_adjustment"] is None
    assert any(w.startswith("CHILD'S DOSE") for w in child["clinical_decisions"]["safety_warnings"])

    for key, v in child["aushadha"].items():
        if isinstance(v, dict) and v.get("adult_dose"):
            assert max(_numbers(v["dose"])) < max(_numbers(v["adult_dose"])), key
    for d in child["snehana_protocol"]["dose_schedule"]:
        assert d["dose_ml"] <= 60
    for day in child["daily_schedule"]:
        for t in day["therapies"]:
            if str(t.get("id", "")).startswith("basti_matra"):
                assert "50–80 ml" not in " ".join(t.get("steps") or [str(t)])


def test_youngs_rule_when_the_weight_is_unknown():
    plan = generate_panchakarma_plan(_profile(age=12), _prefs())
    adj = plan["clinical_decisions"]["dose_adjustment"]
    assert adj["factor"] == 0.5 and "Young" in adj["basis"]


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_no_shilajit_or_guggulu_rasayana_for_a_child(dosha):
    plan = generate_panchakarma_plan(
        _profile(age=11, weight_kg=35, vikriti_dominant=dosha, medical_history=["obesity"]),
        _prefs(setting="home"))
    herb = str(plan["aushadha"]["rasayana"].get("herb") or "")
    assert "Shilajit" not in herb and "Guggulu" not in herb


@pytest.mark.parametrize("age", [61, 65, 70])
def test_no_emesis_from_sixty(age):
    """Charaka Siddhisthana 2: the Vriddha are not given Vamana; Jirna begins at 60."""
    young = generate_panchakarma_plan(
        _profile(age=45, vikriti_dominant="kapha"), _prefs(current_season="vasanta"))
    assert _karma(young) == "vamana"
    old = generate_panchakarma_plan(
        _profile(age=age, vikriti_dominant="kapha"), _prefs(current_season="vasanta"))
    assert _karma(old) != "vamana"


def test_home_nasya_is_pratimarsha_not_navana():
    plan = generate_panchakarma_plan(
        _profile(age=78, vikriti_dominant="kapha"), _prefs(setting="home"))
    names = [t.get("name", "") for d in plan["daily_schedule"] for t in d["therapies"]]
    assert any(n.startswith("Pratimarsha Nasya") for n in names)
    assert not any("Navana" in n for n in names)


def test_a_matra_basti_course_carries_no_gruel_ladder():
    """Matra Basti needs no Parihara (CS Si 4); its patients are often the frail."""
    plan = generate_panchakarma_plan(_profile(age=75, vikriti_dominant="vata"),
                                     _prefs(setting="home"))
    assert _karma(plan) == "basti_matra"
    assert plan["samsarjana_krama"] == []
    assert not any("Niruha" in w for w in plan["clinical_decisions"]["safety_warnings"])
