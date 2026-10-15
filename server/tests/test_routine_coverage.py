"""What a 600-plan sweep, a per-condition probe and five plans read whole found in
the daily routine.

Every slot carried a fixed clock time and only the wake row moved, so a late riser
was woken at 7:30 with rituals at 6:15 (23% of days ran backwards), a Kapha adult
had 6½ hours in bed and an eleven-year-old 5.8. 62 of 70 onboarding conditions
changed nothing, because the table was keyed by names onboarding does not send.
No herb, oil, food or exercise label passed a gate, gym rest days were read as
45-minute workouts, and the AI coaching was sent empty facts and shown nowhere.
"""
import json
import random
import re
from pathlib import Path

import pytest

from services.routine_engine import (_extract_gym_schedule, _resolve_times,
                                     generate_routine_plan)
from services.routine_enricher import _snapshot, gate_routine_enrichment

_R = dict(wake_preference="natural", occupation_type="moderately_active",
          agni_type_self_report="assessed", intermittent_fasting="no", fasting_days=[])


def _plan(routine=None, diet=None, **profile):
    base = dict(id="t", age=35, gender="female", dominant_dosha="vata", medical_history=[])
    base.update(profile)
    return generate_routine_plan(base, {"routine": {**_R, **(routine or {})}, "diet": diet or {}})


def _mins(t):
    h, m, ap = re.match(r"(\d+):(\d+) (AM|PM)", t).groups()
    h = int(h) % 12 + (12 if ap == "PM" else 0)
    return h * 60 + int(m)


def _text(plan):
    return json.dumps(plan, default=str).lower()


# ── Time ──────────────────────────────────────────────────────────────────────

def test_no_day_runs_backwards_and_nobody_is_short_of_sleep():
    rng = random.Random(7)
    for _ in range(300):
        age = rng.choice([10, 12, 14, 17, 25, 45, 62, 80])
        plan = _plan(routine={"wake_preference": rng.choice(["early", "natural", "late"]),
                              "intermittent_fasting": rng.choice(["no", "14:10", "16:8"])},
                     age=age, dominant_dosha=rng.choice(["vata", "pitta", "kapha"]),
                     current_season=rng.choice(["vasanta", "grishma", "varsha", "sharad", "hemanta", "shishira"]))
        din = plan["dinacharya_protocol"]
        need = 9 if age < 13 else 8 if age < 18 else 7
        assert din["sleep_hours"] >= need, (age, din["sleep_hours"])
        for day in plan["weekly_routine"]:
            times = [_mins(s["time"]) for s in day["timeline"]]
            assert times == sorted(times), [(s["time"], s["activity"]) for s in day["timeline"]]
            assert day["timeline"][0]["time"] == din["wake_time"]
            assert day["timeline"][-1]["time"] == din["sleep_time"]


def test_a_late_riser_is_woken_inside_the_band_the_form_promised():
    for dosha in ("vata", "pitta", "kapha"):
        wake = _mins(_plan(routine={"wake_preference": "late"}, dominant_dosha=dosha)
                     ["dinacharya_protocol"]["wake_time"])
        assert 6 * 60 + 30 <= wake <= 7 * 60 + 30, (dosha, wake)


def test_a_child_is_not_woken_before_dawn_to_keep_a_kapha_hour():
    plan = _plan(age=11, dominant_dosha="kapha", current_season="hemanta", routine={"wake_preference": "early"})
    din = plan["dinacharya_protocol"]
    assert din["sleep_hours"] >= 9.5 and din["sleep_notice"]
    assert "Brahma Muhurta" not in plan["weekly_routine"][0]["timeline"][0]["activity"]


def test_a_crowded_day_compresses_instead_of_overlapping():
    slots = [{"at": ("wake", 0), "min": 120, "activity": "a", "type": "x"},
             {"at": ("clock", "6:00"), "min": 0, "activity": "b", "type": "x"}]
    out = _resolve_times(slots, 5 * 60, 22 * 60)
    assert [o["time"] for o in out] == ["5:00 AM", "7:00 AM"]


def test_reflux_gets_three_hours_between_dinner_and_bed():
    plan = _plan(medical_history=["acid_reflux"], dominant_dosha="pitta")
    tl = plan["weekly_routine"][0]["timeline"]
    dinner = next(s for s in tl if s.get("meal_type") == "dinner")
    assert _mins(tl[-1]["time"]) - _mins(dinner["time"]) >= 180


def test_a_16_8_window_moves_the_first_meal():
    tl = _plan(routine={"intermittent_fasting": "16:8"}, dominant_dosha="pitta")["weekly_routine"][0]["timeline"]
    meals = [s for s in tl if s.get("meal_type")]
    first, dinner = meals[0], next(s for s in meals if s["meal_type"] == "dinner")
    assert _mins(dinner["time"]) + 30 - _mins(first["time"]) <= 8 * 60


# ── Who fasting is withheld from ──────────────────────────────────────────────

