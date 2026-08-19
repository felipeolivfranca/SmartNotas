"""Configuração central lida do ambiente (.env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Settings:
    # Banco: arquivo SQLite dentro de backend/data/
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL") or f"sqlite:///{self.DATA_DIR / 'smartnotas.db'}"

    # IA
    @property
    def gemini_api_key(self) -> str | None:
        # GOOGLE_API_KEY é o nome que o SDK do Google usa por convenção; aceitar
        # os dois evita a confusão de ter a chave certa sob o nome "errado".
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None

    @property
    def model(self) -> str:
        return os.getenv("SMARTNOTAS_MODEL", "gemini-3.7-flash")

    # Borda maior da imagem enviada ao modelo. Foto de celular chega com 4000px+
    # e o excedente vira custo de token sem ganho de leitura.
    MAX_IMAGE_EDGE: int = 2400

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
