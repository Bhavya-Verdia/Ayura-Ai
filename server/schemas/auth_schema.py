"""
Ayura AI - Pydantic Schemas for Authentication
"""

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    # bcrypt silently truncates input beyond 72 bytes, so characters past that
    # point would not affect the hash. Reject in bytes (not chars) to also cover
    # multi-byte passwords that fit in 72 chars but exceed 72 bytes.
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes long")
    if not any(ch.isalpha() for ch in password):
        raise ValueError("Password must include at least one letter")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must include at least one number")
    return password


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(..., min_length=8, max_length=72)
    consent_given: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)
    password: str


class GoogleAuthRequest(BaseModel):
    code: str  # Authorization code from Google OAuth
    redirect_uri: str | None = Field(default=None, max_length=500)
    state: str | None = None  # CSRF token state


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str


class RefreshRequest(BaseModel):
    # Optional: the refresh token is normally read from the HTTP-only cookie.
    # Requiring it here made the frontend's cookie-based `POST /auth/refresh {}`
    # fail validation with 422 instead of falling through to the cookie.
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)


class GithubAuthRequest(BaseModel):
    code: str  # Authorization code from GitHub OAuth
    redirect_uri: str | None = Field(default=None, max_length=500)
    state: str | None = None  # CSRF token state


class SendOtpRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20, pattern=r"^\+?[1-9]\d{6,14}$")


class VerifyOtpRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20, pattern=r"^\+?[1-9]\d{6,14}$")
    code: str = Field(..., min_length=6, max_length=6)

