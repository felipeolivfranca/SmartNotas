"""Schemas de resposta da API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
