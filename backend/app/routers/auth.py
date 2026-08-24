"""Cadastro, login e logout."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import usuario_atual
from ..models import Usuario
from ..schemas import Credenciais, Registro, UsuarioOut
from ..services import auth as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _entregar_cookie(resposta: Response, token: str) -> None:
    resposta.set_cookie(
        key=settings.SESSION_COOKIE,
        value=token,
        max_age=settings.session_dias * 24 * 3600,
        httponly=True,  # fora do alcance de qualquer script da página
        samesite="lax",  # o cookie não acompanha requisição vinda de outro site
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/registrar", response_model=UsuarioOut, status_code=201)
def registrar(
    dados: Registro, resposta: Response, db: Session = Depends(get_db)
) -> Usuario:
    """Cria a conta e já deixa a pessoa logada — cadastrar e ter de digitar
    tudo de novo na tela de login seria só atrito."""
    try:
        usuario = svc.criar_usuario(
            db, nome=dados.nome, email=dados.email, senha=dados.senha
        )
    except svc.EmailEmUso as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None

    _entregar_cookie(resposta, svc.abrir_sessao(db, usuario))
    logger.info("Conta criada: %s", usuario.email)
    return usuario


@router.post("/login", response_model=UsuarioOut)
def login(dados: Credenciais, resposta: Response, db: Session = Depends(get_db)) -> Usuario:
    try:
        usuario = svc.autenticar(db, email=dados.email, senha=dados.senha)
    except svc.TentativasDemais as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None
    except svc.CredencialInvalida as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None

    _entregar_cookie(resposta, svc.abrir_sessao(db, usuario))
    return usuario


@router.post("/logout", status_code=204)
def logout(request: Request, resposta: Response, db: Session = Depends(get_db)) -> None:
    """Apaga a sessão no servidor, não só o cookie no navegador.

    Sem isto, um token copiado antes do logout continuaria valendo até expirar.
    """
    token = request.cookies.get(settings.SESSION_COOKIE)
    if token:
        svc.encerrar_sessao(db, token)
    resposta.delete_cookie(settings.SESSION_COOKIE, path="/")


@router.get("/eu", response_model=UsuarioOut)
def eu(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Quem está logado. O frontend chama isto ao abrir para decidir entre a
    tela de login e o dashboard."""
    return usuario
