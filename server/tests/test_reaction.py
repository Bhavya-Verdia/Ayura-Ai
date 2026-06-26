"""
Tests for the adverse-reaction reporting loop (POST /plans/{plan_type}/report-reaction).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token


@pytest.fixture
def client():
    yield TestClient(app)


def _auth(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))


def _mock_collections(mock_db):
    # New collections written by the endpoint (keep conftest's users.find_one intact).
    for name in ("plan_reactions", "timeline", "audit_log"):
        coll = MagicMock()
        coll.insert_one = AsyncMock()
        setattr(mock_db, name, coll)
    mock_db.users.update_one = AsyncMock()


def test_requires_auth(client):
    assert client.post("/api/plans/diet/report-reaction",
                       json={"item": "x", "reaction": "y"}).status_code == 401


def test_unknown_plan_type_rejected(client, mock_db):
    _mock_collections(mock_db)
    _auth(client)
    res = client.post("/api/plans/bogus/report-reaction", json={"item": "x", "reaction": "y"})
    assert res.status_code == 400


def test_missing_fields_rejected(client, mock_db):
    _mock_collections(mock_db)
    _auth(client)
    res = client.post("/api/plans/diet/report-reaction", json={"item": "x"})
    assert res.status_code == 422


def test_records_reaction_and_writes_timeline(client, mock_db):
    _mock_collections(mock_db)
    _auth(client)
    res = client.post("/api/plans/remedies/report-reaction",
                      json={"item": "Triphala", "reaction": "cramps", "severity": "mild"})
    assert res.status_code == 201
    assert res.json()["status"] == "recorded"
    mock_db.plan_reactions.insert_one.assert_awaited()
    mock_db.timeline.insert_one.assert_awaited()
    # mild reaction → no forced re-assessment
    mock_db.users.update_one.assert_not_awaited()


def test_severe_reaction_flags_reassessment(client, mock_db):
    _mock_collections(mock_db)
    _auth(client)
    res = client.post("/api/plans/medicines/report-reaction",
                      json={"item": "X", "reaction": "rash", "severity": "severe"})
    assert res.status_code == 201
    assert res.json()["severity"] == "severe"
    mock_db.users.update_one.assert_awaited()
