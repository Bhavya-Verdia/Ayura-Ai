import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from main import app
from services.auth_service import create_access_token

@pytest.mark.asyncio
async def test_get_profile_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/profile/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_profile_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/profile/me", json={"age": 25})
    assert response.status_code == 401


def test_update_profile_normalizes_free_text_conditions(mock_db):
    """Onboarding's free-text conditions ('high blood pressure', 'GERD') must be
    normalized to canonical vocabulary at the write boundary, so downstream safety
    constraints actually match. Unknown conditions are kept as slugs."""
    mock_db.users.update_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))

    res = client.put("/api/profile/me", json={
        "medical_history": ["high blood pressure", "GERD", "Sarcoidosis"],
    })
    assert res.status_code == 200

    set_doc = mock_db.users.update_one.call_args.args[1]["$set"]
    assert set_doc["medical_history"] == ["hypertension", "acid_reflux", "sarcoidosis"]


def test_unanswered_pickers_do_not_reject_the_whole_profile(mock_db):
    """An unanswered picker arrives as "", which matched none of the enum
    patterns — so the entire onboarding save came back 422 and wrote nothing.
    The rest of the form must still land, with the blanks read as unanswered."""
    mock_db.users.update_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))

    res = client.put("/api/profile/me", json={
        "name": "Fresh Signup", "gender": "male", "age": 24,
        "height_cm": 175, "weight_kg": 70,
        "goal": "", "dominant_dosha": "", "satmya": "", "timezone": "",
    })
    assert res.status_code == 200

    set_doc = mock_db.users.update_one.call_args.args[1]["$set"]
    assert set_doc["age"] == 24 and set_doc["height_cm"] == 175
    assert set_doc["goal"] is None and set_doc["dominant_dosha"] is None
    # No dosha and no scores means onboarding is genuinely not finished yet.
    assert "onboarding_complete" not in set_doc
