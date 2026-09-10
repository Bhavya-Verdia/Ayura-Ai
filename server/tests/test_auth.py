import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app
from database.mongodb import get_mongodb
from services.auth_service import create_access_token, hash_password

# Setup test client and dependency overrides
@pytest.fixture
def client():
    yield TestClient(app)

def test_register_user(client):
    with patch("database.mongodb.get_mongodb"):
        # Mock that the user doesn't exist yet for registration
        mock_db = client.app.dependency_overrides[get_mongodb]()
        mock_db.users.find_one = AsyncMock(return_value=None)

        response = client.post(
            "/api/auth/register",
            json={
                "name": "New User",
                "email": "new@ayura.com",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 201
        data = response.json()
        # Registration no longer issues a session — it requires email verification.
        assert data["requires_verification"] is True
        assert "access_token" not in data

        # Verify db insert was called
        mock_db.users.insert_one.assert_called_once()


def test_register_existing_email_is_generic(client):
    """Registering an existing email returns the same response as a new one
    (no account enumeration) and does not create a duplicate user."""
    mock_db = client.app.dependency_overrides[get_mongodb]()
    # find_one returns an existing user (the conftest mock user)
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Someone",
            "email": "test@ayura.com",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["requires_verification"] is True
    assert "access_token" not in data
    mock_db.users.insert_one.assert_not_called()


def test_login_unverified_local_user_blocked(client):
    """A local account that hasn't verified its email cannot log in."""
    mock_db = client.app.dependency_overrides[get_mongodb]()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "unverified-1",
        "name": "Unverified",
        "email": "unverified@ayura.com",
        "password_hash": hash_password("TestPass123!"),
        "auth_provider": "local",
        "is_verified": False,
        "created_at": now,
        "updated_at": now,
    })
    response = client.post(
        "/api/auth/login",
        json={"email": "unverified@ayura.com", "password": "TestPass123!"},
    )
    assert response.status_code == 403

def test_login_user_success(client):
    # The fixture already sets up the db to return our test user
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@ayura.com",
            "password": "TestPass123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_user_invalid_password(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@ayura.com",
            "password": "WrongPassword!"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_get_current_user_profile(client):
    # First generate a valid token for our mock user
    token = create_access_token("test-uuid-1234", "test@ayura.com")

    response = client.get(
        "/api/profile/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@ayura.com"


# ── Account pre-hijacking via OAuth linking ────────────────────────────────
#
# register() writes a password_hash before anyone proves they own the address.
# Linking flips auth_provider, and the login gate used to read
# `auth_provider == "local" and not is_verified` — so linking switched the gate
# off and the stranger's password opened the account.

from datetime import datetime, timezone  # noqa: E402
from routes.auth import _adopt_oauth_identity, _pick_verified_github_email  # noqa: E402
from schemas.user_schema import UserDocument  # noqa: E402

NOW = datetime.now(timezone.utc)


def _user(**over):
    base = dict(
        _id="victim-uuid", email="victim@gmail.com", name="Victim",
        password_hash=hash_password("AttackerPass123!"),
        auth_provider="local", is_verified=False,
        created_at=NOW, updated_at=NOW,
    )
    base.update(over)
    return UserDocument(**base)


def test_linking_drops_a_password_nobody_verified():
    user = _user()
    fields = _adopt_oauth_identity(user, "google_id", "g-123", "google")
    assert fields["password_hash"] is None and user.password_hash is None
    assert fields["is_verified"] is True
    assert fields["google_id"] == "g-123"
    # Never the whole document — that used to carry `_id` into every $set.
    assert "_id" not in fields and "email" not in fields


def test_linking_keeps_a_password_the_owner_did_verify():
    user = _user(is_verified=True)
    fields = _adopt_oauth_identity(user, "google_id", "g-123", "google")
    assert "password_hash" not in fields and user.password_hash is not None


def test_login_gate_survives_the_provider_flip(client):
    """The exact post-link row: provider flipped, address still unverified."""
    mock_db = client.app.dependency_overrides[get_mongodb]()
    doc = _user(auth_provider="google", google_id="g-123").model_dump(by_alias=True)
    doc["password_hash"] = hash_password("AttackerPass123!")
    mock_db.users.find_one = AsyncMock(return_value=doc)

    res = client.post("/api/auth/login",
                      json={"email": "victim@gmail.com", "password": "AttackerPass123!"})
    assert res.status_code == 403
    assert "verify" in res.json()["detail"].lower()


def test_github_email_must_be_one_github_confirmed():
    emails = [
        {"email": "typed-in@victim.com", "primary": True, "verified": False},
        {"email": "real@example.com", "primary": False, "verified": True},
    ]
    assert _pick_verified_github_email(emails) == "real@example.com"
    assert _pick_verified_github_email(
        [{"email": "typed-in@victim.com", "primary": True, "verified": False}]
    ) is None
    assert _pick_verified_github_email([]) is None
