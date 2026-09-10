from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, Product
from app.schemas import (
    MessageResponse,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderUpdate,
)


router = APIRouter(prefix="/orders", tags=["Orders"])


def find_order(order_id: int, db: Session) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {order_id} não encontrado.",
        )
    return order


def find_product(product_id: int, db: Session) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com ID {product_id} não encontrado.",
        )
    return product


def calculate_total(product: Product, quantity: int) -> float:
    return round(product.price * quantity, 2)


def ensure_available(product: Product) -> None:
    if not product.is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O produto '{product.name}' não está disponível no momento.",
        )


@router.get("", response_model=list[OrderResponse], summary="Listar pedidos")
def list_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    is_takeaway: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(Order)
    if order_status is not None:
        query = query.where(Order.status == order_status)
    if is_takeaway is not None:
        query = query.where(Order.is_takeaway == is_takeaway)
    return db.scalars(query.order_by(Order.id)).all()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    responses={404: {"model": MessageResponse}},
    summary="Mostrar um pedido",
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return find_order(order_id, db)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": MessageResponse}},
    summary="Criar pedido",
)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    product = find_product(data.product_id, db)
    ensure_available(product)
    order = Order(
        **data.model_dump(),
        total_amount=calculate_total(product, data.quantity),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.put(
    "/{order_id}",
    response_model=OrderResponse,
    responses={404: {"model": MessageResponse}},
    summary="Substituir pedido",
)
def replace_order(order_id: int, data: OrderCreate, db: Session = Depends(get_db)):
    order = find_order(order_id, db)
    product = find_product(data.product_id, db)
    ensure_available(product)
    for field, value in data.model_dump().items():
        setattr(order, field, value)
    order.total_amount = calculate_total(product, data.quantity)
    db.commit()
    db.refresh(order)
    return order


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    responses={404: {"model": MessageResponse}},
    summary="Editar parcialmente um pedido",
)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    order = find_order(order_id, db)
    changes = data.model_dump(exclude_unset=True)
    if "product_id" in changes or "quantity" in changes:
        product_id = changes.get("product_id", order.product_id)
        quantity = changes.get("quantity", order.quantity)
        product = find_product(product_id, db)
        if "product_id" in changes:
            ensure_available(product)
        changes["total_amount"] = calculate_total(product, quantity)
    for field, value in changes.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": MessageResponse}},
    summary="Apagar pedido",
)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = find_order(order_id, db)
    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
