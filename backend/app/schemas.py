"""Schemas de resposta da API."""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from .security import SENHA_MAX_BYTES, SENHA_MIN

# Validação de e-mail deliberadamente frouxa: aqui ele é só o identificador do
# login, e a regra "tem um @ e um ponto depois" pega o erro de digitação sem
# arrastar a dependência de um validador completo de RFC.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _limpar_email(valor: str) -> str:
    email = valor.strip().lower()
    if not _EMAIL.match(email):
        raise ValueError("E-mail inválido.")
    return email


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    criado_em: datetime


class Credenciais(BaseModel):
    email: str
    senha: str

    _email = field_validator("email")(_limpar_email)


class Registro(BaseModel):
    nome: str
    email: str
    senha: str

    _email = field_validator("email")(_limpar_email)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        nome = " ".join(valor.split())
        if len(nome) < 2:
            raise ValueError("Informe um nome com pelo menos 2 caracteres.")
        return nome[:120]

    @field_validator("senha")
    @classmethod
    def _senha(cls, valor: str) -> str:
        if len(valor) < SENHA_MIN:
            raise ValueError(f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
        if len(valor.encode("utf-8")) > SENHA_MAX_BYTES:
            # Limite do bcrypt. Aceitar em silêncio faria os caracteres do fim
            # não valerem nada — o usuário acharia que tem uma senha maior.
            raise ValueError("A senha é longa demais (máximo de 72 bytes).")
        return valor


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao_original: str
    nome_canonico: str
    categoria: str
    quantidade: float
    unidade: str
    valor_unitario: float | None
    valor_total: float
    data_compra: date | None


class NotaResumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    arquivo_nome: str
    estabelecimento: str | None
    data_compra: date | None
    total_informado: float | None
    total_calculado: float | None
    status: str
    erro_msg: str | None
    modelo_usado: str | None
    criado_em: datetime
    qtd_itens: int = 0


class NotaDetalheOut(NotaResumoOut):
    itens: list[ItemOut] = []


class ItemUpdate(BaseModel):
    """Correção manual — usada para juntar grupos que a IA separou por engano."""

    nome_canonico: str | None = None
    categoria: str | None = None
    quantidade: float | None = None
    valor_total: float | None = None


class ResultadoUpload(BaseModel):
    arquivo: str
    sucesso: bool
    nota_id: int | None = None
    mensagem: str | None = None
    qtd_itens: int = 0
    total: float | None = None
