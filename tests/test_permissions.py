import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.config import get_auth_settings
from app.auth.dependencies import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import Order, Product, User, UserRole


PEDIDO = {
    "customer_name": "Teste",
    "table_number": 1,
    "payment_method": "Pix",
    "quantity": 1,
    "is_takeaway": False,
    "product_id": 1,
}
PRODUTO = {
    "name": "Suco",
    "category": "Bebidas",
    "price": 7.0,
    "size": "300ml",
    "is_available": True,
    "calories": 90,
}


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ALLOW_INSECURE_HTTP", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://testserver")
    monkeypatch.delenv("ESTOQUE_API_URL", raising=False)
    get_auth_settings.cache_clear()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'perm.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all(
            [
                User(id=1, name="Admin", email="admin@a.com", password_hash="x", role=UserRole.ADMIN),
                User(id=2, name="Staff", email="staff@a.com", password_hash="x", role=UserRole.STAFF),
                User(id=3, name="Ana", email="ana@a.com", password_hash="x", role=UserRole.CUSTOMER),
                User(id=4, name="Bia", email="bia@a.com", password_hash="x", role=UserRole.CUSTOMER),
                Product(id=1, name="Café", category="Bebidas", price=5.0, size="100ml",
                        is_available=True, calories=5),
            ]
        )
        db.commit()
        db.add_all(
            [
                Order(id=1, customer_name="Ana", table_number=1, payment_method="Pix",
                      total_amount=5.0, quantity=1, status="pending", is_takeaway=False,
                      product_id=1, user_id=3),
                Order(id=2, customer_name="Bia", table_number=2, payment_method="Pix",
                      total_amount=5.0, quantity=1, status="pending", is_takeaway=False,
                      product_id=1, user_id=4),
            ]
        )
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()
    get_auth_settings.cache_clear()


def cliente(factory, user_id=None):
    """Cliente https. Com user_id age como esse usuario, sem user_id fica sem login."""
    if user_id is not None:
        with factory() as db:
            user = db.get(User, user_id)
            db.expunge(user)
        app.dependency_overrides[get_current_user] = lambda: user
    else:
        app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app, base_url="https://testserver")


def com_csrf(client):
    token = client.get("/auth/csrf").json()["csrf_token"]
    return {"Origin": "https://testserver", "X-CSRF-Token": token}


def test_sem_login_nao_acessa_pedidos(ambiente):
    client = cliente(ambiente)

    assert client.get("/orders").status_code == 401
    assert client.get("/orders/1").status_code == 401
    assert client.post("/orders", json=PEDIDO).status_code == 401


def test_cardapio_e_publico(ambiente):
    client = cliente(ambiente)

    assert client.get("/products").status_code == 200
    assert client.get("/products/1").status_code == 200


def test_sem_login_nao_altera_produto(ambiente):
    client = cliente(ambiente)

    assert client.post("/products", json=PRODUTO).status_code == 401
    assert client.delete("/products/1").status_code == 401


@pytest.mark.parametrize("user_id", [2, 3])
def test_so_admin_mexe_em_produtos(ambiente, user_id):
    client = cliente(ambiente, user_id)

    assert client.post("/products", json=PRODUTO).status_code == 403
    assert client.put("/products/1", json=PRODUTO).status_code == 403
    assert client.patch("/products/1", json={"price": 9}).status_code == 403
    assert client.delete("/products/1").status_code == 403


def test_admin_cria_produto(ambiente):
    client = cliente(ambiente, 1)

    response = client.post("/products", json=PRODUTO, headers=com_csrf(client))

    assert response.status_code == 201


def test_admin_sem_csrf_e_barrado(ambiente):
    client = cliente(ambiente, 1)

    response = client.post("/products", json=PRODUTO)

    assert response.status_code == 403


def test_cliente_ve_so_os_proprios_pedidos(ambiente):
    client = cliente(ambiente, 3)

    pedidos = client.get("/orders").json()

    assert [p["id"] for p in pedidos] == [1]
    assert client.get("/orders/1").status_code == 200
    assert client.get("/orders/2").status_code == 403


@pytest.mark.parametrize("user_id", [1, 2])
def test_equipe_ve_todos_os_pedidos(ambiente, user_id):
    client = cliente(ambiente, user_id)

    assert len(client.get("/orders").json()) == 2
    assert client.get("/orders/2").status_code == 200


def test_cliente_cria_pedido_e_vira_dono(ambiente):
    client = cliente(ambiente, 3)

    response = client.post("/orders", json=PEDIDO, headers=com_csrf(client))

    assert response.status_code == 201
    novo = response.json()["id"]
    assert client.get(f"/orders/{novo}").status_code == 200
    # a Bia nao enxerga o pedido da Ana
    outro = cliente(ambiente, 4)
    assert outro.get(f"/orders/{novo}").status_code == 403


def test_cliente_nao_altera_nem_apaga_pedido(ambiente):
    client = cliente(ambiente, 3)

    assert client.patch("/orders/1", json={"status": "ready"}).status_code == 403
    assert client.put("/orders/1", json=PEDIDO).status_code == 403
    assert client.delete("/orders/1").status_code == 403


def test_staff_atualiza_status_mas_nao_apaga(ambiente):
    client = cliente(ambiente, 2)
    headers = com_csrf(client)

    patch = client.patch("/orders/1", json={"status": "preparing"}, headers=headers)

    assert patch.status_code == 200
    assert patch.json()["status"] == "preparing"
    assert client.delete("/orders/1", headers=headers).status_code == 403
    assert client.put("/orders/1", json=PEDIDO, headers=headers).status_code == 403


def test_admin_apaga_pedido(ambiente):
    client = cliente(ambiente, 1)

    response = client.delete("/orders/1", headers=com_csrf(client))

    assert response.status_code == 204


def test_estoque_so_para_equipe(ambiente, monkeypatch):
    monkeypatch.setenv("ESTOQUE_API_URL", "http://estoque")

    assert cliente(ambiente).get("/products/1/estoque").status_code == 401
    assert cliente(ambiente, 3).get("/products/1/estoque").status_code == 403
