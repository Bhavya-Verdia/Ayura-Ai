"""
Tests for community post reporting + auto-hide moderation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token


@pytest.fixture
def client():
    yield TestClient(app)


def _auth(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))


def _post(reported_by=None, user_id="other-user"):
    return {
        "_id": "p1", "user_id": user_id, "author_name": "Someone",
        "content": "hi", "likes": [], "reported_by": reported_by or [],
        "created_at": datetime.now(timezone.utc),
    }


def test_cannot_report_own_post(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value=_post(user_id="test-uuid-1234"))
    _auth(client)
    res = client.post("/api/community/p1/report", json={"reason": "spam"})
    assert res.status_code == 400


def test_report_adds_flag_without_hiding(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value=_post(reported_by=[]))
    mock_db.community_posts.update_one = AsyncMock()
    _auth(client)
    res = client.post("/api/community/p1/report", json={"reason": "off-topic"})
    assert res.status_code == 200
    body = res.json()
    assert body["reported"] is True and body["hidden"] is False
    update = mock_db.community_posts.update_one.call_args.args[1]
    assert "$set" not in update  # below threshold → not hidden


def test_third_report_hides_post(client, mock_db):
    mock_db.community_posts = MagicMock()
    # already 2 distinct reporters → this is the 3rd → auto-hide
    mock_db.community_posts.find_one = AsyncMock(return_value=_post(reported_by=["u1", "u2"]))
    mock_db.community_posts.update_one = AsyncMock()
    _auth(client)
    res = client.post("/api/community/p1/report", json={})
    assert res.status_code == 200
    assert res.json()["hidden"] is True
    assert mock_db.community_posts.update_one.call_args.args[1]["$set"] == {"hidden": True}


def test_duplicate_report_is_noop(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value=_post(reported_by=["test-uuid-1234"]))
    mock_db.community_posts.update_one = AsyncMock()
    _auth(client)
    res = client.post("/api/community/p1/report", json={})
    assert res.status_code == 200
    assert res.json().get("already_reported") is True
    mock_db.community_posts.update_one.assert_not_called()
