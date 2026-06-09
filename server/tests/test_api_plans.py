import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_generate_plan_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/plans/generate", json={"plan_types": ["diet"]})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_history_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/plans/history")
    assert response.status_code == 401
