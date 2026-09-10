from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Order, Product


PRODUCTS = [
    Product(
        id=1,
        name="Café Expresso",
        category="Bebidas",
        price=5.0,
        size="100ml",
        is_available=True,
        calories=5,
    ),
    Product(
        id=2,
        name="Pão de Queijo",
        category="Salgados",
        price=6.5,
        size="Unidade",
        is_available=True,
        calories=180,
    ),
    Product(
        id=3,
        name="Fatia de Bolo de Chocolate",
        category="Doces",
        price=12.0,
        size="Fatia",
        is_available=False,
        calories=420,
    ),
]

ORDERS = [
    Order(
        id=1,
        customer_name="Ana Souza",
        table_number=4,
        payment_method="Pix",
        total_amount=10.0,
        quantity=2,
        status="delivered",
        is_takeaway=False,
        product_id=1,
    ),
    Order(
        id=2,
        customer_name="Bruno Lima",
        table_number=2,
        payment_method="Cartão",
        total_amount=6.5,
        quantity=1,
        status="ready",
        is_takeaway=True,
        product_id=2,
    ),
    Order(
        id=3,
        customer_name="Carla Mendes",
        table_number=7,
        payment_method="Dinheiro",
        total_amount=12.0,
        quantity=1,
        status="preparing",
        is_takeaway=False,
        product_id=3,
    ),
]


def populate_database(db: Session) -> None:
    product_count = db.scalar(select(func.count()).select_from(Product))
    if product_count == 0:
        db.add_all(PRODUCTS)
        db.commit()

    order_count = db.scalar(select(func.count()).select_from(Order))
    if order_count == 0:
        db.add_all(ORDERS)
        db.commit()