@pytest.mark.parametrize("profile", [
    dict(age=12), dict(pregnancy_or_nursing=True), dict(medical_history=["diabetes_type2"]),
    dict(current_medications=["glimepiride"]), dict(pregnancy_status="nursing", pregnancy_or_nursing=True),
])
def test_fasting_days_and_windows_are_withheld_from_those_they_endanger(profile):
    plan = _plan(routine={"fasting_days": ["Monday"], "intermittent_fasting": "16:8"}, **profile)
    assert plan["fasting_notice"] and plan["requested_fasting"] == ["Monday"]
    assert not any(d["is_fasting_day"] for d in plan["weekly_routine"])
    assert "intermittent fasting" not in _text(plan["weekly_routine"])


def test_a_fasting_day_that_is_not_a_weekday_is_said_not_silently_dropped():
    plan = _plan(routine={"fasting_days": ["Ekadashi"]})
    assert "Ekadashi" in plan["fasting_notice"]


# ── Conditions ────────────────────────────────────────────────────────────────

# Nothing about waking, bathing, eating, moving or sleeping changes for these.
_NO_DAILY_CHANGE = {"ocd", "alopecia"}


def _onboarding_conditions():
    js = Path(__file__).resolve().parents[2] / "client" / "src" / "constants" / "conditions.js"
    return list(dict.fromkeys(re.findall(r"id: '([a-z_0-9]+)'", js.read_text())))


def _strip(plan):
    plan = dict(plan)
    plan.pop("plan_id"), plan.pop("generated_at")
    return plan


def test_every_onboarding_condition_changes_the_routine_or_is_exempt_with_reason():
    base = _strip(_plan(dominant_dosha="kapha", age=40))
    dead = [c for c in _onboarding_conditions()
            if _strip(_plan(dominant_dosha="kapha", age=40, medical_history=[c])) == base]
    assert set(dead) <= _NO_DAILY_CHANGE, dead


def test_onboarding_ids_reach_the_notes_not_just_the_old_spellings():
    """The table was keyed `diabetes` and `hypothyroid`; onboarding sends
    `diabetes_type2` and `hypothyroidism`."""
    tl = _text(_plan(medical_history=["diabetes_type2"])["weekly_routine"][0])
    assert "10-minute walk" in tl
    tl = _text(_plan(medical_history=["hypothyroidism"])["weekly_routine"][0])
    assert "thyroid tablet" in tl


@pytest.mark.parametrize("cond,cap", [("heart_disease", "gentle"), ("hypertension", "moderate"),
                                      ("glaucoma", "moderate"), ("inguinal_hernia", "moderate"),
                                      ("epilepsy", "moderate")])
def test_a_kapha_week_holds_no_hiit_for_a_condition_it_endangers(cond, cap):
    plan = _plan(dominant_dosha="kapha", medical_history=[cond])
    assert plan["exercise_limits"]["cap"] == cap
    labels = " ".join(d["exercise_label"] for d in plan["weekly_routine"])
    assert not re.search(r"HIIT|Run\b|Vigorous|Power", labels), labels


def test_pregnancy_caps_exercise_and_epilepsy_says_never_swim_alone():
    labels = " ".join(d["exercise_label"] for d in _plan(dominant_dosha="kapha", pregnancy_or_nursing=True)["weekly_routine"])
    assert not re.search(r"HIIT|Run\b|Vigorous", labels)
    assert "never swim alone" in _text(_plan(dominant_dosha="pitta", medical_history=["epilepsy"]))


def test_knee_osteoarthritis_is_low_impact():
    labels = " ".join(d["exercise_label"] for d in
                      _plan(dominant_dosha="kapha", medical_history=["osteoarthritis"])["weekly_routine"])
    assert "Run" not in labels and "HIIT" not in labels


# ── Herbs, oils, foods, medicines ─────────────────────────────────────────────

@pytest.mark.parametrize("dosha,herb,profile", [
    ("kapha", "triphala", dict(pregnancy_or_nursing=True)),
    ("vata", "ashwagandha", dict(medical_history=["hyperthyroidism"])),
    ("vata", "ashwagandha", dict(age=11)),
    ("pitta", "brahmi", dict(age=70, current_medications=["clonazepam"])),
])
def test_an_evening_herb_is_withheld_where_the_formulary_bars_it(dosha, herb, profile):
    plan = _plan(dominant_dosha=dosha, **profile)
    evening = _text(plan["dinacharya_protocol"]["evening_rituals"])
    timeline = _text([s for d in plan["weekly_routine"] for s in d["timeline"]])
    assert herb not in evening and herb not in timeline
    assert any(herb in w["practice"].lower() for w in plan["dinacharya_protocol"]["withheld_practices"])


def test_trikatu_leaves_the_agni_note_for_acid_reflux():
    plan = _plan(dominant_dosha="kapha", agni_type="kapha", medical_history=["acid_reflux"])
    assert "trikatu" not in _text(plan["weekly_routine"][0])


