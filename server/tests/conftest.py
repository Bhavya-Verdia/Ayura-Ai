"""
Ayura AI - Test Configuration and Fixtures (MongoDB Mocked)
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.mongodb import get_mongodb
from main import app
from datetime import datetime, timezone
from services.auth_service import hash_password

@pytest.fixture(autouse=True)
def mock_db():
    db = AsyncMock()
    # Mock user document returned by find_one to fix test_auth.py
    mock_user = {
        "_id": "test-uuid-1234",
        "name": "Test User",
        "email": "test@ayura.com",
        "password_hash": hash_password("TestPass123!"),
        "auth_provider": "local",
        "is_active": True,
        "is_admin": False,
        "is_verified": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    db.users = AsyncMock()
    db.users.find_one = AsyncMock(return_value=mock_user)
    db.users.insert_one = AsyncMock(return_value=AsyncMock(inserted_id="test-uuid-1234"))

    db.plan_history = AsyncMock()
    db.chat_sessions = AsyncMock()
    db.chat_messages = AsyncMock()

    app.dependency_overrides[get_mongodb] = lambda: db
    yield db
    app.dependency_overrides.clear()

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
