from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.routers import orders, products
from app.seed import populate_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
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
app.include_router(orders.router)


@app.get("/", tags=["Status"], summary="Apresentar a API")
def root():
    return {
        "message": "Bem-vindo à Cafeteria API!",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Status"], summary="Verificar a saúde da API")
def health():
    return {"status": "ok"}
