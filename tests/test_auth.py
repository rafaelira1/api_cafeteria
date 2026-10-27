"""Exercise cookie authentication without touching the application's SQLite file."""

import json
import secrets
import time
from http.cookies import SimpleCookie
from types import SimpleNamespace

import jwt
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.config import get_auth_settings
from app.auth.rate_limit import login_limiter
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole


ORIGIN = "https://testserver"
PASSWORD = "  Uma senha segura 42!  "
REGISTRATION = {
    "name": "  Ana Souza  ",
    "email": "  ANA@Example.COM  ",
    "password": PASSWORD,
}
SAFE_USER_FIELDS = {"id", "name", "email", "role", "is_active", "created_at"}


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
    monkeypatch.setenv("AUTH_TOKEN_TTL_MINUTES", "30")
    monkeypatch.setenv("AUTH_LOGIN_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("AUTH_LOGIN_WINDOW_SECONDS", "60")
    get_auth_settings.cache_clear()
    login_limiter.clear()
    yield get_auth_settings()
    login_limiter.clear()
    get_auth_settings.cache_clear()


@pytest.fixture
def db_factory(tmp_path, settings):
    del settings
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'auth.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine)

    def override_db():
        with factory() as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    yield factory
    if previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override
    test_engine.dispose()


@pytest.fixture
def client(db_factory):
    del db_factory
    # No context manager: startup would initialize the production database.
    test_client = TestClient(app, base_url=ORIGIN)
    yield test_client
    test_client.close()


def csrf_headers(client):
    response = client.get("/auth/csrf", headers={"Origin": ORIGIN})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def register(client, **changes):
    return client.post(
        "/auth/register", json={**REGISTRATION, **changes}, headers=csrf_headers(client)
    )


def login(client, email="ana@example.com", password=PASSWORD):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=csrf_headers(client),
    )


@pytest.fixture
def authenticated(client):
    assert register(client).status_code == 201
    response = login(client)
    assert response.status_code == 200, response.text
    return client


def cookie_attributes(response, name):
    for header in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(header)
        if name in parsed:
            return parsed[name]
    raise AssertionError(f"Cookie {name} was not set")


def claims_from_cookie(client, settings):
    return jwt.decode(
        client.cookies.get(settings.auth_cookie),
        settings.signing_key,
        algorithms=["HS256"],
        issuer="cafeteria-api",
        audience="cafeteria-api/auth",
    )


def replace_auth_cookie(client, settings, token):
    client.cookies.clear()
    client.cookies.set(settings.auth_cookie, token, domain="testserver.local", path="/")


def test_register_normalizes_email_and_returns_only_safe_fields(client, db_factory):
    response = register(client)
    assert response.status_code == 201
    assert set(response.json()) == SAFE_USER_FIELDS
    assert response.json()["name"] == "Ana Souza"
    assert response.json()["email"] == "ana@example.com"
    assert response.json()["role"] == "customer"
    assert response.json()["is_active"] is True
    assert response.json()["created_at"]
    assert response.headers["cache-control"] == "no-store"
    with db_factory() as db:
        user = db.scalar(select(User))
        assert user.email == "ana@example.com"
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != PASSWORD
        assert PasswordHasher().verify(user.password_hash, PASSWORD)
        assert user.password_hash not in response.text
    assert PASSWORD not in response.text


@pytest.mark.parametrize("email", ["ana@example.com", "ANA@EXAMPLE.COM", " ana@example.com "])
def test_duplicate_email_is_a_conflict(client, db_factory, email):
    assert register(client).status_code == 201
    duplicate = register(client, email=email)
    assert duplicate.status_code == 409
    with db_factory() as db:
        assert len(db.scalars(select(User)).all()) == 1


@pytest.mark.parametrize("role", ["admin", "staff", "customer"])
def test_public_registration_rejects_role_assignment(client, db_factory, role):
    response = register(client, role=role)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    with db_factory() as db:
        assert db.scalar(select(User)) is None


