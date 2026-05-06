from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.web.router import router as web_router
from app.db.base import Base, engine

# Создаём таблицы при старте (для разработки; в prod используй Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Сервис аренды квартир",
    description="REST API для поиска и бронирования квартир",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(web_router)
app.include_router(api_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
