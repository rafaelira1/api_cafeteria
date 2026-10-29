from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.config import get_auth_settings
from app.bootstrap_demo_users import populate_demo_users
from app.database import (
    Base,
    SessionLocal,
    engine,
    migrate_order_user_id,
    migrate_product_description,
)
from app.routers import auth, orders, products, stock
from app.seed import populate_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    get_auth_settings()  # Refuse startup without a strong key and explicit origins.
    Base.metadata.create_all(bind=engine)
    migrate_product_description()
    migrate_order_user_id()
    with SessionLocal() as db:
        populate_demo_users(db)
        populate_database(db)
    yield


app = FastAPI(
    title="Cafeteria API",
    description=(
        "API REST para gerenciar os itens do cardápio e os pedidos dos clientes "
        "de uma cafeteria. Os dados são persistidos localmente em SQLite."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(products.router)
app.include_router(stock.router)
app.include_router(orders.router)
app.include_router(auth.router)


@app.get("/", tags=["Status"], summary="Apresentar a API")
def root():
    return {
        "message": "Bem-vindo à Cafeteria API!",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Status"], summary="Verificar a saúde da API")
def health():
    return {"status": "ok"}