@pytest.mark.parametrize("extra", [{"is_active": False}, {"password_hash": "forged"}])
def test_public_registration_rejects_internal_fields(client, extra):
    assert register(client, **extra).status_code == 422


@pytest.mark.parametrize(
    "invalid",
    [
        {"name": "   "},
        {"name": "a" * 101},
        {"email": "not-an-email"},
        {"password": "short"},
        {"password": " " * 12},
        {"password": "a" * 129},
        {"password": 123456789012},
    ],
)
def test_registration_validation_does_not_echo_inputs(client, invalid):
    response = register(client, **invalid)
    assert response.status_code == 422
    assert "input" not in response.text
    assert PASSWORD not in response.text
    assert "password_hash" not in response.text


@pytest.mark.parametrize("field", ["password", "name"])
@pytest.mark.parametrize("surrogate", ["\ud800", "\udfff"])
def test_registration_rejects_unpaired_unicode_surrogates(client, db_factory, field, surrogate):
    payload = {**REGISTRATION, field: f"invalid Unicode {surrogate} value"}
    response = client.post(
        "/auth/register",
        content=json.dumps(payload),
        headers={**csrf_headers(client), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "input" not in response.text
    assert PASSWORD not in response.text
    assert "invalid Unicode" not in response.text
    assert "\\ud800" not in response.text
    assert "\\udfff" not in response.text
    with db_factory() as db:
        assert db.scalar(select(User)) is None


@pytest.mark.parametrize("surrogate", ["\ud800", "\udfff"])
def test_login_rejects_unpaired_unicode_surrogates(client, surrogate):
    password = f"invalid Unicode {surrogate} password"
    response = client.post(
        "/auth/login",
        content=json.dumps({"email": "ana@example.com", "password": password}),
        headers={**csrf_headers(client), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "input" not in response.text
    assert "invalid Unicode" not in response.text
    assert "\\ud800" not in response.text
    assert "\\udfff" not in response.text


def test_password_whitespace_is_preserved(client):
    assert register(client).status_code == 201
    assert login(client, password=PASSWORD.strip()).status_code == 401
    assert login(client).status_code == 200


def test_login_sets_secure_cookies_and_does_not_return_jwt(client, settings):
    assert register(client).status_code == 201
    response = login(client, email=" ANA@EXAMPLE.COM ")
    assert response.status_code == 200
    token = client.cookies.get(settings.auth_cookie)
    assert token
    assert token not in response.text
    assert "access_token" not in response.json()
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    auth_cookie = cookie_attributes(response, settings.auth_cookie)
    assert auth_cookie["httponly"]
    assert auth_cookie["secure"]
    assert auth_cookie["samesite"].lower() == "lax"
    assert auth_cookie["path"] == "/"
    assert not auth_cookie["domain"]
    assert settings.auth_cookie.startswith("__Host-")
    claims = claims_from_cookie(client, settings)
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert int(auth_cookie["max-age"]) == claims["exp"] - claims["iat"]
    assert isinstance(claims["sub"], str)
    assert len(claims["jti"]) == 64
    assert claims["role"] == "customer"
    csrf_cookie = cookie_attributes(response, settings.csrf_cookie)
    assert not csrf_cookie["httponly"]
    assert csrf_cookie["secure"]
    assert csrf_cookie["samesite"].lower() == "lax"
    assert csrf_cookie["path"] == "/"
    assert not csrf_cookie["domain"]
    assert settings.preauth_cookie not in client.cookies


def test_invalid_credentials_are_generic(client, settings):
    assert register(client).status_code == 201
    wrong_password = login(client, password="Incorrect password!")
    unknown_user = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert settings.auth_cookie not in client.cookies
    assert "Incorrect password!" not in wrong_password.text


def test_me_requires_cookie_and_ignores_authorization(authenticated, settings):
    token = authenticated.cookies.get(settings.auth_cookie)
    authenticated.cookies.clear()
    assert authenticated.get("/auth/me").status_code == 401
    assert authenticated.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 401
    assert authenticated.get(
        "/auth/me", auth=("ana@example.com", PASSWORD)
    ).status_code == 401


def test_me_returns_current_safe_user(authenticated):
    response = authenticated.get("/auth/me")
    assert response.status_code == 200
    assert set(response.json()) == SAFE_USER_FIELDS
    assert response.json()["email"] == "ana@example.com"
    assert response.headers["cache-control"] == "no-store"


def test_current_role_is_loaded_from_database(authenticated, db_factory, settings):
    assert claims_from_cookie(authenticated, settings)["role"] == "customer"
    with db_factory() as db:
        user = db.scalar(select(User))
        user.role = UserRole.STAFF
        db.commit()
    response = authenticated.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "staff"


@pytest.mark.parametrize("change", ["deactivate", "delete"])
def test_inactive_or_deleted_user_is_rejected(authenticated, db_factory, change):
    with db_factory() as db:
        user = db.scalar(select(User))
        if change == "deactivate":
            user.is_active = False
        else:
            db.delete(user)
        db.commit()
    assert authenticated.get("/auth/me").status_code == 401


def test_deleted_users_jwt_cannot_identify_a_newly_registered_user(authenticated, db_factory, settings):
    old_token = authenticated.cookies.get(settings.auth_cookie)
    old_user_id = authenticated.get("/auth/me").json()["id"]
    with db_factory() as db:
        db.delete(db.get(User, old_user_id))
        db.commit()
    new_client = TestClient(app, base_url=ORIGIN)
    try:
        created = register(new_client, name="Outra pessoa", email="other@example.com")
        assert created.status_code == 201
        assert created.json()["id"] != old_user_id
        assert login(new_client, email="other@example.com").status_code == 200
        assert new_client.get("/auth/me").json()["email"] == "other@example.com"
        replace_auth_cookie(authenticated, settings, old_token)
        assert authenticated.get("/auth/me").status_code == 401
    finally:
        new_client.close()


def test_inactive_user_cannot_login(client, db_factory):
    assert register(client).status_code == 201
    with db_factory() as db:
        user = db.scalar(select(User))
        user.is_active = False
        db.commit()
    inactive = login(client)
    unknown = login(client, email="nobody@example.com")
    assert inactive.status_code == 401
    assert inactive.json() == unknown.json()


@pytest.mark.parametrize("token", ["invalid", "", "a.b.c"])
def test_malformed_jwt_is_rejected(authenticated, settings, token):
    replace_auth_cookie(authenticated, settings, token)
    assert authenticated.get("/auth/me").status_code == 401


def test_tampered_jwt_is_rejected(authenticated, settings):
    token = authenticated.cookies.get(settings.auth_cookie)
    header, payload, signature = token.split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    replace_auth_cookie(authenticated, settings, f"{header}.{payload}.{signature}")
    assert authenticated.get("/auth/me").status_code == 401


@pytest.mark.parametrize("missing", ["sub", "iat", "exp", "jti", "role", "iss", "aud"])
def test_required_jwt_claims_are_checked(authenticated, settings, missing):
    claims = claims_from_cookie(authenticated, settings)
    claims.pop(missing)
    token = jwt.encode(claims, settings.signing_key, algorithm="HS256")
    replace_auth_cookie(authenticated, settings, token)
    assert authenticated.get("/auth/me").status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"sub": "0"},
        {"sub": "-1"},
        {"sub": "1.0"},
        {"sub": 1},
        {"sub": "9" * 100},
        {"iat": "invalid"},
        {"iat": True},
        {"exp": "invalid"},
        {"exp": True},
        {"jti": ""},
        {"jti": 123},
        {"role": "superadmin"},
        {"role": []},
        {"role": {}},
        {"iss": "untrusted-issuer"},
        {"aud": "another-api"},
    ],
)
def test_invalid_jwt_claims_are_rejected(authenticated, settings, changes):
    claims = {**claims_from_cookie(authenticated, settings), **changes}
    token = jwt.encode(claims, settings.signing_key, algorithm="HS256")
    replace_auth_cookie(authenticated, settings, token)
    assert authenticated.get("/auth/me").status_code == 401


@pytest.mark.parametrize("case", ["expired", "future", "long-lived", "backward"])
def test_jwt_dates_are_checked(authenticated, settings, case):
    claims = claims_from_cookie(authenticated, settings)
    now = int(time.time())
    if case == "expired":
        claims.update(iat=now - 2000, exp=now - 200)
    elif case == "future":
        claims.update(iat=now + 600, exp=now + 1800)
    elif case == "long-lived":
        claims.update(iat=now, exp=now + 3600)
    else:
        claims.update(iat=now, exp=now - 1)
    token = jwt.encode(claims, settings.signing_key, algorithm="HS256")
    replace_auth_cookie(authenticated, settings, token)
    assert authenticated.get("/auth/me").status_code == 401


@pytest.mark.parametrize("algorithm", ["HS384", "none", "wrong-key"])
def test_server_does_not_trust_jwt_algorithm(authenticated, settings, algorithm):
    claims = claims_from_cookie(authenticated, settings)
    if algorithm == "wrong-key":
        token = jwt.encode(claims, secrets.token_bytes(48), algorithm="HS256")
    elif algorithm == "none":
        token = jwt.encode(claims, key="", algorithm="none")
    else:
        token = jwt.encode(claims, settings.signing_key, algorithm=algorithm)
    replace_auth_cookie(authenticated, settings, token)
    assert authenticated.get("/auth/me").status_code == 401


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login", "/auth/logout"])
def test_mutations_require_csrf_before_login(client, path):
    response = client.post(path, json=REGISTRATION, headers={"Origin": ORIGIN})
    assert response.status_code == 403


def test_preauthentication_cookie_is_httponly(client, settings):
    response = client.get("/auth/csrf", headers={"Origin": ORIGIN})
    preauth = cookie_attributes(response, settings.preauth_cookie)
    assert preauth["httponly"]
    assert preauth["secure"]
    assert preauth["path"] == "/"
    assert preauth["samesite"].lower() == "lax"
    assert not preauth["domain"]
    assert client.cookies.get(settings.csrf_cookie) == response.json()["csrf_token"]


def test_csrf_rejects_missing_cookie_or_mismatched_header(client, settings):
    headers = csrf_headers(client)
    response = client.post(
        "/auth/register", json=REGISTRATION,
        headers={**headers, "X-CSRF-Token": "incorrect"},
    )
    assert response.status_code == 403
    client.cookies.clear()
    assert client.post(
        "/auth/register", json=REGISTRATION, headers=headers
    ).status_code == 403


def test_csrf_rejects_unsigned_double_submit_token(client, settings):
    csrf_headers(client)
    client.cookies.set(settings.csrf_cookie, "attacker-controlled", domain="testserver.local", path="/")
    response = client.post(
        "/auth/register", json=REGISTRATION,
        headers={"Origin": ORIGIN, "X-CSRF-Token": "attacker-controlled"},
    )
    assert response.status_code == 403


def test_csrf_token_is_bound_to_preauthentication_browser(client, settings):
    first_token = csrf_headers(client)["X-CSRF-Token"]
    other_client = TestClient(app, base_url=ORIGIN)
    try:
        csrf_headers(other_client)
        other_client.cookies.set(
            settings.csrf_cookie, first_token, domain="testserver.local", path="/"
        )
        response = other_client.post(
            "/auth/register", json=REGISTRATION,
            headers={"Origin": ORIGIN, "X-CSRF-Token": first_token},
        )
        assert response.status_code == 403
    finally:
        other_client.close()


@pytest.mark.parametrize("logged_in", [False, True])
def test_csrf_rejects_signature_tampering_even_with_matching_cookie(client, settings, logged_in):
    if logged_in:
        assert register(client).status_code == 201
        assert login(client).status_code == 200
    headers = csrf_headers(client)
    expiry, nonce, signature = headers["X-CSRF-Token"].split(".")
    signature = ("a" if signature[0] != "a" else "b") + signature[1:]
    tampered = f"{expiry}.{nonce}.{signature}"
    client.cookies.set(settings.csrf_cookie, tampered, domain="testserver.local", path="/")
    response = client.post(
        "/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": tampered}
    )
    assert response.status_code == 403


