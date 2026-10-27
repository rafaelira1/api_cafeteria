import secrets

import pytest


@pytest.fixture(autouse=True)
def crud_auth_environment(request, monkeypatch):
    """Configure startup for existing CRUD tests without authenticating those routes."""
    if request.path.name != "test_api.py":
        yield
        return
    from app.auth.config import get_auth_settings

    monkeypatch.setenv("AUTH_JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://testserver")
    get_auth_settings.cache_clear()
    yield
    get_auth_settings.cache_clear()
