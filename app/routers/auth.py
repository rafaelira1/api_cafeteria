import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.config import AuthSettings, get_auth_settings
from app.auth.dependencies import (
    get_current_user, require_allowed_origin, require_auth_transport, require_csrf,
)
from app.auth.rate_limit import login_limiter
from app.auth.schemas import CSRFResponse, Credentials, UserRegister, UserResponse
from app.auth.security import (
    create_access_token, create_csrf_token, decode_access_token, dummy_password_hash,
    hash_password, password_hasher, validate_csrf_token, verify_password,
)
from app.database import get_db
from app.models import User, UserRole


class AuthRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def protected_handler(request: Request) -> Response:
            try:
                response = await handler(request)
            except RequestValidationError as error:
                # FastAPI normally echoes invalid inputs, including passwords.
                response = JSONResponse(
                    status_code=422,
                    content={"detail": [
                        {key: item[key] for key in ("type", "loc", "msg")}
                        for item in error.errors()
                    ]},
                )
            except HTTPException as error:
                error.headers = {**(error.headers or {}), "Cache-Control": "no-store"}
                raise
            response.headers["Cache-Control"] = "no-store"
            return response

        return protected_handler


router = APIRouter(
    prefix="/auth", tags=["Authentication"], route_class=AuthRoute,
    dependencies=[Depends(require_auth_transport)],
)


def _set_cookie(
    response: Response, name: str, value: str, max_age: int,
    settings: AuthSettings, *, httponly: bool,
) -> None:
    response.set_cookie(
        name, value, max_age=max_age, secure=settings.cookie_secure,
        httponly=httponly, samesite="lax", path="/",
    )


def _delete_cookie(response: Response, name: str, settings: AuthSettings, *, httponly: bool) -> None:
    response.delete_cookie(
        name, path="/", secure=settings.cookie_secure, httponly=httponly, samesite="lax",
    )


@router.get("/csrf", response_model=CSRFResponse, summary="Obter proteção CSRF")
def get_csrf(
    request: Request, response: Response,
    settings: AuthSettings = Depends(get_auth_settings),
):
    # Same-origin browser GETs may omit Origin; cross-origin requests must pass it.
    if request.headers.get("origin") is not None or request.headers.get("sec-fetch-site") == "cross-site":
        require_allowed_origin(request, settings)
    expires_at = int(time.time()) + settings.token_ttl_seconds
    claims = None
    auth_token = request.cookies.get(settings.auth_cookie)
    if auth_token:
        try:
            claims = decode_access_token(auth_token, settings)
        except HTTPException:
            _delete_cookie(response, settings.auth_cookie, settings, httponly=True)
    if claims:
        binding = "auth:" + claims["jti"]
        expires_at = claims["exp"]
    else:
        preauth = request.cookies.get(settings.preauth_cookie, "")
        try:
            nonce = validate_csrf_token(preauth, "preauth", "", settings)
            expires_at = int(preauth.split(".")[0])
        except HTTPException:
            preauth = create_csrf_token("preauth", "", expires_at, settings)
            nonce = validate_csrf_token(preauth, "preauth", "", settings)
            _set_cookie(
                response, settings.preauth_cookie, preauth,
                max(0, expires_at - int(time.time())), settings, httponly=True,
            )
        binding = "preauth:" + nonce
    csrf = create_csrf_token("csrf", binding, expires_at, settings)
    _set_cookie(
        response, settings.csrf_cookie, csrf, max(0, expires_at - int(time.time())),
        settings, httponly=False,
    )
    return {"csrf_token": csrf}


@router.post(
    "/register", response_model=UserResponse, status_code=201,
    dependencies=[Depends(require_csrf)], summary="Cadastrar um cliente",
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == str(data.email))) is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado.")
    user = User(
        name=data.name, email=str(data.email),
        password_hash=hash_password(data.password.get_secret_value()),
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email já cadastrado.") from error
    db.refresh(user)
    return user


@router.post(
    "/login", response_model=UserResponse,
    dependencies=[Depends(require_csrf)], summary="Entrar com cookie HttpOnly",
)
def login(
    data: Credentials, request: Request, response: Response,
    db: Session = Depends(get_db), settings: AuthSettings = Depends(get_auth_settings),
):
    login_limiter.check(request, settings)
    user = db.scalar(select(User).where(User.email == str(data.email)))
    password = data.password.get_secret_value()
    password_hash = user.password_hash if user is not None else dummy_password_hash()
    valid = verify_password(password, password_hash)
    if user is None or not valid or not user.is_active:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos.")
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    token, claims = create_access_token(user, settings)
    max_age = max(0, claims["exp"] - int(time.time()))
    _set_cookie(response, settings.auth_cookie, token, max_age, settings, httponly=True)
    csrf = create_csrf_token("csrf", "auth:" + claims["jti"], claims["exp"], settings)
    _set_cookie(response, settings.csrf_cookie, csrf, max_age, settings, httponly=False)
    _delete_cookie(response, settings.preauth_cookie, settings, httponly=True)
    return user


@router.get("/me", response_model=UserResponse, summary="Consultar o usuário autenticado")
def me(user: User = Depends(get_current_user)):
    return user


@router.post(
    "/logout", status_code=204, dependencies=[Depends(require_csrf)],
    summary="Remover os cookies de autenticação e CSRF",
)
def logout(response: Response, settings: AuthSettings = Depends(get_auth_settings)):
    _delete_cookie(response, settings.auth_cookie, settings, httponly=True)
    _delete_cookie(response, settings.csrf_cookie, settings, httponly=False)
    _delete_cookie(response, settings.preauth_cookie, settings, httponly=True)
