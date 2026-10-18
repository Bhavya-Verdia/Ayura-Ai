"""Tests for routine_engine gym/yoga schedule extraction robustness.

Regression for the code-review finding where a single malformed day (blank/unknown
day_name, or an explicit null session duration) raised inside the extractor and the
bare `except` discarded the ENTIRE week's schedule instead of just that day.
"""
import pytest

from services.routine_engine import _extract_yoga_schedule, _extract_gym_schedule


def test_yoga_schedule_skips_unknown_day_keeps_rest():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Monday", "session": {"total_duration_minutes": 60, "dosha_theme": "Vata"}},
        {"day_name": "", "session": {"total_duration_minutes": 45}},          # malformed → skip
        {"day_name": "Wednesday", "rest": True},
    ]}]}
    out = _extract_yoga_schedule(plan)
    assert 0 in out and out[0]["ex_duration"] == "60 min"
    assert 2 in out and out[2]["is_rest"] is True
    assert 1 not in out  # blank day skipped, surrounding days survive


def test_yoga_schedule_null_duration_defaults_not_crash():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Tuesday", "session": {"total_duration_minutes": None, "dosha_theme": "Kapha"}},
    ]}]}
    out = _extract_yoga_schedule(plan)
    assert out[1]["ex_duration"] == "30 min"  # explicit null → default 30, no TypeError


def test_gym_schedule_skips_unknown_day_keeps_rest():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Funday", "focus": "Legs"},                # unknown weekday → skip
        {"day_name": "Friday", "focus": "Push"},
        {"day_name": "Sunday", "type": "rest"},
    ]}]}
    out = _extract_gym_schedule(plan)
    assert 4 in out and out[4]["gym_focus"] == "Push"
    assert 6 in out and out[6]["is_rest"] is True
    assert len(out) == 2  # the unknown day did not poison the whole schedule


# ── Pregnancy ────────────────────────────────────────────────────────────────

def _routine(pregnant, dosha="kapha"):
    from services.routine_engine import generate_routine_plan
    return generate_routine_plan(
        {"id": "t", "age": 29, "gender": "female", "dominant_dosha": dosha,
         "weight_kg": 68, "height": 162, "bmi_category": "normal",
         "medical_history": [], "pregnancy_or_nursing": pregnant},
        {"wake_time": "06:00", "sleep_time": "22:00"})


_SHODHANA = ("virechana", "vamana", "basti", "nasya")
_WITHHELD_LANGUAGE = ("withheld", "contraindicated", "set aside", "no virechana",
                      "not undertaken", "omitted", "skip")


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_no_shodhana_is_recommended_during_pregnancy(dosha):
    """This engine handled twenty condition tokens and had no concept of
    pregnancy — the word did not appear in the file. A pregnant practitioner's
    autumn Ritucharya read "Virechana (Pitta purge) classically recommended",
    spring offered "Vamana if supervised", monsoon "Basti karma", and Nasya
    reached her every morning.

    `panchakarma_engine` has always refused: "Pregnancy / nursing — Shodhana
    contraindicated". Virechana IS Shodhana. Both engines read the same profile;
    this one was never asked.
    """
    import json
    import re

    blob = json.dumps(_routine(True, dosha), default=str)
    offending = []
    for match in re.finditer(r'"[^"]*(?:%s)[^"]*"' % "|".join(_SHODHANA), blob, re.I):
        text = match.group(0).strip('"')
        if len(text) > 15 and not any(w in text.lower() for w in _WITHHELD_LANGUAGE):
            offending.append(text[:90])
    assert not offending, offending


def test_the_same_instruction_is_gated_in_every_structure_that_carries_it():
    """The ritual list, the seasonal guidance and the weekly timeline each hold
    their OWN copy of the Nasya instruction. Gating the first two left the third
    untouched — seven times, once per day — which is exactly how prose has
    escaped a gate everywhere else in this codebase."""
    import json

    plan = _routine(True)
    timeline_text = json.dumps(plan["weekly_routine"], default=str).lower()
    assert "nasya with warm mustard oil" not in timeline_text
    assert "nasya, kavala" not in timeline_text


