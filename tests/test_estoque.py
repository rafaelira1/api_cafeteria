import secrets

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.config import get_auth_settings
from app.database import Base, get_db
from app.main import app
from app.models import Product
from estoque_api.main import app as estoque_app, estoque as dados_estoque


@pytest.fixture(autouse=True)
def banco_e_estoque(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://testserver")
    monkeypatch.setenv("ESTOQUE_API_URL", "http://estoque")
    get_auth_settings.cache_clear()

    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'estoque.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine)
    with factory() as db:
        db.add_all(
            [
                Product(id=1, name="Café Expresso", category="Bebidas", price=5.0,
                        size="100ml", is_available=True, calories=5),
                Product(id=2, name="Pão de Queijo", category="Salgados", price=6.5,
                        size="Unidade", is_available=True, calories=180),
                Product(id=3, name="Fatia de Bolo", category="Doces", price=12.0,
                        size="Fatia", is_available=False, calories=420),
            ]
        )
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    # as chamadas para o estoque caem direto na app do mock
    fake = TestClient(estoque_app)

    def request(method, url, **kwargs):
        kwargs.pop("timeout", None)
        return fake.request(method, url.replace("http://estoque", ""), **kwargs)

    monkeypatch.setattr(httpx, "request", request)
    antes = {k: v["quantity"] for k, v in dados_estoque.items()}
    yield
    for k, v in antes.items():
        dados_estoque[k]["quantity"] = v
    app.dependency_overrides.pop(get_db, None)
    test_engine.dispose()
    get_auth_settings.cache_clear()


def test_produto_com_estoque():
    client = TestClient(app)
    response = client.get("/products/1/estoque")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Café Expresso"
    assert body["stock"]["quantity"] == 40
    assert body["can_sell"] is True


def test_produto_sem_estoque_nao_pode_vender():
    client = TestClient(app)
    body = client.get("/products/3/estoque").json()

    assert body["stock"]["quantity"] == 0
    assert body["can_sell"] is False


def test_produto_inexistente():
    client = TestClient(app)
    assert client.get("/products/99/estoque").status_code == 404


def test_pedido_desconta_estoque():
    client = TestClient(app)
    response = client.post(
        "/orders",
        json={
            "customer_name": "Teste",
            "table_number": 1,
            "payment_method": "Pix",
            "quantity": 5,
            "is_takeaway": False,
            "product_id": 1,
        },
    )

    assert response.status_code == 201
    assert dados_estoque[1]["quantity"] == 35


def test_pedido_com_estoque_insuficiente():
    client = TestClient(app)
    response = client.post(
        "/orders",
        json={
            "customer_name": "Teste",
            "table_number": 1,
            "payment_method": "Pix",
            "quantity": 100,
            "is_takeaway": False,
            "product_id": 1,
        },
    )

    assert response.status_code == 409
    assert dados_estoque[1]["quantity"] == 40


def test_estoque_fora_do_ar(monkeypatch):
    def falha(*args, **kwargs):
        raise httpx.ConnectError("caiu")

    monkeypatch.setattr(httpx, "request", falha)
    client = TestClient(app)
    assert client.get("/products/1/estoque").status_code == 503