@pytest.mark.parametrize("logged_in", [False, True])
def test_csrf_rejects_expired_signed_token(client, settings, logged_in):
    from app.auth.security import create_csrf_token

    if logged_in:
        assert register(client).status_code == 201
        assert login(client).status_code == 200
        binding = "auth:" + claims_from_cookie(client, settings)["jti"]
    else:
        csrf_headers(client)
        binding = "preauth:" + client.cookies.get(settings.preauth_cookie).split(".")[1]
    expired = create_csrf_token("csrf", binding, int(time.time()) - 1, settings)
    client.cookies.set(settings.csrf_cookie, expired, domain="testserver.local", path="/")
    response = client.post(
        "/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": expired}
    )
    assert response.status_code == 403


@pytest.mark.parametrize("failure", ["missing", "expired"])
def test_preauthentication_cookie_failure_requires_new_csrf_flow(client, settings, failure):
    from app.auth.security import create_csrf_token

    headers = csrf_headers(client)
    if failure == "missing":
        client.cookies.delete(settings.preauth_cookie)
    else:
        expired = create_csrf_token("preauth", "", int(time.time()) - 1, settings)
        client.cookies.set(settings.preauth_cookie, expired, domain="testserver.local", path="/")
        csrf = create_csrf_token(
            "csrf", "preauth:" + expired.split(".")[1],
            int(time.time()) + settings.token_ttl_seconds, settings,
        )
        client.cookies.set(settings.csrf_cookie, csrf, domain="testserver.local", path="/")
        headers["X-CSRF-Token"] = csrf
    assert client.post("/auth/register", json=REGISTRATION, headers=headers).status_code == 403
    assert register(client).status_code == 201