def test_a_practitioner_who_is_not_pregnant_keeps_the_full_routine():
    """The gate withholds; it does not water the feature down for everyone."""
    plan = _routine(False)
    nasya = [r for r in plan["dinacharya_protocol"]["morning_rituals"]
             if r["name"] == "Nasya"]
    assert nasya and "drops" in nasya[0]["instruction"]
    assert not plan["dinacharya_protocol"].get("pregnancy_notices")


def test_a_withheld_practice_says_that_it_was_withheld():
    plan = _routine(True)
    notices = plan["dinacharya_protocol"]["pregnancy_notices"]
    assert notices
    assert any("Shodhana" in n for n in notices)


# ── The season's Agni is not the person's ─────────────────────────────────────

@pytest.mark.parametrize("season", ["sharad", "shishira", "hemanta", "vasanta", "grishma", "varsha"])
def test_every_seasonal_agni_note_names_its_season(season):
    """'Agni is strong' with no season read as a statement about the person, printed
    beside 'Your Agni type is Vishama'."""
    from services.routine_engine import _SEASON_MAP, _build_meal_guidance
    note = _build_meal_guidance("vata", season, "sama")["seasonal_note"]
    assert note.startswith("In " + _SEASON_MAP[season]["label"].split(" (")[0] + ",")


@pytest.mark.parametrize("own", ["manda", "vishama"])
@pytest.mark.parametrize("season", ["sharad", "hemanta"])
def test_a_strong_season_defers_to_a_weak_or_irregular_agni(season, own):
    from services.routine_engine import _build_meal_guidance
    note = _build_meal_guidance("vata", season, own)["seasonal_note"]
    assert "not you" in note and "regular and moderate" in note


@pytest.mark.parametrize("own", ["sama", "tikshna"])
def test_a_strong_season_says_nothing_extra_when_agni_agrees(own):
    from services.routine_engine import _build_meal_guidance
    assert "not you" not in _build_meal_guidance("pitta", "sharad", own)["seasonal_note"]


# ── The day's own lines name food, and are screened like the meal card ────────

def _plan(dosha, conditions, agni="", allergies=None):
    from services.routine_engine import generate_routine_plan
    return generate_routine_plan(
        {"id": "t", "age": 42, "gender": "female", "dominant_dosha": dosha,
         "medical_history": conditions, "agni_type": agni, "allergies": allergies or [],
         "current_season": "sharad"},
        {"routine": {"agni_type_self_report": agni or "assessed"}})


def _day_lines(plan):
    proto = plan["dinacharya_protocol"]
    out = [r["instruction"] for r in proto["morning_rituals"] + proto["evening_rituals"]]
    for day in plan["weekly_routine"]:
        for s in day["timeline"]:
            out += [s.get("description") or "", s.get("agni_note") or ""]
    return out + [plan["meal_guidance"]["agni_note"]]


def test_a_diabetic_is_not_offered_dates_by_the_timeline():
    """The meal card withheld 'soaked dates or figs' while every 4 PM row of the week
    said 'Soaked dates, warm milk, or light soup' (found on production)."""
    plan = _plan("vata", ["diabetes"], "vishama")
    import re
    assert not [t for t in _day_lines(plan) if re.search(r"\bdates\b", t, re.I)]
    snack = next(s for s in plan["weekly_routine"][0]["timeline"] if s.get("meal_type") == "snack")
    assert "Warm milk or light soup." in snack["description"]
    assert "Warm broth — nothing raw or cold." in snack["agni_note"]
    assert any("dates" in w["reason"] for w in plan["meal_guidance"]["withheld"])


_PATIENTS = [(d, c, a) for d in ("vata", "pitta", "kapha")
             for c in (["diabetes"], ["acid_reflux"], ["kidney_disease"], ["obesity"],
                       ["hypothyroidism"], ["piles"], [])
             for a in ("manda", "tikshna", "vishama")]


