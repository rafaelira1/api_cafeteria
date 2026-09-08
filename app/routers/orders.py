from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, Product
from app.schemas import MessageResponse, OrderCreate, OrderResponse, OrderUpdate


router = APIRouter(prefix="/orders", tags=["Orders"])


def find_order(order_id: int, db: Session) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {order_id} não encontrado.",
        )
    return order


def ensure_product_exists(product_id: int, db: Session) -> None:
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com ID {product_id} não encontrado.",
        )


@router.get("", response_model=list[OrderResponse], summary="Listar pedidos")
def list_orders(db: Session = Depends(get_db)):
    return db.scalars(select(Order).order_by(Order.id)).all()


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
    ensure_product_exists(data.product_id, db)
    order = Order(**data.model_dump())
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
    ensure_product_exists(data.product_id, db)
    for field, value in data.model_dump().items():
        setattr(order, field, value)
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
    if "product_id" in changes:
        ensure_product_exists(changes["product_id"], db)
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