@pytest.mark.parametrize("origin", [None, "null", "https://evil.example", ORIGIN + ".evil.example"])
def test_csrf_requires_explicit_allowed_origin(client, origin):
    headers = csrf_headers(client)
    if origin is None:
        headers.pop("Origin")
    else:
        headers["Origin"] = origin
    response = client.post("/auth/register", json=REGISTRATION, headers=headers)
    assert response.status_code == 403


def test_csrf_endpoint_rejects_disallowed_origin(client):
    response = client.get("/auth/csrf", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_csrf_rejects_non_ascii_untrusted_tokens_without_server_error(client, settings):
    non_ascii = "ç".encode("utf-8")
    response = client.post(
        "/auth/register", json=REGISTRATION,
        headers=[
            (b"Origin", ORIGIN.encode("ascii")),
            (b"X-CSRF-Token", non_ascii),
            (b"Cookie", settings.csrf_cookie.encode("ascii") + b"=" + non_ascii),
        ],
    )
    assert response.status_code == 403


def test_csrf_rotates_on_login_and_rejects_preauthentication_token(client, settings):
    assert register(client).status_code == 201
    old_headers = csrf_headers(client)
    response = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": PASSWORD},
        headers=old_headers,
    )
    assert response.status_code == 200
    assert client.cookies.get(settings.csrf_cookie) != old_headers["X-CSRF-Token"]
    assert settings.preauth_cookie not in client.cookies
    # Supplying the old value in both places still fails its authentication binding.
    client.cookies.set(
        settings.csrf_cookie, old_headers["X-CSRF-Token"], domain="testserver.local", path="/"
    )
    assert client.post("/auth/logout", headers=old_headers).status_code == 403
    assert client.get("/auth/me").status_code == 200


