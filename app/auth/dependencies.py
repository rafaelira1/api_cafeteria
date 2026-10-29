import hmac

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.config import AuthSettings, LOCAL_HOSTS, get_auth_settings
from app.auth.security import authentication_error, decode_access_token, validate_csrf_token
from app.database import get_db
from app.models import User, UserRole


def require_auth_transport(
    request: Request, settings: AuthSettings = Depends(get_auth_settings)
) -> None:
    if request.url.scheme == "https":
        return
    if not settings.cookie_secure and request.url.hostname in LOCAL_HOSTS:
        return
    raise HTTPException(status_code=403, detail="A autenticação exige HTTPS; HTTP somente no modo local explícito.")


def require_allowed_origin(request: Request, settings: AuthSettings) -> None:
    # Compare against configuration, never against an untrusted Host/proxy header.
    origin = request.headers.get("origin")
    if origin not in settings.allowed_origins or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Origem não permitida.")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
    _transport: None = Depends(require_auth_transport),
) -> User:
    token = request.cookies.get(settings.auth_cookie)
    if not token:
        raise authentication_error()
    claims = decode_access_token(token, settings)
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise authentication_error()
    # The database is authoritative for both activity and the current role.
    return user


def require_roles(*roles: UserRole):
    """Deixa passar so os perfis informados. Sem login da 401, perfil errado da 403."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Você não tem permissão para essa ação.")
        return user

    return checker


def csrf_binding(request: Request, settings: AuthSettings) -> str:
    token = request.cookies.get(settings.auth_cookie)
    if token:
        return "auth:" + decode_access_token(token, settings)["jti"]
    preauth = request.cookies.get(settings.preauth_cookie, "")
    nonce = validate_csrf_token(preauth, "preauth", "", settings)
    return "preauth:" + nonce


def require_csrf(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
    _transport: None = Depends(require_auth_transport),
) -> None:
    require_allowed_origin(request, settings)
    cookie = request.cookies.get(settings.csrf_cookie, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or len(cookie) > 256 or len(header) > 256:
        raise HTTPException(status_code=403, detail="Proteção CSRF inválida ou ausente.")
    # Compare bytes so non-ASCII untrusted input cannot raise TypeError.
    if not hmac.compare_digest(cookie.encode("utf-8"), header.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Proteção CSRF inválida ou ausente.")
    validate_csrf_token(header, "csrf", csrf_binding(request, settings), settings)
