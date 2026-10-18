"""
Ayura AI - Authentication Service
Handles JWT creation/validation and password hashing.
"""

from datetime import datetime, timedelta, timezone
import uuid
import jwt
import bcrypt
import hashlib
from config import settings


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    user_id: str,
    email: str,
    name: str = "",
    is_admin: bool = False,
    onboarding_complete: bool = False,
) -> str:
    """Create a short-lived JWT access token with embedded user claims.

    Embedding name, is_admin, and onboarding_complete avoids a DB round-trip
    on every authenticated request for simple auth checks.
    """
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "is_admin": is_admin,
        "onboarding_complete": onboarding_complete,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def create_verification_token(email: str) -> str:
    """Create a token for email verification."""
    payload = {
        "sub": email,
        "type": "verify",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_verification_token(token: str) -> str:
    """Verify email verification token and return the email address."""
    payload = decode_token(token)
    if payload.get("type") != "verify":
        raise ValueError("Not an email verification token")
    return payload["sub"]


def get_current_user_id(token: str) -> str:
    """Extract user ID from a valid access token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload["sub"]


def token_predates_password_change(claims: dict, user_dict: dict) -> bool:
    """True for a token issued before the account's password last changed.

    A password reset changed the hash and nothing else, so every session that
    existed before it kept working — including the one belonging to whoever the
    owner was resetting to lock out. Refresh tokens are revoked at the change
    (end_other_sessions); access tokens cannot be revoked one by one, so this
    refuses any issued before it. Compared at second resolution, which is what
    a JWT's iat carries.
    """
    changed = user_dict.get("password_changed_at")
    if not changed:
        return False
    if isinstance(changed, datetime) and changed.tzinfo is None:
        changed = changed.replace(tzinfo=timezone.utc)
    if not isinstance(changed, datetime):
        return False
    return int(claims.get("iat") or 0) < int(changed.timestamp())


async def end_other_sessions(db, user_id: str) -> datetime:
    """After a password reset or change: revoke every refresh token and stamp
    the change, so tokens issued before it stop working. Returns the stamp; a
    token issued from now on is not refused."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    await db.users.update_one({"_id": user_id}, {"$set": {"password_changed_at": now}})
    await db.refresh_tokens.update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": now, "revoked_reason": "password_changed"}},
    )
    return now


def get_token_claims(token: str) -> dict:
    """Decode an access token and return the full claims payload.

    Returns a dict with keys: sub, email, name, is_admin, onboarding_complete.
    Raises ValueError for invalid/expired tokens.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload


def create_reset_token(user_id: str, email: str, password_hash: str) -> str:
    """Create a short-lived password reset token (1 hour) tied to the current password hash."""
    pw_hash_digest = hashlib.sha256(password_hash.encode("utf-8")).hexdigest()
    payload = {
        "sub": user_id,
        "email": email,
        "pwh": pw_hash_digest,
        "type": "reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_reset_token(token: str) -> dict:
    """Verify a password reset token and return its payload."""
    payload = decode_token(token)
    if payload.get("type") != "reset":
        raise ValueError("Not a password reset token")
    return payload
