"""Dependências compartilhadas pelos routers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Usuario
from .services import auth as svc_auth

NAO_AUTENTICADO = HTTPException(status_code=401, detail="Faça login para continuar.")


def usuario_atual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Resolve o dono da requisição a partir do cookie de sessão.

    Toda rota que toca dado de nota depende disto: é o único ponto em que o
    `usuario_id` usado nos filtros é escolhido, e ele nunca vem do cliente.
    """
    token = request.cookies.get(settings.SESSION_COOKIE)
    if not token:
        raise NAO_AUTENTICADO

    usuario = svc_auth.usuario_da_sessao(db, token)
    if usuario is None:
        raise NAO_AUTENTICADO

    return usuario
