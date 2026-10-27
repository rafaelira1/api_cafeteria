import base64
import binascii
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlsplit


LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _valid_hostname(hostname: str) -> bool:
    try:
        ip_address(hostname)
        return "%" not in hostname
    except ValueError:
        return len(hostname) <= 253 and all(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in hostname.split(".")
        )


def origin_is_valid(origin: str, *, allow_http: bool) -> bool:
    """Accept complete origins, never wildcard, userinfo, paths or queries."""
    try:
        parsed = urlsplit(origin)
        _ = parsed.port
        return bool(
            parsed.hostname
            and _valid_hostname(parsed.hostname)
            and parsed.netloc
            and not parsed.netloc.endswith(":")
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and origin == f"{parsed.scheme}://{parsed.netloc}"
            and (
                parsed.scheme == "https"
                or (
                    allow_http
                    and parsed.scheme == "http"
                    and parsed.hostname in LOCAL_HOSTS
                )
            )
        )
    except ValueError:
        return False


def _integer(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise RuntimeError(f"{name} deve ser um número inteiro.") from error
    if not 1 <= value <= maximum:
        raise RuntimeError(f"{name} deve estar entre 1 e {maximum}.")
    return value


@dataclass(frozen=True)
class AuthSettings:
    signing_key: bytes = field(repr=False)
    allowed_origins: frozenset[str]
    cookie_secure: bool = True
    token_ttl_minutes: int = 30
    login_max_attempts: int = 5
    login_window_seconds: int = 60

    @property
    def token_ttl_seconds(self) -> int:
        return self.token_ttl_minutes * 60

    @property
    def auth_cookie(self) -> str:
        return self._cookie_name("auth")

    @property
    def csrf_cookie(self) -> str:
        return self._cookie_name("csrf")

    @property
    def preauth_cookie(self) -> str:
        return self._cookie_name("preauth")

    def _cookie_name(self, suffix: str) -> str:
        prefix = "__Host-" if self.cookie_secure else ""
        return f"{prefix}cafeteria_{suffix}"


@lru_cache
def get_auth_settings() -> AuthSettings:
    environment = os.getenv("AUTH_ENVIRONMENT", "production")
    if environment not in {"production", "development"}:
        raise RuntimeError("AUTH_ENVIRONMENT deve ser production ou development.")
    insecure = os.getenv("AUTH_ALLOW_INSECURE_HTTP", "false").lower()
    if insecure not in {"true", "false"}:
        raise RuntimeError("AUTH_ALLOW_INSECURE_HTTP deve ser true ou false.")
    allow_http = insecure == "true"
    if allow_http and environment != "development":
        raise RuntimeError("HTTP local só pode ser habilitado em development.")

    secret = os.getenv("AUTH_JWT_SECRET", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43,}", secret):
        raise RuntimeError(
            "Configure AUTH_JWT_SECRET com pelo menos 32 bytes aleatórios em base64url."
        )
    try:
        key = base64.b64decode(secret + "=" * (-len(secret) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as error:
        raise RuntimeError("AUTH_JWT_SECRET deve estar em base64url.") from error
    if len(key) < 32:
        raise RuntimeError("AUTH_JWT_SECRET deve conter pelo menos 32 bytes aleatórios.")

    origins = frozenset(
        value.strip() for value in os.getenv("AUTH_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    )
    if not origins or any(not origin_is_valid(origin, allow_http=allow_http) for origin in origins):
        raise RuntimeError(
            "AUTH_ALLOWED_ORIGINS exige origens HTTPS explícitas; "
            "HTTP somente em loopback com a opção de desenvolvimento."
        )
    return AuthSettings(
        signing_key=key,
        allowed_origins=origins,
        cookie_secure=not allow_http,
        token_ttl_minutes=_integer("AUTH_TOKEN_TTL_MINUTES", 30, 60),
        login_max_attempts=_integer("AUTH_LOGIN_MAX_ATTEMPTS", 5, 1000),
        login_window_seconds=_integer("AUTH_LOGIN_WINDOW_SECONDS", 60, 3600),
    )
