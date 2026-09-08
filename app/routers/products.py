from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import MessageResponse, ProductCreate, ProductResponse, ProductUpdate


router = APIRouter(prefix="/products", tags=["Products"])


def find_product(product_id: int, db: Session) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com ID {product_id} não encontrado.",
        )
    return product


@router.get("", response_model=list[ProductResponse], summary="Listar produtos")
def list_products(db: Session = Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.id)).all()


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": MessageResponse}},
    summary="Mostrar um produto",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return find_product(product_id, db)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar produto",
)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": MessageResponse}},
    summary="Substituir produto",
)
def replace_product(
    product_id: int, data: ProductCreate, db: Session = Depends(get_db)
):
    product = find_product(product_id, db)
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": MessageResponse}},
    summary="Editar parcialmente um produto",
)
def update_product(
    product_id: int, data: ProductUpdate, db: Session = Depends(get_db)
):
    product = find_product(product_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": MessageResponse},
        409: {"model": MessageResponse},
    },
    summary="Apagar produto",
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = find_product(product_id, db)
    db.delete(product)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O produto não pode ser apagado porque possui pedidos vinculados.",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
