"""
Tests for community comments + notification delete/clear-all.
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


# ── Community comments ───────────────────────────────────────────────────────────

def test_add_comment_increments_count(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value={"_id": "p1", "user_id": "u9"})
    mock_db.community_posts.update_one = AsyncMock()
    mock_db.community_comments = MagicMock()
    mock_db.community_comments.insert_one = AsyncMock()
    _auth(client)
    res = client.post("/api/community/p1/comments", json={"content": "Great tip, thanks!"})
    assert res.status_code == 201
    body = res.json()
    assert body["content"] == "Great tip, thanks!" and body["is_mine"] is True
    mock_db.community_comments.insert_one.assert_awaited()
    inc = mock_db.community_posts.update_one.call_args.args[1]
    assert inc == {"$inc": {"comment_count": 1}}


def test_add_comment_on_missing_post_404(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value=None)
    _auth(client)
    res = client.post("/api/community/nope/comments", json={"content": "hi"})
    assert res.status_code == 404


def test_comment_moderation_blocks_links(client, mock_db):
    mock_db.community_posts = MagicMock()
    mock_db.community_posts.find_one = AsyncMock(return_value={"_id": "p1", "user_id": "u9"})
    _auth(client)
    res = client.post("/api/community/p1/comments", json={"content": "visit my site http://spam.com"})
    assert res.status_code == 422


def test_delete_others_comment_forbidden(client, mock_db):
    mock_db.community_comments = MagicMock()
    mock_db.community_comments.find_one = AsyncMock(return_value={"_id": "c1", "post_id": "p1", "user_id": "someone-else"})
    _auth(client)
    res = client.delete("/api/community/comments/c1")
    assert res.status_code == 403


# ── Notification delete / clear ──────────────────────────────────────────────────

def test_delete_notification(client, mock_db):
    mock_db.notifications = MagicMock()
    mock_db.notifications.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    _auth(client)
    res = client.delete("/api/notifications/n1")
    assert res.status_code == 204


def test_delete_missing_notification_404(client, mock_db):
    mock_db.notifications = MagicMock()
    mock_db.notifications.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    _auth(client)
    res = client.delete("/api/notifications/nope")
    assert res.status_code == 404


def test_clear_all_notifications(client, mock_db):
    mock_db.notifications = MagicMock()
    mock_db.notifications.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
    _auth(client)
    res = client.delete("/api/notifications")
    assert res.status_code == 200
    assert res.json()["deleted"] == 5
