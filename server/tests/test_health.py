"""
Tests for /api/health and /api/ready endpoints.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health_check_returns_200_when_mongodb_available():
    # Patch at the source module since both functions are imported inside the route handler
    with patch("database.mongodb.is_mongodb_available", return_value=True), \
         patch("database.chromadb_client.is_chromadb_available", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_returns_503_when_mongodb_unavailable():
    with patch("database.mongodb.is_mongodb_available", return_value=False), \
         patch("database.chromadb_client.is_chromadb_available", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_ready_returns_503_when_kb_cache_not_loaded():
    with patch("database.mongodb.is_mongodb_available", return_value=True), \
         patch("core.kb_cache.kb_cache") as mock_cache:
        mock_cache.loaded = False
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/ready")
    assert resp.status_code == 503
    assert resp.json()["ready"] is False
    assert resp.json()["kb_cache"] == "loading"


@pytest.mark.asyncio
async def test_ready_returns_200_when_fully_ready():
    with patch("database.mongodb.is_mongodb_available", return_value=True), \
         patch("core.kb_cache.kb_cache") as mock_cache:
        mock_cache.loaded = True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True
