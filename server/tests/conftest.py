"""
Ayura AI - Test Configuration and Fixtures (MongoDB Mocked)
"""

import asyncio
import pytest
import sys
import os
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.users = AsyncMock()
    db.plan_history = AsyncMock()
    db.chat_sessions = AsyncMock()
    db.chat_messages = AsyncMock()
    return db

@pytest.fixture
def sample_user_data():
    return {
        "name": "Test User",
        "email": "test@ayura.com",
        "password": "TestPass123!",
    }

@pytest.fixture
def sample_profile_data():
    return {
        "gender": "male",
        "age": 30,
        "height_cm": 175.0,
        "weight_kg": 75.0,
        "fitness_level": "intermediate",
        "activity_level": "moderate",
        "goal": "general_wellness",
        "medical_history": ["none"],
        "current_symptoms": ["fatigue"],
        "current_medications": [],
    }
