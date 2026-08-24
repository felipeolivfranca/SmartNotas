"""Cadastro, login e ciclo de vida da sessão."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Item, NotaFiscal, Sessao, Usuario
from ..security import conferir_senha, gerar_hash_senha, gerar_token, hash_token

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Falha esperada de cadastro/login — vira 4xx, não 500."""


class EmailEmUso(AuthError):
    pass


class CredencialInvalida(AuthError):
    pass


class TentativasDemais(AuthError):
    pass


def _agora() -> datetime:
    """UTC sem tzinfo — é nesse formato que o SQLite devolve o que gravou."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- brute force

# Freio simples contra tentativa em massa de senha. Vive em memória: reinicia
# junto com o servidor e não vale entre processos, o que é suficiente para um
# app que roda local. Um deploy exposto trocaria isto por Redis.
MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 15 * 60

_tentativas: dict[str, list[float]] = {}


def _falhas_recentes(email: str) -> list[float]:
    corte = time.monotonic() - JANELA_SEGUNDOS
    recentes = [t for t in _tentativas.get(email, []) if t > corte]
    if recentes:
        _tentativas[email] = recentes
    else:
        _tentativas.pop(email, None)
    return recentes


def _registrar_falha(email: str) -> None:
    _tentativas.setdefault(email, []).append(time.monotonic())


def _limpar_falhas(email: str) -> None:
    _tentativas.pop(email, None)


# -------------------------------------------------------------------- usuário


def criar_usuario(db: Session, *, nome: str, email: str, senha: str) -> Usuario:
    if db.scalar(select(Usuario).where(Usuario.email == email)) is not None:
        raise EmailEmUso("Já existe uma conta com este e-mail.")

    usuario = Usuario(nome=nome, email=email, senha_hash=gerar_hash_senha(senha))
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # Dois cadastros simultâneos com o mesmo e-mail: o índice único decide.
        db.rollback()
        raise EmailEmUso("Já existe uma conta com este e-mail.") from None
    db.refresh(usuario)

    _adotar_dados_orfaos(db, usuario)
    return usuario


def _adotar_dados_orfaos(db: Session, usuario: Usuario) -> None:
    """Entrega ao primeiro usuário as notas que existiam antes do login.

    Sem isto, quem já usava a versão 0.1 abriria a 0.2 com o dashboard vazio e
    as notas antigas presas no banco, invisíveis para qualquer conta.
    """
    total_usuarios = db.scalar(select(Usuario.id).limit(2).offset(1))
    if total_usuarios is not None:
        return  # não é o primeiro cadastro; órfã que sobrou continua órfã

    orfas = db.execute(
        update(NotaFiscal)
        .where(NotaFiscal.usuario_id.is_(None))
        .values(usuario_id=usuario.id)
    ).rowcount
    db.execute(
        update(Item).where(Item.usuario_id.is_(None)).values(usuario_id=usuario.id)
    )
    db.commit()

    if orfas:
        logger.info("%d nota(s) anteriores ao login atribuídas a %s.", orfas, usuario.email)


def autenticar(db: Session, *, email: str, senha: str) -> Usuario:
    if len(_falhas_recentes(email)) >= MAX_TENTATIVAS:
        raise TentativasDemais(
            "Muitas tentativas de login. Espere alguns minutos e tente de novo."
        )

    usuario = db.scalar(select(Usuario).where(Usuario.email == email))

    # `conferir_senha` gasta o tempo de um bcrypt mesmo com usuario None, para
    # que "e-mail não existe" e "senha errada" não sejam distinguíveis pelo
    # tempo de resposta — nem aqui, nem na mensagem devolvida.
    if not conferir_senha(senha, usuario.senha_hash if usuario else None):
        _registrar_falha(email)
        raise CredencialInvalida("E-mail ou senha incorretos.")

    _limpar_falhas(email)
    assert usuario is not None
    usuario.ultimo_acesso = _agora()
    db.commit()
    return usuario


# -------------------------------------------------------------------- sessão


def abrir_sessao(db: Session, usuario: Usuario) -> str:
    """Cria a sessão e devolve o token em claro — só aqui ele existe legível."""
    _limpar_sessoes_expiradas(db)

    token = gerar_token()
    db.add(
        Sessao(
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            expira_em=_agora() + timedelta(days=settings.session_dias),
        )
    )
    db.commit()
    return token


def usuario_da_sessao(db: Session, token: str) -> Usuario | None:
    sessao = db.scalar(
        select(Sessao).where(
            Sessao.token_hash == hash_token(token),
            Sessao.expira_em > _agora(),
        )
    )
    return sessao.usuario if sessao else None


def encerrar_sessao(db: Session, token: str) -> None:
    db.execute(delete(Sessao).where(Sessao.token_hash == hash_token(token)))
    db.commit()


def _limpar_sessoes_expiradas(db: Session) -> None:
    db.execute(delete(Sessao).where(Sessao.expira_em <= _agora()))
