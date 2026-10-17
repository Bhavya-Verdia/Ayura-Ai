"""Lab results: what a value is read as, what is refused, and where it goes.

The bands are the published ones and each boundary is pinned, because a band moved
by one unit is invisible in the UI and changes what a patient is told.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.lab_results import LAB_TESTS, catalogue, classify, latest_by_test, plausible


# ── Bands: every boundary, on the side the guideline puts it ───────────────────

@pytest.mark.parametrize("test,value,status", [
    ("hba1c", 5.6, "normal"), ("hba1c", 5.7, "borderline"), ("hba1c", 6.4, "borderline"),
    ("hba1c", 6.5, "high"),
    ("fasting_glucose", 69, "low"), ("fasting_glucose", 99, "normal"),
    ("fasting_glucose", 100, "borderline"), ("fasting_glucose", 126, "high"),
    ("tsh", 0.39, "low"), ("tsh", 4.0, "normal"), ("tsh", 4.1, "high"),
    ("vitamin_d", 19, "low"), ("vitamin_d", 20, "borderline"), ("vitamin_d", 30, "normal"),
    ("ldl", 99, "normal"), ("ldl", 100, "borderline"), ("ldl", 160, "high"),
    ("triglycerides", 150, "borderline"), ("triglycerides", 200, "high"),
    ("egfr", 90, "normal"), ("egfr", 60, "borderline"), ("egfr", 59, "low"),
    ("potassium", 5.0, "normal"), ("potassium", 5.1, "high"), ("potassium", 3.4, "low"),
    ("systolic_bp", 129, "normal"), ("systolic_bp", 130, "borderline"), ("systolic_bp", 140, "high"),
    ("diastolic_bp", 84, "normal"), ("diastolic_bp", 85, "borderline"), ("diastolic_bp", 90, "high"),
])
def test_published_boundaries(test, value, status):
    assert classify(test, value, "female")["status"] == status


def test_sex_specific_ranges():
    assert classify("hemoglobin", 12.5, "female")["status"] == "normal"
    assert classify("hemoglobin", 12.5, "male")["status"] == "low"
    assert classify("hdl", 45, "male")["status"] == "normal"
    assert classify("hdl", 45, "female")["status"] == "low"


@pytest.mark.parametrize("sex", ["other", None, ""])
def test_unrecorded_sex_takes_the_stricter_limit(sex):
    """Over-flagging costs a conversation with a doctor; a falsely reassuring
    'normal' costs more."""
    assert classify("hemoglobin", 12.5, sex)["status"] == "low"      # male low limit
    assert classify("hemoglobin", 16.0, sex)["status"] == "high"     # female high limit
    assert classify("hdl", 45, sex)["status"] == "low"               # female low limit
    assert classify("uric_acid", 6.5, sex)["status"] == "high"       # female high limit
    assert classify("ferritin", 180, sex)["status"] == "high"        # female high limit


def test_pregnancy_moves_or_withholds_a_range():
    assert classify("hemoglobin", 11.5, "female", pregnant=True)["status"] == "normal"
    tsh = classify("tsh", 3.5, "female", pregnant=True)
    assert tsh["status"] == "unclassified" and "pregnancy" in tsh["advice"]


@pytest.mark.parametrize("test,value", [
    ("potassium", 6.0), ("potassium", 2.9), ("fasting_glucose", 53), ("fasting_glucose", 250),
    ("hemoglobin", 7.9), ("systolic_bp", 180), ("diastolic_bp", 110), ("egfr", 14),
])
def test_values_that_should_not_wait_for_the_next_appointment(test, value):
    r = classify(test, value, "female")
    assert r["urgent"] and "today" in r["advice"]


def test_a_normal_reading_carries_no_advice_and_a_flagged_one_does():
    assert classify("hba1c", 5.2)["advice"] is None
    assert "doctor" in classify("hba1c", 6.0)["advice"]


def test_no_band_label_diagnoses():
    """A single reading is not a diagnosis; the label says which range it is in."""
    for key, spec in LAB_TESTS.items():
        for sex in ("male", "female", None):
            for _upper, _status, label in spec["bands"](sex, False) or []:
                assert not label.lower().startswith("you "), (key, label)
                assert "you have" not in label.lower(), (key, label)


def test_every_test_names_its_source_and_has_sane_bounds():
    for item in catalogue():
        assert item["source"] and item["unit"]
        assert item["min"] < item["max"]


def test_implausible_values_are_typos_not_results():
    assert not plausible("hba1c", 65)          # mmol/mol entered as %
    assert not plausible("fasting_glucose", 5.4)  # mmol/L entered as mg/dL
    assert plausible("fasting_glucose", 95)


def test_latest_by_test_keeps_the_newest_in_catalogue_order():
    rows = [
        {"test": "tsh", "taken_on": "2026-01-01", "value": 5},
        {"test": "hba1c", "taken_on": "2026-03-01", "value": 6.1},
        {"test": "hba1c", "taken_on": "2026-06-01", "value": 5.9},
    ]
    out = latest_by_test(rows)
    assert [r["test"] for r in out] == ["hba1c", "tsh"]
    assert out[0]["value"] == 5.9


def test_an_urgent_result_comes_first():
    rows = [{"test": "vitamin_d", "taken_on": "2026-10-01", "urgent": False},
            {"test": "potassium", "taken_on": "2026-10-01", "urgent": True}]
    assert latest_by_test(rows)[0]["test"] == "potassium"


# ── Routes ──────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True, "gender": "female",
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.lab_results = MagicMock()
    mock_db.lab_results.insert_one = AsyncMock()
    mock_db.lab_results.count_documents = AsyncMock(return_value=0)
    mock_db.lab_results.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


def test_a_result_is_stored_and_read_back_with_its_band(auth_client, mock_db):
    r = auth_client.post("/api/labs", json={"test": "hba1c", "value": 6.1,
                                            "taken_on": date.today().isoformat()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "borderline" and body["unit"] == "%"
    # The test's name and the band's wording are separate fields; one used to
    # overwrite the other.
    assert body["label"] == "HbA1c" and body["reading"] == "In the prediabetes range"
    doc = mock_db.lab_results.insert_one.call_args[0][0]
    assert doc["user_id"] == "test-uuid-1234"
    assert "status" not in doc  # bands are applied on read, never stored


@pytest.mark.parametrize("payload", [
    {"test": "made_up", "value": 1},
    {"test": "hba1c", "value": 65},
    {"test": "hba1c", "value": 6, "taken_on": (date.today() + timedelta(days=2)).isoformat()},
])
def test_unknown_implausible_or_future_results_are_refused(auth_client, payload):
    payload = {"taken_on": date.today().isoformat(), **payload}
    assert auth_client.post("/api/labs", json=payload).status_code == 422


def test_deleting_is_scoped_to_the_owner(auth_client, mock_db):
    mock_db.lab_results.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    assert auth_client.delete("/api/labs/someone-elses").status_code == 404
    assert mock_db.lab_results.delete_one.call_args[0][0]["user_id"] == "test-uuid-1234"


def test_the_handoff_pdf_carries_lab_results():
    from routes.export import _build_pdf
    from schemas.user_schema import UserDocument
    user = UserDocument(_id="u1", email="a@b.c", name="Asha", gender="female",
                        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    labs = [{"test": "hba1c", "label": "HbA1c", "unit": "%", "value": 6.1,
             "taken_on": "2026-10-01", **classify("hba1c", 6.1, "female")}]
    pdf = _build_pdf(user, {}, "today", labs)
    if pdf is None:
        pytest.skip("reportlab not installed")
    assert pdf[:4] == b"%PDF" and len(pdf) > len(_build_pdf(user, {}, "today", []))
