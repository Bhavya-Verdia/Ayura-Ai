"""The Daily Routine PDF: one sheet per day, everything the screen shows, nothing that
prints as an empty box."""
import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from main import app
from services.auth_service import create_access_token
from services.routine_engine import generate_routine_plan
from services.routine_pdf import build_routine_pdf, exercise_limit_lines, plain, text

_PROFILES = [
    ({"id": "u1", "name": "Asha Rao", "age": 34, "gender": "female", "dominant_dosha": "pitta",
      "agni_type": "tikshna", "medical_history": ["acidity", "hypothyroidism"]},
     {"wake_preference": "early", "occupation_type": "sedentary", "agni_type_self_report": "tikshna"}),
    # many condition notes: the case that used to spill a row onto a second page
    ({"id": "u2", "name": "Ravi Kumar", "age": 68, "gender": "male", "dominant_dosha": "vata",
      "agni_type": "vishama", "medical_history": ["diabetes", "hypertension", "arthritis", "insomnia"]},
     {"wake_preference": "late", "occupation_type": "very_active", "agni_type_self_report": "vishama"}),
]


def _text(pdf: bytes) -> list[str]:
    return [p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages]


def _heading(page: str) -> str:
    """The page's first line that is not the footer."""
    return next(line for line in page.splitlines()
                if line.strip() and not line.startswith("Ayura AI ·") and not line.startswith("Page "))


@pytest.mark.parametrize("profile,prefs", _PROFILES)
def test_the_week_is_a_cover_one_sheet_per_day_and_the_food_page(profile, prefs):
    plan = generate_routine_plan(profile, prefs)
    pages = _text(build_routine_pdf(plan, profile["name"], "all", 0, datetime(2026, 10, 17)))
    assert len(pages) == 1 + 7 + 1
    for i, day in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")):
        assert _heading(pages[1 + i]) == day, (day, pages[1 + i][:80])
        assert "Sleep" in pages[1 + i]           # the last row stays on its own day's sheet


def test_today_is_one_day_sheet():
    profile, prefs = _PROFILES[0]
    plan = generate_routine_plan(profile, prefs)
    pages = _text(build_routine_pdf(plan, "Asha", "today", 4, datetime(2026, 10, 17)))
    assert len(pages) == 3 and _heading(pages[1]) == "Friday"
    assert all(_heading(p) != "Monday" for p in pages)


def test_what_the_screen_shows_is_on_the_page():
    profile, prefs = _PROFILES[0]
    plan = generate_routine_plan(profile, prefs)
    whole = "\n".join(_text(build_routine_pdf(plan, "Asha", "all", 0)))
    day = plan["weekly_routine"][0]
    for item in day["timeline"]:
        assert item["time"] in whole and item["activity"].split(" ")[0] in whole
    notes = [n for it in day["timeline"] for n in (it.get("condition_notes") or [])]
    assert notes and notes[0].split(":")[0] in whole        # e.g. "Hypothyroidism"
    assert plan["dinacharya_protocol"]["morning_rituals"][0]["name"] in whole
    assert "Meals" in whole and "Season" in whole


def test_exercise_limits_are_sentences_not_flags():
    lines = exercise_limit_lines({"cap": "moderate", "low_impact": True, "no_swim_alone": False,
                                  "reasons": ["high blood pressure"]})
    assert lines == ["Exercise is kept to a pace you can talk through and low impact, "
                     "because of high blood pressure."]
    assert exercise_limit_lines({"cap": None, "low_impact": False, "reasons": []}) == []


def test_characters_the_fonts_cannot_draw_are_folded_not_boxed():
    assert plain("Śirodhārā → Nasya ≥ 2") == "Sirodhara -> Nasya >= 2"
    assert plain("Ghee — ½ tsp · 5 min") == "Ghee — 1/2 tsp · 5 min"   # cp1252 keeps these
    assert text("salt < 5 g & sugar") == "salt &lt; 5 g &amp; sugar"


# ── Endpoint ────────────────────────────────────────────────────────────────

@pytest.fixture
def client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Asha Rao", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_verified": True,
        "onboarding_complete": True, "timezone": "Asia/Kolkata",
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    c = TestClient(app)
    c.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return c


def test_the_endpoint_serves_the_latest_routine(client, mock_db):
    plan = generate_routine_plan(*_PROFILES[0])
    mock_db.plan_history.find_one = AsyncMock(return_value={"plan_data": {"routine_plan": plan}})
    r = client.get("/api/export/routine-pdf?day=today")
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    assert "ayura_daily_routine_today.pdf" in r.headers["content-disposition"]
    flt = mock_db.plan_history.find_one.call_args[0][0]
    assert flt == {"user_id": "test-uuid-1234", "plan_type": "routine"}


def test_no_routine_or_a_bad_day_is_refused(client, mock_db):
    mock_db.plan_history.find_one = AsyncMock(return_value=None)
    assert client.get("/api/export/routine-pdf").status_code == 404
    assert client.get("/api/export/routine-pdf?day=9").status_code == 422
