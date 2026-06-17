"""
Ayura AI - Pydantic Schemas for Authentication
"""

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(ch.isalpha() for ch in password):
        raise ValueError("Password must include at least one letter")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must include at least one number")
    return password


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
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
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

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
    phone_number: str = Field(..., min_length=7, max_length=20)


class VerifyOtpRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20)
    code: str = Field(..., min_length=6, max_length=6)