@pytest.mark.parametrize("dosha,conditions,agni", _PATIENTS)
def test_no_food_a_day_line_still_names_is_withheld(dosha, conditions, agni):
    """Every option the tables govern that survives into the plan passes the same
    screen as the meal card, for this patient."""
    from services.routine_engine import _SLOT_FOOD_LISTS, _SLOT_FOOD_SWAPS, _screen_food_list
    text = " ".join(_day_lines(_plan(dosha, conditions, agni)))
    for phrase, options, _ in _SLOT_FOOD_LISTS:
        if phrase in text:
            assert not _screen_food_list(list(options), conditions, [], False)[1], phrase
    for phrase, food, _ in _SLOT_FOOD_SWAPS:
        if phrase.strip() and phrase in text:
            assert not _screen_food_list([food], conditions, [], False)[1], phrase


def test_every_governed_phrase_is_one_the_engine_writes():
    """A phrase that matches no template is decoration: the line it was written for
    goes on naming the food unscreened."""
    from services.routine_engine import (_SLOT_FOOD_LISTS, _SLOT_FOOD_SWAPS, _agni_notes,
                                         _template_slots, _MORNING_RITUALS_BASE,
                                         _EVENING_RITUALS_BASE)
    source = []
    for d in ("vata", "pitta", "kapha"):
        source += [s["description"] for s in _template_slots(d, "Wake", "6:00")]
        source += [r["instruction"] for r in _MORNING_RITUALS_BASE[d] + _EVENING_RITUALS_BASE[d]]
    for a in ("manda", "tikshna", "vishama"):
        for trikatu in (True, False):
            source += [v for v in _agni_notes(a, trikatu, False).values() if v]
    text = " ".join(source)
    for phrase, *_ in _SLOT_FOOD_LISTS + _SLOT_FOOD_SWAPS:
        assert phrase in text, phrase


def test_a_dairy_allergy_takes_milk_out_of_the_snack_cleanly():
    plan = _plan("vata", [], "vishama", ["dairy"])
    snack = next(s for s in plan["weekly_routine"][0]["timeline"] if s.get("meal_type") == "snack")
    assert "Soaked dates or light soup." in snack["description"]


def test_acidity_gets_no_ginger_from_the_rituals_or_the_agni_notes():
    plan = _plan("kapha", ["acid_reflux"], "manda")
    import re
    assert not [t for t in _day_lines(plan) if re.search(r"\bginger\b", t, re.I)]


def test_the_withheld_list_does_not_repeat_itself():
    for plan in (_plan("kapha", ["acid_reflux"], "manda"), _plan("vata", ["diabetes"], "vishama")):
        reasons = [w["reason"] for w in plan["meal_guidance"]["withheld"]
                   if w["meal"] == "day"]
        items = [(w["item"].lower(), w["reason"]) for w in plan["meal_guidance"]["withheld"]]
        assert len(items) == len(set(items))
        assert len(reasons) == len(set(reasons))


def test_the_blood_pressure_note_does_not_call_it_heart_disease():
    plan = _plan("vata", ["hypertension"])
    notes = [n for day in plan["weekly_routine"] for s in day["timeline"]
             for n in s.get("condition_notes") or []]
    assert notes and not [n for n in notes if "Hridaya" in n]
    assert any(n.startswith("High blood pressure: keep intensity moderate") for n in notes)


@pytest.mark.parametrize("dosha", ["vata", "pitta"])
def test_a_rest_day_names_its_abhyanga_once(dosha):
    """The rest slot was relabelled 'Abhyanga Focus Day', so the morning carried two
    Abhyanga rows, each with the bath notes."""
    plan = _plan(dosha, ["hypertension"])
    rest_days = [d for d in plan["weekly_routine"] if d["is_rest_day"]]
    assert rest_days
    for day in rest_days:
        rows = [s for s in day["timeline"] if "abhyanga" in s["activity"].lower()]
        assert len(rows) == 1, [s["activity"] for s in rows]
        assert any(s["activity"] == "Rest — no structured exercise" for s in day["timeline"])
