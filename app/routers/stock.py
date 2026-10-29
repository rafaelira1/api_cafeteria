from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import estoque
from app.database import get_db
from app.models import Product
from app.schemas import MessageResponse


router = APIRouter(prefix="/products", tags=["Estoque"])


@router.get(
    "/{product_id}/estoque",
    responses={
        404: {"model": MessageResponse},
        503: {"model": MessageResponse},
    },
    summary="Mostrar o produto com os dados do estoque externo",
)
def product_with_stock(product_id: int, db: Session = Depends(get_db)):
    if estoque.estoque_url() is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A API de estoque não está configurada.",
        )
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com ID {product_id} não encontrado.",
        )
    stock = estoque.consultar_estoque(product_id)
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "is_available": product.is_available,
        "stock": {
            "ingredient": stock["ingredient"],
            "quantity": stock["quantity"],
            "unit": stock["unit"],
            "low_stock": stock["low_stock"],
        },
        # so aparece como vendavel se esta ativo no cardapio e tem estoque
        "can_sell": product.is_available and stock["quantity"] > 0,
    }
