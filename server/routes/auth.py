"""
Ayura AI - Authentication Routes
Handles registration, login, Google OAuth, and token refresh.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import secrets
import uuid

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import settings
from database.mongodb import get_mongodb
from schemas.user_schema import UserDocument
from schemas.auth_schema import (
    RegisterRequest, LoginRequest, GoogleAuthRequest, GithubAuthRequest,
    TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
    ResendVerificationRequest, SendOtpRequest, VerifyOtpRequest,
)
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    create_reset_token, verify_reset_token,
    create_verification_token, verify_verification_token,
)
from core.logger import logger
from services.email_service import send_verification_email, send_password_reset_email
from services.sms_service import send_sms_otp

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_otp(phone_number: str, code: str) -> str:
    payload = f"{phone_number}:{code}:{settings.SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _cookie_kwargs(max_age: int) -> dict:
    return {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": max_age,
        "path": "/",
    }


async def _store_refresh_token(db: AsyncIOMotorDatabase, token: str, replaced_by: str | None = None) -> dict:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")

    await db.refresh_tokens.insert_one({
        "user_id": payload["sub"],
        "jti": payload["jti"],
        "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc),
        "replaced_by_jti": replaced_by,
        "revoked_at": None
    })
    return payload


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        settings.ACCESS_TOKEN_COOKIE,
        access_token,
        **_cookie_kwargs(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    )
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE,
        refresh_token,
        **_cookie_kwargs(settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path="/")


async def _issue_tokens(user: UserDocument, response: Response, db: AsyncIOMotorDatabase) -> TokenResponse:
    access_token = create_access_token(
        user.id,
        user.email,
        name=user.name or "",
        is_admin=user.is_admin,
        onboarding_complete=user.onboarding_complete,
    )
    refresh_token = create_refresh_token(user.id)
    await _store_refresh_token(db, refresh_token)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, background_tasks: BackgroundTasks, response: Response, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Register a new user with email/password."""
    existing_user = await db.users.find_one({"email": req.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    now = datetime.now(timezone.utc)
    user = UserDocument(
        _id=str(uuid.uuid4()),
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        auth_provider="local",
        consent_given=req.consent_given,
        consent_at=now if req.consent_given else None,
        created_at=now,
        updated_at=now
    )

    await db.users.insert_one(user.model_dump(by_alias=True))

    # --- Email Verification ---
    token = create_verification_token(user.email)
    background_tasks.add_task(send_verification_email, user.email, token)
    logger.info(f"Verification email scheduled for {user.email}")

    return await _issue_tokens(user, response, db)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Login with email/password."""
    user_dict = await db.users.find_one({"email": req.email})

    if not user_dict or not user_dict.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(req.password, user_dict["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = UserDocument(**user_dict)
    return await _issue_tokens(user, response, db)


@router.get("/google/url")
async def get_google_auth_url(response: Response):
    """Generate Google Auth URL with CSRF state."""
    from config import settings
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    state = secrets.token_urlsafe(32)
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/"
    )

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.RESOLVED_GOOGLE_REDIRECT_URI}&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )
    return {"url": auth_url}


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    req: GoogleAuthRequest,
    response: Response,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Authenticate with Google OAuth authorization code."""
    import httpx
    from config import settings

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured on this server.")

    if not oauth_state or not req.state or not hmac.compare_digest(oauth_state, req.state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state (CSRF failure)")

    # Clear the state cookie after use
    response.delete_cookie("oauth_state", path="/")

    redirect_uri = req.redirect_uri or settings.RESOLVED_GOOGLE_REDIRECT_URI

    # Exchange code for tokens with Google
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": req.code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_resp.json()

            if "error" in token_data:
                error_description = token_data.get("error_description")
                detail = f"Google auth failed: {token_data['error']}"
                if error_description:
                    detail = f"{detail} ({error_description})"
                raise HTTPException(status_code=400, detail=detail)

            # Get user info from Google
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            google_user = user_resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=500, detail="Failed to communicate with Google")

    if "id" not in google_user or "email" not in google_user:
        raise HTTPException(status_code=400, detail="Google auth failed: invalid user profile data.")

    # Find or create user
    user_dict = await db.users.find_one({
        "$or": [{"google_id": google_user["id"]}, {"email": google_user["email"]}]
    })

    now = datetime.now(timezone.utc)

    if not user_dict:
        user = UserDocument(
            _id=str(uuid.uuid4()),
            email=google_user["email"],
            name=google_user.get("name", "User"),
            avatar_url=google_user.get("picture"),
            auth_provider="google",
            google_id=google_user["id"],
            created_at=now,
            updated_at=now
        )
        await db.users.insert_one(user.model_dump(by_alias=True))
    else:
        user = UserDocument(**user_dict)
        if not user.google_id:
            # Link Google account to existing email user
            user.google_id = google_user["id"]
            user.auth_provider = "google"
            if google_user.get("picture"):
                user.avatar_url = google_user["picture"]
            user.updated_at = now
            await db.users.update_one(
                {"_id": user.id},
                {"$set": user.model_dump(by_alias=True)}
            )

    return await _issue_tokens(user, response, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    req: RefreshRequest | None = Body(default=None),
    refresh_cookie: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Refresh an expired access token."""
    incoming_refresh = (req.refresh_token if req else None) or refresh_cookie
    if not incoming_refresh:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = decode_token(incoming_refresh)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user_id = payload["sub"]
    stored_token = await db.refresh_tokens.find_one({"jti": payload.get("jti")})

    expires_at = _as_aware_utc(stored_token.get("expires_at")) if stored_token else None
    if not stored_token or stored_token.get("revoked_at") or not expires_at or expires_at <= _utc_now():
        raise HTTPException(status_code=401, detail="Refresh token is no longer valid")

    user_dict = await db.users.find_one({"_id": user_id})
    if not user_dict:
        raise HTTPException(status_code=401, detail="User not found")

    user = UserDocument(**user_dict)

    new_access = create_access_token(
        user.id,
        user.email,
        name=user.name or "",
        is_admin=user.is_admin,
        onboarding_complete=user.onboarding_complete,
    )
    new_refresh = create_refresh_token(user.id)
    new_payload = await _store_refresh_token(db, new_refresh)

    await db.refresh_tokens.update_one(
        {"_id": stored_token["_id"]},
        {"$set": {
            "revoked_at": datetime.now(timezone.utc),
            "replaced_by_jti": new_payload["jti"]
        }}
    )

    _set_auth_cookies(response, new_access, new_refresh)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Revoke the current refresh token and clear auth cookies."""
    if refresh_cookie:
        try:
            payload = decode_token(refresh_cookie)
            stored_token = await db.refresh_tokens.find_one({"jti": payload.get("jti")})
            if stored_token and not stored_token.get("revoked_at"):
                await db.refresh_tokens.update_one(
                    {"_id": stored_token["_id"]},
                    {"$set": {"revoked_at": datetime.now(timezone.utc)}}
                )
        except ValueError:
            pass
    _clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Generate a password reset token and send email."""
    user_dict = await db.users.find_one({"email": req.email})

    # Always return success to prevent email enumeration
    if not user_dict:
        return {"message": "If an account with that email exists, a reset link has been sent."}

    user = UserDocument(**user_dict)
    if user.auth_provider != "local":
        return {"message": "If an account with that email exists, a reset link has been sent."}

    token = create_reset_token(user.id, user.email, user.password_hash or "")

    # Send email in background
    background_tasks.add_task(send_password_reset_email, user.email, token)
    logger.info(f"Password reset email scheduled for {user.email}")

    return {
        "message": "If an account with that email exists, a reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Reset password using token."""
    try:
        payload = verify_reset_token(req.token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_dict = await db.users.find_one({
        "_id": payload["sub"],
        "email": payload["email"],
    })

    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")

    current_hash_digest = hashlib.sha256((user_dict.get("password_hash") or "").encode("utf-8")).hexdigest()
    if payload.get("pwh") != current_hash_digest:
        raise HTTPException(status_code=400, detail="Password reset token has already been used or is invalid")

    await db.users.update_one(
        {"_id": payload["sub"]},
        {"$set": {
            "password_hash": hash_password(req.new_password),
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Verify user's email address."""
    try:
        email = verify_verification_token(req.token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_dict = await db.users.find_one({"email": email})

    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"_id": user_dict["_id"]},
        {"$set": {
            "is_verified": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Email verified successfully. You can now log in."}

@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest, background_tasks: BackgroundTasks, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Resend the email verification link."""
    user_dict = await db.users.find_one({"email": req.email})

    if not user_dict:
        return {"message": "If an account with that email exists, a verification link has been sent."}

    user = UserDocument(**user_dict)
    if user.is_verified:
        return {"message": "This email is already verified."}

    token = create_verification_token(user.email)
    background_tasks.add_task(send_verification_email, user.email, token)
    logger.info(f"Verification email re-scheduled for {user.email}")

    return {"message": "If an account with that email exists, a verification link has been sent."}


@router.get("/github/url")
async def get_github_auth_url(response: Response):
    """Generate GitHub Auth URL with CSRF state cookie (mirrors /google/url)."""
    if not getattr(settings, "GITHUB_CLIENT_ID", None):
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    state = secrets.token_urlsafe(32)
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/",
    )
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"scope=user:email&"
        f"state={state}"
    )
    return {"url": auth_url}


@router.post("/github", response_model=TokenResponse)
async def github_auth(
    req: GithubAuthRequest,
    response: Response,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Authenticate with GitHub OAuth authorization code."""
    import httpx
    from config import settings

    if not getattr(settings, "GITHUB_CLIENT_ID", None) or not getattr(settings, "GITHUB_CLIENT_SECRET", None):
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured on this server.")

    if not oauth_state or not req.state or not hmac.compare_digest(oauth_state, req.state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state (CSRF failure)")

    response.delete_cookie("oauth_state", path="/")

    # 1. Exchange code for access token
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": req.code,
                },
            )
            token_data = token_resp.json()

            if "error" in token_data:
                raise HTTPException(status_code=400, detail=f"GitHub auth failed: {token_data.get('error_description', token_data['error'])}")

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub")

            # 2. Get user profile
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            github_user = user_resp.json()

            if "id" not in github_user:
                raise HTTPException(status_code=400, detail="Failed to retrieve GitHub profile")

            # 3. Get user emails (GitHub doesn't always return email in profile)
            email = github_user.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                emails = emails_resp.json()
                primary_email = next((e["email"] for e in emails if e.get("primary")), None)
                if primary_email:
                    email = primary_email
                elif len(emails) > 0:
                    email = emails[0]["email"]

    except httpx.HTTPError:
        raise HTTPException(status_code=500, detail="Failed to communicate with GitHub")

    if not email:
        raise HTTPException(status_code=400, detail="GitHub auth failed: no email found associated with this GitHub account.")

    # 4. Find or create user
    github_id_str = str(github_user["id"])
    user_dict = await db.users.find_one({
        "$or": [{"github_id": github_id_str}, {"email": email}]
    })

    now = datetime.now(timezone.utc)

    if not user_dict:
        user = UserDocument(
            _id=str(uuid.uuid4()),
            email=email,
            name=github_user.get("name") or github_user.get("login") or "User",
            avatar_url=github_user.get("avatar_url"),
            auth_provider="github",
            github_id=github_id_str,
            created_at=now,
            updated_at=now
        )
        await db.users.insert_one(user.model_dump(by_alias=True))
    else:
        user = UserDocument(**user_dict)
        if not user.github_id:
            # Link GitHub account to existing email user
            user.github_id = github_id_str
            user.auth_provider = "github"
            if github_user.get("avatar_url") and not user.avatar_url:
                user.avatar_url = github_user["avatar_url"]
            user.updated_at = now
            await db.users.update_one(
                {"_id": user.id},
                {"$set": user.model_dump(by_alias=True)}
            )

    return await _issue_tokens(user, response, db)


@router.post("/send-otp")
async def send_otp(req: SendOtpRequest, background_tasks: BackgroundTasks, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Generate and send an OTP code to a mobile number."""
    otp_code = f"{secrets.randbelow(900000) + 100000}"

    # Store as a real datetime so MongoDB TTL index can expire it automatically
    expires_at = _utc_now() + timedelta(seconds=300)

    await db.otps.update_one(
        {"phone_number": req.phone_number},
        {"$set": {
            "code_hash": _hash_otp(req.phone_number, otp_code),
            "expires_at": expires_at,
            "created_at": _utc_now()
        }},
        upsert=True
    )

    # Send via background task
    sent = await send_sms_otp(req.phone_number, otp_code)
    if not sent:
        await db.otps.delete_one({"phone_number": req.phone_number})
        raise HTTPException(status_code=503, detail="SMS delivery is not configured.")

    return {"message": "OTP sent successfully."}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(req: VerifyOtpRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Verify an OTP and log the user in (or create an account)."""
    otp_doc = await db.otps.find_one({"phone_number": req.phone_number})

    if not otp_doc:
        raise HTTPException(status_code=400, detail="No OTP requested for this number")

    expected_hash = otp_doc.get("code_hash")
    provided_hash = _hash_otp(req.phone_number, req.code)
    legacy_code = otp_doc.get("code")
    if expected_hash:
        is_valid_code = hmac.compare_digest(expected_hash, provided_hash)
    else:
        is_valid_code = hmac.compare_digest(str(legacy_code or ""), req.code)

    if not is_valid_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    otp_expires = otp_doc["expires_at"]
    if isinstance(otp_expires, (int, float)):
        otp_expires = datetime.fromtimestamp(otp_expires, timezone.utc)
    if datetime.now(timezone.utc) > otp_expires:
        raise HTTPException(status_code=400, detail="OTP code has expired")

    # Valid OTP -> Clear it so it can't be reused
    await db.otps.delete_one({"_id": otp_doc["_id"]})

    # Find or create user
    user_dict = await db.users.find_one({"phone_number": req.phone_number})
    now = datetime.now(timezone.utc)

    if not user_dict:
        # Sentinel domain that no real user can register — avoids collision with real email accounts
        placeholder_email = f"phone_{req.phone_number.strip('+')}@phone.internal.ayura"
        user = UserDocument(
            _id=str(uuid.uuid4()),
            email=placeholder_email,
            name="New User",
            auth_provider="phone",
            phone_number=req.phone_number,
            phone_only=True,
            is_verified=True,
            created_at=now,
            updated_at=now
        )
        await db.users.insert_one(user.model_dump(by_alias=True))
    else:
        user = UserDocument(**user_dict)

    return await _issue_tokens(user, response, db)
