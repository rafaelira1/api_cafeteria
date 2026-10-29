from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Estoque API",
    description="API de estoque usada pela Cafeteria API. Os dados ficam em memória.",
    version="1.0.0",
)

# o id bate com o id do produto na cafeteria
estoque = {
    1: {"ingredient": "Grãos de café", "quantity": 40, "unit": "doses", "minimum": 10},
    2: {"ingredient": "Massa de pão de queijo", "quantity": 25, "unit": "unidades", "minimum": 8},
    3: {"ingredient": "Massa de bolo de chocolate", "quantity": 0, "unit": "fatias", "minimum": 4},
}


class Baixa(BaseModel):
    quantity: int = Field(gt=0)


def montar(product_id: int):
    item = estoque.get(product_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto {product_id} não existe no estoque.",
        )
    return {
        "product_id": product_id,
        **item,
        "low_stock": item["quantity"] <= item["minimum"],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/")
def root():
    return {"message": "Estoque API no ar", "documentation": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/estoque")
def listar():
    return [montar(product_id) for product_id in estoque]


@app.get("/estoque/{product_id}")
def consultar(product_id: int):
    return montar(product_id)


@app.post("/estoque/{product_id}/baixa")
def dar_baixa(product_id: int, data: Baixa):
    item = estoque.get(product_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto {product_id} não existe no estoque.",
        )
    if item["quantity"] < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Estoque insuficiente.",
        )
    item["quantity"] -= data.quantity
    return montar(product_id)
