"""Admin authentication helpers."""

from fastapi import Header, HTTPException
import hmac

from config import settings


async def require_admin_token(x_admin_token: str | None = Header(default=None)):
    if not settings.ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="Admin endpoints are not configured")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True
