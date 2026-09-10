import os
from pathlib import Path


TEST_DATABASE = Path(__file__).with_name("test_cafeteria.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"

from fastapi.testclient import TestClient

from app.database import engine
from app.main import app


def setup_module():
    TEST_DATABASE.unlink(missing_ok=True)


def teardown_module():
    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)


def test_initial_data():
    with TestClient(app) as client:
        products = client.get("/products")
        orders = client.get("/orders")

        assert products.status_code == 200
        assert orders.status_code == 200
        assert len(products.json()) == 3
        assert len(orders.json()) == 3
        assert orders.json()[0]["quantity"] == 2
        assert orders.json()[0]["total_amount"] == 10.0


def test_product_crud():
    with TestClient(app) as client:
        created = client.post(
            "/products",
            json={
                "name": "Cappuccino",
                "category": "Bebidas",
                "price": 9.5,
                "size": "250ml",
                "is_available": True,
                "calories": 120,
            },
        )
        assert created.status_code == 201
        product_id = created.json()["id"]

        fetched = client.get(f"/products/{product_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Cappuccino"

        replaced = client.put(
            f"/products/{product_id}",
            json={
                "name": "Cappuccino Grande",
                "category": "Bebidas",
                "price": 12.0,
                "size": "350ml",
                "is_available": True,
                "calories": 170,
            },
        )
        assert replaced.status_code == 200
        assert replaced.json()["size"] == "350ml"

        updated = client.patch(
            f"/products/{product_id}", json={"is_available": False}
        )
        assert updated.status_code == 200
        assert updated.json()["is_available"] is False

        deleted = client.delete(f"/products/{product_id}")
        assert deleted.status_code == 204
        assert client.get(f"/products/{product_id}").status_code == 404


def test_order_crud():
    with TestClient(app) as client:
        created = client.post(
            "/orders",
            json={
                "customer_name": "Daniel Rocha",
                "table_number": 5,
                "payment_method": "Pix",
                "quantity": 2,
                "status": "pending",
                "is_takeaway": False,
                "product_id": 1,
            },
        )
        assert created.status_code == 201
        assert created.json()["total_amount"] == 10.0
        order_id = created.json()["id"]

        fetched = client.get(f"/orders/{order_id}")
        assert fetched.status_code == 200
        assert fetched.json()["customer_name"] == "Daniel Rocha"

        replaced = client.put(
            f"/orders/{order_id}",
            json={
                "customer_name": "Daniel Rocha",
                "table_number": 8,
                "payment_method": "Dinheiro",
                "quantity": 3,
                "status": "preparing",
                "is_takeaway": False,
                "product_id": 2,
            },
        )
        assert replaced.status_code == 200
        assert replaced.json()["table_number"] == 8
        assert replaced.json()["product_id"] == 2
        assert replaced.json()["total_amount"] == 19.5

        updated = client.patch(
            f"/orders/{order_id}",
            json={
                "payment_method": "Cartão",
                "quantity": 4,
                "status": "ready",
                "is_takeaway": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["payment_method"] == "Cartão"
        assert updated.json()["quantity"] == 4
        assert updated.json()["status"] == "ready"
        assert updated.json()["total_amount"] == 26.0

        deleted = client.delete(f"/orders/{order_id}")
        assert deleted.status_code == 204
        assert client.get(f"/orders/{order_id}").status_code == 404


def test_errors_and_validation():
    with TestClient(app) as client:
        assert client.get("/products/9999").status_code == 404
        assert client.get("/orders/9999").status_code == 404

        invalid_order = client.post(
            "/orders",
            json={
                "customer_name": "Cliente",
                "table_number": 1,
                "payment_method": "Pix",
                "quantity": 1,
                "status": "pending",
                "is_takeaway": False,
                "product_id": 9999,
            },
        )
        assert invalid_order.status_code == 404

        invalid_quantity = client.post(
            "/orders",
            json={
                "customer_name": "Cliente",
                "table_number": 1,
                "payment_method": "Pix",
                "quantity": 0,
                "status": "pending",
                "is_takeaway": False,
                "product_id": 1,
            },
        )
        assert invalid_quantity.status_code == 422

        invalid_product = client.post(
            "/products",
            json={
                "name": "Produto inválido",
                "category": "Teste",
                "price": -1,
                "size": "Unidade",
                "is_available": True,
                "calories": 10,
            },
        )
        assert invalid_product.status_code == 422

        conflict = client.delete("/products/1")
        assert conflict.status_code == 409
