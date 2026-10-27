import hashlib
import hmac
import re
import secrets
import time
from functools import lru_cache

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException

from app.auth.config import AuthSettings
from app.models import User, UserRole


JWT_ALGORITHM = "HS256"
JWT_ISSUER = "cafeteria-api"
JWT_AUDIENCE = "cafeteria-api/auth"
password_hasher = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    """Unknown emails also perform an Argon2 verification."""
    return hash_password(secrets.token_urlsafe(32))


def authentication_error() -> HTTPException:
    return HTTPException(status_code=401, detail="Autenticação ausente, inválida ou expirada.")


def create_access_token(user: User, settings: AuthSettings) -> tuple[str, dict]:
    issued_at = int(time.time())
    claims = {
        "sub": str(user.id),
        "iat": issued_at,
        "exp": issued_at + settings.token_ttl_seconds,
        "jti": secrets.token_hex(32),
        "role": UserRole(user.role).value,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(claims, settings.signing_key, algorithm=JWT_ALGORITHM), claims


def decode_access_token(token: str, settings: AuthSettings) -> dict:
    try:
        if len(token) > 4096:
            raise jwt.InvalidTokenError()
        claims = jwt.decode(
            token,
            settings.signing_key,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "iat", "exp", "jti", "role", "iss", "aud"]},
        )
        subject = claims["sub"]
        if not isinstance(subject, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", subject):
            raise jwt.InvalidTokenError()
        if int(subject) > 2**63 - 1:
            raise jwt.InvalidTokenError()
        if type(claims["iat"]) is not int or type(claims["exp"]) is not int:
            raise jwt.InvalidTokenError()
        if not 0 < claims["exp"] - claims["iat"] <= settings.token_ttl_seconds:
            raise jwt.InvalidTokenError()
        if not isinstance(claims["jti"], str) or not re.fullmatch(r"[0-9a-f]{64}", claims["jti"]):
            raise jwt.InvalidTokenError()
        if claims["role"] not in {role.value for role in UserRole}:
            raise jwt.InvalidTokenError()
        return claims
    except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError) as error:
        raise authentication_error() from error


def _signature(payload: str, kind: str, binding: str, settings: AuthSettings) -> str:
    # Domain separation keeps CSRF signatures independent from JWT signatures.
    key = hmac.digest(settings.signing_key, b"cafeteria/csrf/key/v1", "sha256")
    message = f"{kind}!{len(binding)}!{binding}!{payload}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def create_csrf_token(kind: str, binding: str, expires_at: int, settings: AuthSettings) -> str:
    payload = f"{expires_at}.{secrets.token_hex(32)}"
    return f"{payload}.{_signature(payload, kind, binding, settings)}"


def validate_csrf_token(token: str, kind: str, binding: str, settings: AuthSettings) -> str:
    """Return the random nonce only after authenticating the signed token."""
    if not re.fullmatch(r"[0-9]{1,12}\.[0-9a-f]{64}\.[0-9a-f]{64}", token):
        raise HTTPException(status_code=403, detail="Proteção CSRF inválida ou ausente.")
    expiry, nonce, signature = token.split(".")
    expected = _signature(f"{expiry}.{nonce}", kind, binding, settings)
    now = int(time.time())
    if (
        not hmac.compare_digest(signature, expected)
        or not now < int(expiry) <= now + settings.token_ttl_seconds
    ):
        raise HTTPException(status_code=403, detail="Proteção CSRF inválida ou ausente.")
    return nonce
