import getpass
import secrets
import warnings

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.auth.config import get_auth_settings
from app.create_demo_users import _secure_password, create_demo_users
from app.database import Base
from app.models import Order, Product, User, UserRole


@pytest.fixture
def demo_database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'existing.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield engine, factory
    engine.dispose()


def demo_inputs(*, emails=None, confirmation=None):
    emails = emails or [" ADMIN@EXAMPLE.COM ", "staff@example.com", "customer@example.com"]
    answers = iter(value for role, email in zip(UserRole, emails) for value in (role.value, email))
    password = "  Minha senha privada 42!  "
    passwords = iter(value for _ in UserRole for value in (password, confirmation or password))
    return lambda _: next(answers), lambda _: next(passwords), password


def test_demo_users_are_explicit_with_all_roles_and_private_hashes(demo_database):
    _, factory = demo_database
    input_fn, password_fn, password = demo_inputs()
    with factory() as db:
        assert db.scalar(select(User)) is None
        create_demo_users(db, input_fn=input_fn, password_fn=password_fn)
    with factory() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        assert [user.role for user in users] == list(UserRole)
        assert users[0].email == "admin@example.com"
        assert all(user.is_active for user in users)
        assert len({user.password_hash for user in users}) == 3
        for user in users:
            assert user.password_hash.startswith("$argon2id$")
            assert PasswordHasher().verify(user.password_hash, password)


@pytest.mark.parametrize("failure", ["confirmation", "duplicate", "existing"])
def test_invalid_demo_creation_does_not_partially_insert_or_overwrite(demo_database, failure):
    _, factory = demo_database
    with factory() as db:
        if failure == "existing":
            db.add(User(
                name="Existente", email="customer@example.com", password_hash="existing-hash",
                role=UserRole.STAFF,
            ))
            db.commit()
        input_fn, password_fn, _ = demo_inputs(
            emails=["admin@example.com", "staff@example.com", "ADMIN@example.com"]
            if failure == "duplicate" else None,
            confirmation="Outra senha privada 42!" if failure == "confirmation" else None,
        )
        with pytest.raises(ValueError):
            create_demo_users(db, input_fn=input_fn, password_fn=password_fn)
        db.rollback()
    with factory() as db:
        users = db.scalars(select(User)).all()
        assert len(users) == (1 if failure == "existing" else 0)
        if users:
            assert users[0].password_hash == "existing-hash"
            assert users[0].role == UserRole.STAFF


def test_demo_command_refuses_password_input_without_a_secure_terminal(monkeypatch):
    def insecure_getpass(_):
        warnings.warn("No terminal", getpass.GetPassWarning)
        raise AssertionError("Password fallback must never be reached")

    monkeypatch.setattr(getpass, "getpass", insecure_getpass)
    with pytest.raises(getpass.GetPassWarning):
        _secure_password("Senha: ")


def test_startup_adds_user_table_and_preserves_existing_products_and_orders(tmp_path, monkeypatch):
    from app import database, main

    temp_engine = create_engine(
        f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(bind=temp_engine)
    Product.__table__.create(temp_engine)
    Order.__table__.create(temp_engine)
    with factory() as db:
        db.add(Product(
            id=42, name="Produto existente", description="Preservar descrição", category="Bebidas",
            price=7.5, size="100ml", is_available=True, calories=1,
        ))
        db.flush()
        db.add(Order(
            id=42, customer_name="Cliente existente", table_number=3, payment_method="Pix",
            total_amount=15, quantity=2, status="pending", is_takeaway=False, product_id=42,
        ))
        db.commit()
    assert "users" not in inspect(temp_engine).get_table_names()

    monkeypatch.setenv("AUTH_JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://testserver")
    get_auth_settings.cache_clear()
    monkeypatch.setattr(database, "engine", temp_engine)
    monkeypatch.setattr(database, "SessionLocal", factory)
    monkeypatch.setattr(main, "engine", temp_engine)
    monkeypatch.setattr(main, "SessionLocal", factory)
    try:
        with TestClient(main.app) as client:
            assert "users" in inspect(temp_engine).get_table_names()
            assert [item["id"] for item in client.get("/products").json()] == [42]
            assert [item["id"] for item in client.get("/orders").json()] == [42]
        with factory() as db:
            assert db.get(Product, 42).description == "Preservar descrição"
            assert db.get(Order, 42).total_amount == 15
            assert db.scalar(select(User)) is None
    finally:
        temp_engine.dispose()
        get_auth_settings.cache_clear()


def test_startup_fails_without_signing_key_before_initializing_database(monkeypatch):
    from app import main

    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    get_auth_settings.cache_clear()

    def must_not_create_tables(**_):
        raise AssertionError("An invalid configuration must stop before touching the database")

    monkeypatch.setattr(Base.metadata, "create_all", must_not_create_tables)
    try:
        with pytest.raises(RuntimeError, match="AUTH_JWT_SECRET"):
            with TestClient(main.app):
                pass
    finally:
        get_auth_settings.cache_clear()