def test_csrf_token_is_bound_to_authenticated_jti(authenticated, settings):
    first_token = csrf_headers(authenticated)["X-CSRF-Token"]
    other_client = TestClient(app, base_url=ORIGIN)
    try:
        assert login(other_client).status_code == 200
        other_client.cookies.set(
            settings.csrf_cookie, first_token, domain="testserver.local", path="/"
        )
        response = other_client.post(
            "/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": first_token}
        )
        assert response.status_code == 403
        assert other_client.get("/auth/me").status_code == 200
    finally:
        other_client.close()


def test_authenticated_logout_without_csrf_fails(authenticated):
    assert authenticated.post("/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
    assert authenticated.get("/auth/me").status_code == 200


def test_logout_deletes_cookies_but_does_not_revoke_copied_jwt(authenticated, settings):
    copied_token = authenticated.cookies.get(settings.auth_cookie)
    response = authenticated.post("/auth/logout", headers=csrf_headers(authenticated))
    assert response.status_code == 204
    assert not response.content
    for name in (settings.auth_cookie, settings.csrf_cookie, settings.preauth_cookie):
        assert name not in authenticated.cookies
        deletion = cookie_attributes(response, name)
        assert deletion["max-age"] == "0"
        assert deletion["path"] == "/"
        assert deletion["secure"]
        assert deletion["samesite"].lower() == "lax"
    assert authenticated.get("/auth/me").status_code == 401
    replace_auth_cookie(authenticated, settings, copied_token)
    assert authenticated.get("/auth/me").status_code == 200


def test_csrf_endpoint_recovers_from_expired_authentication(authenticated, settings):
    claims = claims_from_cookie(authenticated, settings)
    now = int(time.time())
    claims.update(iat=now - 2000, exp=now - 200)
    expired = jwt.encode(claims, settings.signing_key, algorithm="HS256")
    replace_auth_cookie(authenticated, settings, expired)
    headers = csrf_headers(authenticated)
    assert settings.auth_cookie not in authenticated.cookies
    assert settings.preauth_cookie in authenticated.cookies
    response = authenticated.post(
        "/auth/login", json={"email": "ana@example.com", "password": PASSWORD},
        headers=headers,
    )
    assert response.status_code == 200


def test_login_rate_limit_is_per_client_and_returns_retry_after(client, settings):
    headers = csrf_headers(client)
    payload = {"email": "nobody@example.com", "password": "wrong password"}
    for _ in range(settings.login_max_attempts):
        assert client.post("/auth/login", json=payload, headers=headers).status_code == 401
    blocked = client.post(
        "/auth/login", json=payload,
        headers={**headers, "X-Forwarded-For": "198.51.100.99"},
    )
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["retry-after"]) <= settings.login_window_seconds
    assert PASSWORD not in blocked.text


