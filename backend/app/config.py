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

    # --- Login ---
    # O cookie de sessão. httpOnly, então o JavaScript da página não o enxerga.
    SESSION_COOKIE: str = "smartnotas_sessao"

    @property
    def session_dias(self) -> int:
        """Quantos dias um login continua valendo sem digitar a senha de novo."""
        try:
            return max(1, int(os.getenv("SMARTNOTAS_SESSION_DIAS", "14")))
        except ValueError:
            return 14

    @property
    def cookie_secure(self) -> bool:
        # Em http://localhost um cookie Secure simplesmente não é enviado, por
        # isso o padrão é desligado. Ligue ao publicar o app atrás de HTTPS.
        return os.getenv("SMARTNOTAS_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"}

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
