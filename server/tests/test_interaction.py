"""
Tests for the standalone drug-herb interaction checker (POST /plans/interaction-check).

Covers the new optional `medications` override + empty-input guards, plus a known
interaction firing a warning (deterministic tier; LLM/RAG mocked).
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token


@pytest.fixture
def client():
    yield TestClient(app)


def _auth(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))


def test_requires_auth(client):
    assert client.post("/api/plans/interaction-check", json={"herbs": ["tulsi"]}).status_code == 401


def test_no_herbs_is_safe(client, mock_db):
    _auth(client)
    res = client.post("/api/plans/interaction-check", json={"herbs": []})
    assert res.status_code == 200
    assert res.json()["status"] == "safe"


def test_no_medications_is_safe(client, mock_db):
    _auth(client)
    res = client.post("/api/plans/interaction-check",
                      json={"herbs": ["ashwagandha"], "medications": []})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "safe"
    assert "medication" in body["detailed_explanation"].lower()


def test_benign_combo_is_safe(client, mock_db):
    _auth(client)
    res = client.post("/api/plans/interaction-check",
                      json={"herbs": ["tulsi"], "medications": ["paracetamol"]})
    assert res.status_code == 200
    assert res.json()["status"] == "safe"


def test_known_interaction_flags_warning(client, mock_db):
    _auth(client)
    with patch("ai.llm_client.llm_client") as mock_llm, \
         patch("ai.rag_pipeline.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value="Potential interaction — consult your doctor.")
        mock_rag.query = AsyncMock(return_value=[])
        res = client.post("/api/plans/interaction-check",
                          json={"herbs": ["fenugreek"], "medications": ["metformin"]})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "warning"
    assert len(body["warnings"]) >= 1
    assert any("fenugreek" in (w.get("herb", "").lower()) for w in body["warnings"])