def test_a_sesame_allergy_reaches_every_oil_and_dairy_every_drink():
    sesame = _plan(dominant_dosha="vata", allergies=["sesame"])
    assert "sesame" not in _text({k: v for k, v in sesame.items() if k != "seasonal_ritucharya"})
    dairy = _plan(dominant_dosha="vata", allergies=["dairy"])
    drinks = [s for d in dairy["weekly_routine"] for s in d["timeline"] if s.get("icon") == "milk"]
    assert drinks and all("1 cup warm milk" not in s["description"] for s in drinks)
    assert not any("ghee" in f for f in dairy["meal_guidance"]["breakfast"]["favour"])


def test_a_vegan_is_not_served_milk():
    plan = _plan(dominant_dosha="pitta", diet={"dietary_type": "vegan"})
    assert "1 cup warm milk" not in _text(plan["dinacharya_protocol"]["evening_rituals"])


def test_medicines_change_the_day():
    thyroid = _text(_plan(current_medications=["thyronorm 50"])["weekly_routine"][0]["timeline"][0])
    assert "thyroid tablet" in thyroid
    kapha = _plan(dominant_dosha="kapha", current_medications=["glimepiride"])
    breakfast = next(s for s in kapha["weekly_routine"][0]["timeline"] if s.get("meal_type") == "breakfast")
    assert "skip if not genuinely hungry" not in breakfast["description"].lower()
    warfarin = _plan(dominant_dosha="kapha", current_medications=["warfarin"])
    garshana = next(r for r in warfarin["dinacharya_protocol"]["morning_rituals"] if r["name"] == "Garshana")
    assert garshana["withheld"]


def test_a_withheld_ritual_is_not_named_in_the_timeline():
    child = _plan(age=11, dominant_dosha="vata")
    rituals = next(s for s in child["weekly_routine"][0]["timeline"] if s["activity"] == "Dinacharya Rituals")
    assert "nasya" not in rituals["description"].lower() and "kavala" not in rituals["description"].lower()
    elder = _plan(age=72, dominant_dosha="kapha")
    bath = next(s for s in elder["weekly_routine"][0]["timeline"] if "Abhyanga" in s["activity"])
    assert "Garshana" not in bath["activity"] and "dry brushing" not in bath["description"]


def test_cleansing_therapies_are_not_offered_to_a_child_or_past_70():
    for age in (12, 75):
        practices = " ".join(_plan(age=age, current_season="sharad")["seasonal_ritucharya"]["seasonal_practices"])
        assert "Virechana" not in practices


def test_the_assessed_agni_is_used_unless_the_user_answered():
    assert _plan(agni_type="kapha")["dinacharya_protocol"]["agni_type"] == "manda"
    assert _plan(agni_type="kapha", routine={"agni_type_self_report": "tikshna"})["dinacharya_protocol"]["agni_type"] == "tikshna"


# ── Gym and yoga integration ──────────────────────────────────────────────────

def test_a_gym_recovery_day_is_a_rest_day():
    sched = _extract_gym_schedule({"four_week_plan": [{"days": [
        {"day_name": "Monday", "type": "strength", "focus": "Full Body", "estimated_duration_minutes": 48},
        {"day_name": "Tuesday", "type": "recovery", "focus": "Rest & Recovery"}]}]})
    assert sched[1]["is_rest"] and sched[0]["ex_duration"] == "48 min"


def test_an_evening_yoga_plan_shares_a_gym_day():
    gym = {"four_week_plan": [{"days": [{"day_name": "Monday", "type": "strength", "focus": "Push",
                                         "estimated_duration_minutes": 50}]}]}
    yoga = {"four_week_plan": [{"days": [{"day_name": "Monday", "rest": False,
                                          "session": {"dosha_theme": "Calm", "total_duration_minutes": 30}}]}]}
    plan = generate_routine_plan(
        dict(id="t", age=30, gender="male", dominant_dosha="vata", medical_history=[]),
        {"routine": {**_R, "yoga_time_of_day": "evening"}}, gym_plan_data=gym, yoga_plan_data=yoga)
    acts = [s["activity"] for s in plan["weekly_routine"][0]["timeline"]]
    assert "Gym — Push" in acts and "Yoga — Calm" in acts
    assert acts.index("Gym — Push") < acts.index("Yoga — Calm")


# ── The narrative ─────────────────────────────────────────────────────────────

def test_the_enricher_is_sent_the_schedule_it_is_asked_to_explain():
    snap = _snapshot(_plan())
    assert snap["wake_time"] and snap["sleep_time"] and snap["morning_rituals"] and snap["meal_times"]


def test_the_gate_withholds_what_the_plan_withheld():
    prof = dict(id="t", age=29, gender="female", dominant_dosha="kapha", medical_history=["hypertension"],
                pregnancy_or_nursing=True, allergies=["dairy"])
    plan = generate_routine_plan(prof, {"routine": _R})
    out, withheld = gate_routine_enrichment(
        {"a": "Sip Triphala at night. Begin with Nasya. Walk after dinner. Avoid Triphala in pregnancy. "
              "Drink warm milk before bed. Try HIIT on Mondays."}, plan, prof)
    assert out["a"] == "Walk after dinner. Avoid Triphala in pregnancy."
    assert len(withheld) == 4
