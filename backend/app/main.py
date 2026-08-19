"""SmartNotas — API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import dashboard, notas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if not settings.gemini_api_key:
        logging.getLogger(__name__).warning(
            "GEMINI_API_KEY não configurada — o upload de notas vai falhar até "
            "você criar backend/.env a partir do .env.example."
        )
    yield


app = FastAPI(
    title="SmartNotas",
    description="Leitura de notas fiscais com IA e consolidação de gastos por produto.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notas.router)
app.include_router(notas.itens_router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health() -> dict:
    """Usado pelo frontend para avisar se a chave da IA ainda não foi configurada."""
    return {
        "ok": True,
        "ia_configurada": bool(settings.gemini_api_key),
        "modelo": settings.model,
    }
