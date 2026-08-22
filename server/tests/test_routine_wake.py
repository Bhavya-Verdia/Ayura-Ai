"""`wake_preference` — collected, and read by nothing.

Every user got the wake time their Dosha and season dictated, whatever they had
answered. The field is honoured now, because the classical hour is an ideal and the
user's life is a fact — shift work, small children, a partner on another schedule.

What it must not do is honour the preference and keep the classical LABEL. 7:00 AM
is not Brahma Muhurta, and calling it that is the same fault as a card disagreeing
with the schedule underneath it.
"""
import pytest

import schemas.preferences_schema as S
from services.routine_engine import generate_routine_plan

DOSHAS = ["vata", "pitta", "kapha"]
SEASONS = ["shishira", "vasanta", "grishma", "varsha", "sharad", "hemanta"]


def _profile(**over):
    base = dict(
        id="t", age=32, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
        fitness_level="beginner", medical_history=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _plan(profile, wake_preference="natural"):
    prefs = S.RoutinePreferences().model_dump()
    prefs["wake_preference"] = wake_preference
    return generate_routine_plan(profile, {"routine": prefs, "diet": {}})


def _wake_row(plan):
    return next(x for x in plan["weekly_routine"][0]["timeline"]
                if x["type"] == "morning_routine")


def _minutes(t):
    h, m = map(int, t.replace(" AM", "").split(":"))
    return h * 60 + m


@pytest.mark.parametrize("dosha", DOSHAS)
def test_the_wake_preference_moves_the_wake_time(dosha):
    early = _plan(_profile(dominant_dosha=dosha, vikriti_dominant=dosha), "early")
    natural = _plan(_profile(dominant_dosha=dosha, vikriti_dominant=dosha), "natural")
    late = _plan(_profile(dominant_dosha=dosha, vikriti_dominant=dosha), "late")

    times = [_minutes(p["dinacharya_protocol"]["wake_time"]) for p in (early, natural, late)]
    assert times[0] < times[1] < times[2], times


@pytest.mark.parametrize("dosha", DOSHAS)
def test_the_timeline_and_the_protocol_agree_on_the_hour(dosha):
    """The dinacharya block computed its own wake time from the same table and would
    otherwise print the classical hour beside a timeline showing the shifted one."""
    for preference in ("early", "natural", "late"):
        plan = _plan(_profile(dominant_dosha=dosha, vikriti_dominant=dosha), preference)
        assert _wake_row(plan)["time"] == plan["dinacharya_protocol"]["wake_time"]


@pytest.mark.parametrize("dosha", DOSHAS)
@pytest.mark.parametrize("season", SEASONS)
def test_the_label_stops_saying_brahma_muhurta_once_it_is_not(dosha, season):
    """Brahma Muhurta is the pre-dawn window — practically, before 6 AM. A row at
    6:15 headed "Brahma Muhurta" is a label contradicting its own timestamp."""
    for preference in ("early", "natural", "late"):
        plan = _plan(
            _profile(dominant_dosha=dosha, vikriti_dominant=dosha, current_season=season),
            preference)
        row = _wake_row(plan)
        is_brahma = "Brahma Muhurta" in row["activity"]
        assert is_brahma == (_minutes(row["time"]) < 6 * 60), (season, dosha, preference, row["time"])


def test_a_late_start_says_what_it_costs():
    plan = _plan(_profile(), "late")
    notice = plan["dinacharya_protocol"]["wake_notice"]
    assert notice and "past Brahma Muhurta" in notice
    assert plan["dinacharya_protocol"]["wake_time"] in notice


def test_no_notice_when_the_hour_is_still_classical():
    """The notice has to mean something, so it cannot appear on every plan."""
    for preference in ("early", "natural"):
        assert _plan(_profile(), preference)["dinacharya_protocol"]["wake_notice"] is None


@pytest.mark.parametrize("season", SEASONS)
def test_kapha_stops_calling_it_non_negotiable_while_scheduling_it(season):
    """The Kapha wake instruction reads "Rise BEFORE Kapha Kala (6-10 AM) ...
    Non-negotiable." Once a preference puts the time inside that window, printing it
    unchanged asserts the opposite of the schedule beside it — and calls the thing it
    is doing non-negotiable while doing it.
    """
    plan = _plan(
        _profile(dominant_dosha="kapha", vikriti_dominant="kapha", current_season=season), "late")
    row = _wake_row(plan)
    inside_kapha_kala = _minutes(row["time"]) >= 6 * 60

    if inside_kapha_kala:
        assert "Non-negotiable" not in row["description"]
        assert "inside Kapha Kala" in row["description"]
    else:
        assert "Non-negotiable" in row["description"]


def test_the_elderly_shift_still_applies_on_top():
    """`vriddha` already shifted the wake 30 minutes later. The preference stacks on
    that rather than replacing it."""
    young = _plan(_profile(age=32), "natural")["dinacharya_protocol"]["wake_time"]
    old = _plan(_profile(age=72), "natural")["dinacharya_protocol"]["wake_time"]
    assert _minutes(old) > _minutes(young)

    old_early = _plan(_profile(age=72), "early")["dinacharya_protocol"]["wake_time"]
    assert _minutes(old_early) < _minutes(old)
