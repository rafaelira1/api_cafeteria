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


@pytest.fixture(autouse=True)
def admin_logado(request):
    """Os testes de CRUD e de estoque rodam como admin, sem passar pelo login."""
    if request.path.name not in ("test_api.py", "test_estoque.py"):
        yield
        return
    from app.auth.dependencies import get_current_user, require_csrf
    from app.main import app
    from app.models import User, UserRole

    app.dependency_overrides[get_current_user] = lambda: User(
        name="Admin", email="admin@teste.com", role=UserRole.ADMIN, is_active=True
    )
    app.dependency_overrides[require_csrf] = lambda: None
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_csrf, None)
