"""
Ayura AI - Application Configuration
Loads environment variables and provides typed settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, field_validator, model_validator
from typing import Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR / ".env"),
            str(ROOT_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Ayura AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    TRUSTED_HOSTS: Optional[str] = None
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20
    REDIS_URL: Optional[str] = None
    TRUST_FORWARDED_FOR: bool = False
    ADMIN_TOKEN: Optional[str] = None
    CACHE_ENABLED: bool = True
    PLAN_TIMEOUT_SECONDS: int = 120

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Allow common environment tokens like 'release' / 'production'."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return value

    def validate_production_secrets(self) -> None:
        """Raise RuntimeError if insecure defaults are used in production."""
        if self.APP_ENV == "production":
            insecure = "change-me-in-production"
            if self.SECRET_KEY == insecure:
                raise RuntimeError(
                    "SECRET_KEY must be changed from the default value in production. "
                    "Set a long random string in your .env file."
                )
            if self.JWT_SECRET_KEY == insecure:
                raise RuntimeError(
                    "JWT_SECRET_KEY must be changed from the default value in production. "
                    "Set a long random string in your .env file."
                )
            if not self.ADMIN_TOKEN or self.ADMIN_TOKEN == "change-this-admin-token":
                raise RuntimeError(
                    "ADMIN_TOKEN must be set to a secure random value in production."
                )
            if self.SMS_OTP_MOCK:
                raise RuntimeError(
                    "SMS_OTP_MOCK must be false in production. Configure a real SMS provider "
                    "or disable phone OTP login."
                )

    # --- MongoDB ---
    MONGO_URL: Optional[str] = None
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "ayura"
    MONGO_USER: Optional[str] = None
    MONGO_PASSWORD: Optional[str] = None

    @model_validator(mode="after")
    def resolve_mongo_url(self):
        if not self.MONGO_URL:
            if self.MONGO_USER and self.MONGO_PASSWORD:
                self.MONGO_URL = (
                    f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
                    f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}?authSource=admin"
                )
            else:
                self.MONGO_URL = f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"
        return self

    # --- ChromaDB ---
    CHROMA_PERSIST_DIRECTORY: str = "./server/data/chromadb"

    # --- Azure OpenAI (Primary LLM) ---
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # --- Google Gemini (Fallback LLM) ---
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # --- GitHub OAuth ---
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    @property
    def RESOLVED_GOOGLE_REDIRECT_URI(self) -> str:
        """Return the configured redirect URI, or derive from FRONTEND_URL."""
        if self.GOOGLE_REDIRECT_URI:
            return self.GOOGLE_REDIRECT_URI
        return f"{self.FRONTEND_URL}/auth/google/callback"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_COOKIE: str = "ayura_access"
    REFRESH_TOKEN_COOKIE: str = "ayura_refresh"
    # Default False so local HTTP dev works; auto-forced True in production via APP_ENV validator
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    @field_validator("COOKIE_SECURE", mode="before")
    @classmethod
    def auto_secure_cookie(cls, value, info):
        """Force COOKIE_SECURE=True when APP_ENV=production, regardless of .env setting."""
        import os
        app_env = os.environ.get("APP_ENV", "development").strip().lower()
        if app_env == "production":
            return True
        return value

    @property
    def RESOLVED_GOOGLE_REDIRECT_URI(self) -> str:
        """Return the configured redirect URI, or derive from FRONTEND_URL."""
        if self.GOOGLE_REDIRECT_URI:
            return self.GOOGLE_REDIRECT_URI
        return f"{self.FRONTEND_URL}/auth/google/callback"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_COOKIE: str = "ayura_access"
    REFRESH_TOKEN_COOKIE: str = "ayura_refresh"
    # Default False so local HTTP dev works; auto-forced True in production via APP_ENV validator
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    @field_validator("COOKIE_SECURE", mode="before")
    @classmethod
    def auto_secure_cookie(cls, value, info):
        """Force COOKIE_SECURE=True when APP_ENV=production, regardless of .env setting."""
        import os
        app_env = os.environ.get("APP_ENV", "development").strip().lower()
        if app_env == "production":
            return True
        return value

    # --- Weather API (OpenWeatherMap - optional, free tier) ---
    WEATHER_API_KEY: Optional[str] = None
    DEFAULT_LAT: float = 28.6139  # Default: New Delhi
    DEFAULT_LON: float = 77.2090

    # --- Sentry Error Tracking ---
    SENTRY_DSN: Optional[str] = None

    # --- Uploads (S3 / R2 / Spaces) ---
    UPLOADS_DIR: str = str(BASE_DIR / "uploads") # Fallback for local dev
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_REGION_NAME: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None

    # --- SMTP / Email Services ---
    SMTP_SERVER: str = Field(
        default="smtp.gmail.com",
        validation_alias=AliasChoices("SMTP_SERVER", "SMTP_HOST"),
    )
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_USER", "SMTP_USERNAME"),
    )
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = Field(
        default="noreply@ayura.com",
        validation_alias=AliasChoices("FROM_EMAIL", "EMAIL_FROM"),
    )

    # --- SMS / OTP ---
    SMS_OTP_MOCK: bool = True
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # --- URLs ---
    FRONTEND_URL: str = "http://localhost:5173"
    FRONTEND_URLS: Optional[str] = None
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Allowed frontend origins for local/dev and configurable deployments."""
        origins = {
            self.FRONTEND_URL,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
        if self.FRONTEND_URLS:
            origins.update(
                origin.strip() for origin in self.FRONTEND_URLS.split(",") if origin.strip()
            )
        return sorted(origins)

    @property
    def TRUSTED_HOST_LIST(self) -> list[str]:
        if not self.TRUSTED_HOSTS:
            return ["*"]
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

settings = Settings()