def test_successful_login_attempts_are_also_limited(client, settings):
    assert register(client).status_code == 201
    for _ in range(settings.login_max_attempts):
        assert login(client).status_code == 200
    assert login(client).status_code == 429


def test_login_rate_limit_expires_without_sleeping(client, settings, monkeypatch):
    from app.auth import rate_limit

    clock = [1000.0]
    monkeypatch.setattr(rate_limit, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    headers = csrf_headers(client)
    payload = {"email": "nobody@example.com", "password": "wrong password"}
    for _ in range(settings.login_max_attempts):
        assert client.post("/auth/login", json=payload, headers=headers).status_code == 401
    assert client.post("/auth/login", json=payload, headers=headers).status_code == 429
    clock[0] += settings.login_window_seconds + 1
    assert client.post("/auth/login", json=payload, headers=headers).status_code == 401


def test_one_clients_attempts_do_not_block_another_client(client, settings):
    headers = csrf_headers(client)
    payload = {"email": "nobody@example.com", "password": "wrong password"}
    for _ in range(settings.login_max_attempts):
        assert client.post("/auth/login", json=payload, headers=headers).status_code == 401
    assert client.post("/auth/login", json=payload, headers=headers).status_code == 429
    other_client = TestClient(app, base_url=ORIGIN, client=("198.51.100.15", 6000))
    try:
        response = other_client.post(
            "/auth/login", json=payload, headers=csrf_headers(other_client)
        )
        assert response.status_code == 401
    finally:
        other_client.close()


@pytest.mark.parametrize(
    "variable,value",
    [
        ("AUTH_JWT_SECRET", ""),
        ("AUTH_JWT_SECRET", "short-secret"),
        ("AUTH_ALLOWED_ORIGINS", ""),
        ("AUTH_ALLOWED_ORIGINS", "*"),
        ("AUTH_ALLOWED_ORIGINS", "https://*"),
        ("AUTH_ALLOWED_ORIGINS", "https://*.example.com"),
        ("AUTH_ALLOWED_ORIGINS", "https://a b.example"),
        ("AUTH_ALLOWED_ORIGINS", "https://example.com/path"),
        ("AUTH_ALLOWED_ORIGINS", "http://example.com"),
        ("AUTH_TOKEN_TTL_MINUTES", "0"),
        ("AUTH_TOKEN_TTL_MINUTES", "61"),
        ("AUTH_TOKEN_TTL_MINUTES", "invalid"),
        ("AUTH_ALLOW_INSECURE_HTTP", "true"),
    ],
)
def test_auth_configuration_rejects_unsafe_values(settings, monkeypatch, variable, value):
    del settings
    monkeypatch.setenv(variable, value)
    get_auth_settings.cache_clear()
    with pytest.raises(RuntimeError):
        get_auth_settings()


def test_local_http_requires_explicit_development_configuration(settings, monkeypatch):
    assert settings.cookie_secure is True
    monkeypatch.setenv("AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "true")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "http://127.0.0.1:8000")
    get_auth_settings.cache_clear()
    local_settings = get_auth_settings()
    assert local_settings.cookie_secure is False
    assert not local_settings.auth_cookie.startswith("__Host-")


def test_local_http_option_cannot_allow_remote_insecure_origins(settings, monkeypatch):
    del settings
    monkeypatch.setenv("AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "true")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "http://example.com")
    get_auth_settings.cache_clear()
    with pytest.raises(RuntimeError):
        get_auth_settings()


def test_auth_routes_reject_http_without_explicit_configuration(client):
    insecure = TestClient(app, base_url="http://127.0.0.1:8000")
    try:
        assert insecure.get("/auth/csrf").status_code == 403
    finally:
        insecure.close()


def test_explicit_local_http_sets_local_cookies(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "true")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "http://127.0.0.1:8000")
    get_auth_settings.cache_clear()
    settings = get_auth_settings()
    local = TestClient(app, base_url="http://127.0.0.1:8000")
    try:
        csrf = local.get("/auth/csrf")
        assert csrf.status_code == 200
        headers = {
            "Origin": "http://127.0.0.1:8000",
            "X-CSRF-Token": csrf.json()["csrf_token"],
        }
        assert local.post("/auth/register", json=REGISTRATION, headers=headers).status_code == 201
        response = local.post(
            "/auth/login", json={"email": "ana@example.com", "password": PASSWORD},
            headers=headers,
        )
        assert response.status_code == 200
        cookie = cookie_attributes(response, settings.auth_cookie)
        assert cookie["httponly"]
        assert not cookie["secure"]
        assert local.get("/auth/me").status_code == 200
    finally:
        local.close()


def test_explicit_local_http_still_rejects_remote_http_hosts(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "true")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "http://127.0.0.1:8000")
    get_auth_settings.cache_clear()
    remote = TestClient(app, base_url="http://example.com")
    try:
        assert remote.get("/auth/csrf").status_code == 403
    finally:
        remote.close()
