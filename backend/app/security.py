"""Senha e token de sessão — a parte que não pode ser improvisada.

Duas decisões que valem explicação:

* **bcrypt** guarda o custo dentro do próprio hash, então dá para subir o fator
  de trabalho no futuro sem invalidar as senhas já cadastradas.
* **O token de sessão nunca é gravado em claro.** O banco recebe só o SHA-256
  dele; quem tiver o arquivo `smartnotas.db` em mãos não consegue reconstruir o
  cookie e entrar como outra pessoa.
"""

from __future__ import annotations

import hashlib
import secrets

import bcrypt

# bcrypt trunca em 72 bytes. Em vez de aceitar em silêncio uma senha em que os
# caracteres do fim não valem nada, a API recusa acima disso (ver schemas.py).
SENHA_MAX_BYTES = 72
SENHA_MIN = 8

# Hash descartável de uma senha aleatória. Serve para gastar o mesmo tempo de
# CPU quando o e-mail não existe: sem isso, a diferença de resposta entre
# "e-mail desconhecido" e "senha errada" seria medível no relógio.
_HASH_FALSO = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt())


def gerar_hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def conferir_senha(senha: str, hash_guardado: str | None) -> bool:
    """Compara a senha com o hash. Sempre gasta o tempo de um bcrypt real."""
    bruto = senha.encode("utf-8")[:SENHA_MAX_BYTES]

    if not hash_guardado:
        bcrypt.checkpw(bruto, _HASH_FALSO)
        return False

    try:
        return bcrypt.checkpw(bruto, hash_guardado.encode("ascii"))
    except ValueError:
        # Hash corrompido no banco: trata como senha errada, não como erro 500.
        return False


def gerar_token() -> str:
    """Token do cookie de sessão — 32 bytes de entropia."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
