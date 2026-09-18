"""The Vaidya handoff PDF rendered the diet plan as truncated JSON.

`_build_pdf` turns each plan key into one table row holding
`json.dumps(value)[:400]`. A diet plan's `diet_weeks` is ~6 KB, so the practitioner
got **7%** of it — four hundred characters of escaped JSON where twenty-eight days of
meals should be — and the safety findings truncated as soon as there were more than
about two of them.

This is the artifact the whole clinical review depends on, and the diet plan is the
largest thing in it.
"""

import io
from datetime import datetime, timezone

import pytest

from routes.export import _build_pdf
from schemas.user_schema import UserDocument


def _pdf_text(plan_data):
    now = datetime.now(timezone.utc)
    user = UserDocument(_id="u1", email="t@t.com", name="Meera",
                        hashed_password="x", created_at=now, updated_at=now)
    raw = _build_pdf(user, plan_data, now.isoformat())
    try:
        from pypdf import PdfReader
    except ImportError:                      # pragma: no cover
        from PyPDF2 import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)


def _diet_plan():
    return {
        "energy_prescription": {"target_calories": 1440, "band": [1267, 1613],
                                "protein_floor_g": 63, "basis": "measured"},
        "therapeutic_arc": {
            "weeks": [{"phase": p} for p in
                      ("Ama Pachana", "Langhana", "Rukshana", "Sthairya")],
            "withheld": ["Brimhana — Charaka Sutrasthana 23 names Prameha a disease "
                         "of over-nourishment"],
        },
        "diet_weeks": [
            {"week_number": w, "phase": "Ama Pachana", "daily_plan": {
                day: {"breakfast": {"meal_name": "Moong Dal Chilla with coriander"},
                      "lunch": {"meal_name": "Khichdi with lauki and cumin"},
                      "snack": {"meal_name": "Roasted Makhana"},
                      "dinner": {"meal_name": "Bottle gourd soup"},
                      "special_drink": {"name": "Coriander-Fennel Water"}}
                for day in ("Monday", "Tuesday", "Wednesday", "Thursday",
                            "Friday", "Saturday", "Sunday")}}
            for w in (1, 2, 3, 4)
        ],
        "condition_safety_alerts": [
            {"week": "Week 1", "day": f"Day{i}", "meal_slot": "breakfast",
             "condition": "Diabetes (Prameha / Madhumeha)", "food": f"flagged{i}"}
            for i in range(7)
        ],
        "withheld_recommendations": [
            {"item": "Soaked figs in limited quantity", "food": "figs",
             "reason": "Apathya in Prameha"}],
        "conditions_without_food_floor": ["lupus"],
        "conditions_screened_by_terms_only": ["gout"],
    }


def test_the_meals_reach_the_practitioner():
    text = _pdf_text({"diet_plan": _diet_plan()})
    for probe in ("Moong Dal Chilla", "Khichdi", "Roasted Makhana",
                  "Coriander-Fennel Water"):
        assert probe in text, probe
    # All four weeks, not just whatever fitted in 400 characters.
    for week in ("Week 1", "Week 2", "Week 3", "Week 4"):
        assert week in text, week


def test_every_safety_finding_survives_not_the_first_two():
    """A truncated list of flagged meals is worse than none — it reads as the whole
    list."""
    text = _pdf_text({"diet_plan": _diet_plan()})
    for i in range(7):
        assert f"flagged{i}" in text, i


def test_the_withheld_item_is_named_not_just_its_food_word():
    """"figs" alone loses what was actually taken off the patient's list."""
    assert "Soaked figs" in _pdf_text({"diet_plan": _diet_plan()})


def test_the_coverage_caveats_reach_the_reviewer():
    """The two statements a reviewer most needs: what could not be screened at all,
    and what was screened only against a term list."""
    text = _pdf_text({"diet_plan": _diet_plan()})
    assert "lupus" in text
    assert "gout" in text


def test_the_prescription_and_the_arc_are_stated():
    text = _pdf_text({"diet_plan": _diet_plan()})
    assert "1440" in text
    assert "Ama Pachana" in text
    assert "Brimhana" in text          # the phase withheld, and why


def test_a_plan_with_nothing_flagged_still_renders():
    text = _pdf_text({"diet_plan": {
        "diet_weeks": [{"week_number": 1, "daily_plan": {
            "Monday": {"lunch": {"meal_name": "Khichdi"}}}}]}})
    assert "Khichdi" in text


def test_the_other_features_keep_the_generic_renderer():
    """Only the diet section is special-cased; a gym plan must still render."""
    text = _pdf_text({"gym_plan": {"weekly_schedule": [{"day_name": "Monday",
                                                       "focus": "Upper body"}]}})
    assert "Fitness" in text or "Upper body" in text
