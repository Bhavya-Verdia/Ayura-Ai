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


# ── The deployed commit ───────────────────────────────────────────────────────
#
# `/api/health` reported a hardcoded "1.0.0", so a successful deploy run and a
# container still running last week's image were indistinguishable over HTTP. A
# frontend deploy could always be verified — grep the served bundle for a string
# only the new build contains — and a backend one could not be verified at all
# without shell access to the droplet.

@pytest.mark.asyncio
async def test_health_reports_the_commit_it_was_built_from():
    with patch("database.mongodb.is_mongodb_available", return_value=True), \
         patch("database.chromadb_client.is_chromadb_available", return_value=True), \
         patch.dict("os.environ", {"GIT_SHA": "abc123def456"}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/health")
    assert resp.json()["git_sha"] == "abc123def456"


@pytest.mark.asyncio
async def test_an_unstamped_build_says_so_rather_than_inventing_a_sha():
    """A local build was not built from a known commit, and claiming one would make
    the check that depends on this field lie in the direction of passing."""
    import os as _os
    env = {k: v for k, v in _os.environ.items() if k != "GIT_SHA"}
    with patch("database.mongodb.is_mongodb_available", return_value=True), \
         patch("database.chromadb_client.is_chromadb_available", return_value=True), \
         patch.dict("os.environ", env, clear=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/health")
    assert resp.json()["git_sha"] == "unknown"


def test_the_build_arg_reaches_every_image_built_from_the_server_context():
    """The api and the worker run the same code. A worker left on an older image is
    the harder failure to see, because nothing serves an HTTP response from it."""
    import os
    import yaml
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    compose = yaml.safe_load(open(os.path.join(root, "docker-compose.yml")))
    for service in ("api", "worker"):
        build = compose["services"][service]["build"]
        assert build["context"] == "./server"
        assert any("GIT_SHA" in str(a) for a in build.get("args", [])), \
            f"{service} builds from ./server but is not stamped with GIT_SHA"
