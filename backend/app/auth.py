import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Header, HTTPException

from .persistence import organization_for_api_key

AUTH_SECRET = os.getenv("APP_SECRET_KEY", "development-only-change-me")


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return base64.urlsafe_b64encode(salt + digest).decode()


def password_matches(password: str, encoded: str) -> bool:
    raw = base64.urlsafe_b64decode(encoded.encode())
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 240_000), raw[16:])


def _b64(value: bytes) -> str: return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def issue_token(user_id: str, organization_id: str, role: str) -> str:
    header, body = _b64(b'{"alg":"HS256","typ":"JWT"}'), _b64(json.dumps({"sub": user_id, "org": organization_id, "role": role, "exp": int(time.time()) + 3600}).encode())
    signature = _b64(hmac.new(AUTH_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{signature}"


def current_identity(authorization: str | None = Header(default=None), x_api_key: str | None = Header(default=None)) -> dict:
    if x_api_key:
        org = organization_for_api_key(x_api_key)
        if org: return {"org": org, "role": "developer", "auth": "api_key"}
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    try:
        header, body, signature = authorization[7:].split(".")
        expected = _b64(hmac.new(AUTH_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not hmac.compare_digest(signature, expected) or payload["exp"] < time.time(): raise ValueError
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(401, "Invalid or expired token")
