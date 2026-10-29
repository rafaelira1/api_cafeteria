import os

import httpx
from fastapi import HTTPException, status


def estoque_url() -> str | None:
    url = os.getenv("ESTOQUE_API_URL", "").strip()
    return url.rstrip("/") or None


def chamar(method: str, path: str, **kwargs):
    base = estoque_url()
    try:
        response = httpx.request(method, f"{base}{path}", timeout=5, **kwargs)
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível falar com a API de estoque.",
        ) from error
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado no estoque.",
        )
    if response.status_code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Estoque insuficiente para esse pedido.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A API de estoque respondeu com erro.",
        )
    return response.json()


def consultar_estoque(product_id: int) -> dict:
    return chamar("GET", f"/estoque/{product_id}")


def dar_baixa(product_id: int, quantity: int) -> dict:
    return chamar("POST", f"/estoque/{product_id}/baixa", json={"quantity": quantity})
