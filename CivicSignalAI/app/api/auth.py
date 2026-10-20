from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
import urllib.request
from urllib.parse import urlencode, urlsplit
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import database
from app.services.team_auth import normalize_email, hash_password, verify_password

router = APIRouter(prefix="/api/auth/team", tags=["team-auth"])
citizen_router = APIRouter(prefix="/api/auth/citizen", tags=["citizen-auth"])
logger = logging.getLogger(__name__)
SESSION_COOKIE = "civicsignal_team_session"
CITIZEN_SESSION_COOKIE = "civicsignal_citizen_session"
SESSION_SECONDS = 8 * 60 * 60
CITIZEN_SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_ATTEMPTS = 5
OAUTH_STATE_SECONDS = 10 * 60
OAUTH_COOKIE_PATH = "/api/auth/citizen/oauth"
OAUTH_PROVIDERS = {
    "google": {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "linkedin": {
        "authorization_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "userinfo_url": "https://api.linkedin.com/v2/userinfo",
        "scope": "openid profile email",
    },
}
DUMMY_PASSWORD_HASH = hash_password("not-a-valid-team-password")


class TeamLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        try:
            return normalize_email(value)
        except ValueError as exception:
            raise ValueError(str(exception)) from exception


class CitizenSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(min_length=6, max_length=40)
    password: str = Field(min_length=12, max_length=1024)
    confirm_password: str = Field(min_length=12, max_length=1024)
    accepted_terms: bool = Field(default=False)

    @field_validator("full_name", "phone")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        try:
            return normalize_email(value)
        except ValueError as exception:
            raise ValueError(str(exception)) from exception


class CitizenLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        try:
            return normalize_email(value)
        except ValueError as exception:
            raise ValueError(str(exception)) from exception


def session_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def current_team_user(request: Request) -> dict[str, str] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = database.get_team_session(session_fingerprint(token), int(time.time()))
    if session is None:
        return None
    return {"email": str(session["email"])}


def citizen_session_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def current_citizen_user(request: Request) -> dict[str, str] | None:
    token = request.cookies.get(CITIZEN_SESSION_COOKIE)
    if not token:
        return None
    session = database.get_citizen_session(citizen_session_fingerprint(token), int(time.time()))
    if session is None:
        return None
    return {"id": str(session["user_id"]), "email": str(session["email"])}


def require_citizen_user(request: Request) -> dict[str, str]:
    user = current_citizen_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Citizen authentication is required.")
    return user


def require_team_user(request: Request) -> dict[str, str]:
    user = current_team_user(request)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Team authentication is required.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    expected = str(request.base_url).rstrip("/")
    if origin and origin.rstrip("/") != expected:
        raise HTTPException(status_code=403, detail="Cross-origin request rejected.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-origin request rejected.")


def _remote_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _secure_cookie(request: Request) -> bool:
    configured = os.getenv("CIVICSIGNAL_COOKIE_SECURE")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return request.url.scheme == "https"


def _oauth_settings(provider: str) -> dict[str, str] | None:
    provider_settings = OAUTH_PROVIDERS.get(provider)
    if provider_settings is None:
        return None
    prefix = provider.upper()
    client_id = os.getenv(f"{prefix}_CLIENT_ID", "").strip()
    client_secret = os.getenv(f"{prefix}_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv(f"{prefix}_REDIRECT_URI", "").strip()
    state_secret = os.getenv("CIVICSIGNAL_OAUTH_STATE_SECRET", "")
    redirect = urlsplit(redirect_uri)
    local_http = redirect.scheme == "http" and redirect.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not client_id
        or not client_secret
        or len(state_secret.encode("utf-8")) < 32
        or not redirect.netloc
        or (redirect.scheme != "https" and not local_http)
        or redirect.path != f"{OAUTH_COOKIE_PATH}/{provider}/callback"
        or redirect.username is not None
        or redirect.password is not None
        or redirect.query
        or redirect.fragment
    ):
        return None
    return {
        **provider_settings,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "state_secret": state_secret,
    }


def _oauth_cookie_name(provider: str, cookie_type: str) -> str:
    return f"civicsignal_oauth_{provider}_{cookie_type}"


def _oauth_secure_cookie(request: Request) -> bool:
    return request.url.scheme == "https" or os.getenv("VERCEL") == "1"


def _sign_oauth_state(provider: str, state: str, secret: str) -> str:
    payload = json.dumps(
        {"provider": provider, "state": state, "expires_at": int(time.time()) + OAUTH_STATE_SECONDS},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def _valid_oauth_state(cookie: str, provider: str, state: str, secret: str) -> bool:
    try:
        encoded_payload, encoded_signature = cookie.split(".", 1)
        expected_signature = hmac.new(
            secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        padding = "=" * (-len(encoded_signature) % 4)
        received_signature = base64.urlsafe_b64decode((encoded_signature + padding).encode("ascii"))
        if not hmac.compare_digest(expected_signature, received_signature):
            return False
        payload_padding = "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode((encoded_payload + payload_padding).encode("ascii")))
        return (
            payload.get("provider") == provider
            and int(payload.get("expires_at", 0)) > int(time.time())
            and hmac.compare_digest(str(payload.get("state", "")), state)
        )
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return False


def _oauth_json_request(
    url: str,
    form: dict[str, str] | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if form is not None:
        body = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        content = response.read(65537)
    if len(content) > 65536:
        raise ValueError("OAuth provider response was too large.")
    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError("OAuth provider returned an invalid response.")
    return result


def _oauth_error_redirect(error: str) -> RedirectResponse:
    return RedirectResponse(url=f"/?oauth_error={error}", status_code=303)


def _clear_oauth_cookies(response: Response, provider: str, secure: bool) -> None:
    for cookie_type in ("state", "verifier"):
        response.delete_cookie(
            key=_oauth_cookie_name(provider, cookie_type),
            httponly=True,
            secure=secure,
            samesite="lax",
            path=OAUTH_COOKIE_PATH,
        )


@citizen_router.get("/oauth/{provider}", include_in_schema=False)
def citizen_oauth_start(provider: str, request: Request) -> Response:
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="OAuth provider not found.")
    settings = _oauth_settings(provider)
    if settings is None:
        return _oauth_error_redirect("not_configured")

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    challenge_text = challenge.decode("ascii").rstrip("=")
    query = urlencode({
        "client_id": settings["client_id"],
        "redirect_uri": settings["redirect_uri"],
        "response_type": "code",
        "scope": settings["scope"],
        "state": state,
        "code_challenge": challenge_text,
        "code_challenge_method": "S256",
    })
    response = RedirectResponse(f"{settings['authorization_url']}?{query}", status_code=302)
    secure = _oauth_secure_cookie(request)
    response.set_cookie(
        _oauth_cookie_name(provider, "state"),
        _sign_oauth_state(provider, state, settings["state_secret"]),
        max_age=OAUTH_STATE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )
    response.set_cookie(
        _oauth_cookie_name(provider, "verifier"),
        verifier,
        max_age=OAUTH_STATE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@citizen_router.get("/oauth/{provider}/callback", include_in_schema=False)
def citizen_oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="OAuth provider not found.")
    settings = _oauth_settings(provider)
    if settings is None:
        return _oauth_error_redirect("not_configured")

    secure = _oauth_secure_cookie(request)
    state_cookie = request.cookies.get(_oauth_cookie_name(provider, "state"), "")
    verifier = request.cookies.get(_oauth_cookie_name(provider, "verifier"), "")
    if not state or not verifier or not _valid_oauth_state(state_cookie, provider, state, settings["state_secret"]):
        return _oauth_error_redirect("invalid_state")

    if error:
        response = _oauth_error_redirect("cancelled")
        _clear_oauth_cookies(response, provider, secure)
        return response
    if not code:
        response = _oauth_error_redirect("provider_error")
        _clear_oauth_cookies(response, provider, secure)
        return response

    try:
        tokens = _oauth_json_request(
            settings["token_url"],
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings["redirect_uri"],
                "client_id": settings["client_id"],
                "client_secret": settings["client_secret"],
                "code_verifier": verifier,
            },
        )
        access_token = tokens.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("OAuth provider did not return an access token.")
        profile = _oauth_json_request(settings["userinfo_url"], access_token=access_token)
    except Exception:
        logger.exception("OAuth provider exchange failed for %s", provider)
        response = _oauth_error_redirect("provider_error")
        _clear_oauth_cookies(response, provider, secure)
        return response

    email = profile.get("email")
    if not isinstance(email, str) or profile.get("email_verified") is not True:
        response = _oauth_error_redirect("unverified_email")
        _clear_oauth_cookies(response, provider, secure)
        return response
    try:
        normalized_email = normalize_email(email)
    except ValueError:
        response = _oauth_error_redirect("unverified_email")
        _clear_oauth_cookies(response, provider, secure)
        return response

    try:
        user = database.get_citizen_user_by_email(normalized_email)
    except sqlite3.Error:
        logger.exception("Could not find citizen account for %s OAuth sign-in", provider)
        response = _oauth_error_redirect("sign_in_failed")
        _clear_oauth_cookies(response, provider, secure)
        return response
    if user is None or not bool(user["is_active"]):
        response = _oauth_error_redirect("account_required")
        _clear_oauth_cookies(response, provider, secure)
        return response

    session_token = secrets.token_urlsafe(32)
    email_value = str(user["email"])
    database.create_citizen_session(
        citizen_session_fingerprint(session_token),
        str(user["id"]),
        email_value,
        int(time.time()) + CITIZEN_SESSION_SECONDS,
    )
    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie(
        key=CITIZEN_SESSION_COOKIE,
        value=session_token,
        max_age=CITIZEN_SESSION_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    _clear_oauth_cookies(response, provider, secure)
    return response


@router.post("/login")
def team_login(payload: TeamLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    now = int(time.time())
    remote_addr = _remote_address(request)
    if database.count_recent_team_login_attempts(remote_addr, now - LOGIN_WINDOW_SECONDS) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")

    user = database.get_team_user(payload.email)
    encoded_hash = str(user["password_hash"]) if user else DUMMY_PASSWORD_HASH
    valid_password = verify_password(payload.password, encoded_hash)
    if user is None or not bool(user["is_active"]) or not valid_password:
        database.record_team_login_attempt(remote_addr, now)
        raise HTTPException(status_code=401, detail="Work email or password is incorrect.")

    database.clear_team_login_attempts(remote_addr)
    token = secrets.token_urlsafe(32)
    expires_at = now + SESSION_SECONDS
    database.create_team_session(session_fingerprint(token), payload.email, expires_at)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "email": payload.email}


@router.get("/me")
def team_session(user: dict[str, str] = Depends(require_team_user)) -> dict[str, object]:
    return {"authenticated": True, "email": user["email"]}


@router.post("/logout")
def team_logout(request: Request, response: Response, _: dict[str, str] = Depends(require_team_user)) -> dict[str, bool]:
    require_same_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        database.delete_team_session(session_fingerprint(token))
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}


@citizen_router.post("/register")
def citizen_register(payload: CitizenSignupRequest, request: Request, response: Response) -> dict[str, Any]:
    require_same_origin(request)
    if not payload.accepted_terms:
        raise HTTPException(status_code=400, detail="You must accept the terms and privacy policy.")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    normalized_email = normalize_email(payload.email)
    existing = database.get_citizen_user_by_email(normalized_email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this email.")

    password_hash = hash_password(payload.password)
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    user_id = secrets.token_urlsafe(16)
    try:
        database.create_citizen_user(
            user_id,
            payload.full_name,
            normalized_email,
            payload.phone,
            password_hash,
            True,
            created_at,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account already exists for this email.") from None

    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + CITIZEN_SESSION_SECONDS
    database.create_citizen_session(citizen_session_fingerprint(token), user_id, normalized_email, expires_at)
    response.set_cookie(
        key=CITIZEN_SESSION_COOKIE,
        value=token,
        max_age=CITIZEN_SESSION_SECONDS,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "email": normalized_email, "full_name": payload.full_name}


@citizen_router.post("/login")
def citizen_login(payload: CitizenLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    require_same_origin(request)
    now = int(time.time())
    remote_addr = _remote_address(request)
    if database.count_recent_team_login_attempts(remote_addr, now - LOGIN_WINDOW_SECONDS) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")

    normalized_email = normalize_email(payload.email)
    user = database.get_citizen_user_by_email(normalized_email)
    encoded_hash = str(user["password_hash"]) if user else DUMMY_PASSWORD_HASH
    valid_password = verify_password(payload.password, encoded_hash)
    if user is None or not bool(user["is_active"]) or not valid_password:
        database.record_team_login_attempt(remote_addr, now)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    database.clear_team_login_attempts(remote_addr)
    token = secrets.token_urlsafe(32)
    expires_at = now + CITIZEN_SESSION_SECONDS
    database.create_citizen_session(citizen_session_fingerprint(token), str(user["id"]), normalized_email, expires_at)
    response.set_cookie(
        key=CITIZEN_SESSION_COOKIE,
        value=token,
        max_age=CITIZEN_SESSION_SECONDS,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "email": normalized_email, "full_name": str(user["full_name"])}


@citizen_router.get("/me")
def citizen_session(user: dict[str, str] = Depends(require_citizen_user)) -> dict[str, object]:
    return {"authenticated": True, "email": user["email"], "id": user["id"]}


@citizen_router.post("/logout")
def citizen_logout(request: Request, response: Response, _: dict[str, str] = Depends(require_citizen_user)) -> dict[str, bool]:
    require_same_origin(request)
    token = request.cookies.get(CITIZEN_SESSION_COOKIE)
    if token:
        database.delete_citizen_session(citizen_session_fingerprint(token))
    response.delete_cookie(
        key=CITIZEN_SESSION_COOKIE,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}