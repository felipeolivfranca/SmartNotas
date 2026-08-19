"""Tabelas do banco."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    arquivo_nome: Mapped[str] = mapped_column(String(255))
    # Hash do conteúdo: impede subir a mesma foto duas vezes e duplicar o gasto.
    arquivo_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    arquivo_path: Mapped[str] = mapped_column(String(512))

    estabelecimento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_compra: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # total impresso na nota vs. soma dos itens que a IA extraiu; divergência
    # grande é o sinal mais confiável de leitura incompleta.
    total_informado: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_calculado: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="processada")
    erro_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    modelo_usado: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now)

    itens: Mapped[list["Item"]] = relationship(
        back_populates="nota",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Item(Base):
    __tablename__ = "itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nota_id: Mapped[int] = mapped_column(
        ForeignKey("notas_fiscais.id", ondelete="CASCADE"), index=True
    )

    descricao_original: Mapped[str] = mapped_column(String(255))
    # Nome genérico devolvido pela IA ("requeijão"), sem marca nem tamanho.
    nome_canonico: Mapped[str] = mapped_column(String(120))
    # Versão sem acento/caixa do nome canônico — é a chave de agrupamento.
    nome_normalizado: Mapped[str] = mapped_column(String(120), index=True)
    categoria: Mapped[str] = mapped_column(String(32), default="outros", index=True)

    quantidade: Mapped[float] = mapped_column(Float, default=1.0)
    unidade: Mapped[str] = mapped_column(String(8), default="UN")
    valor_unitario: Mapped[float | None] = mapped_column(Float, nullable=True)
    valor_total: Mapped[float] = mapped_column(Float, default=0.0)

    # Desnormalizado a partir da nota: o dashboard filtra por período em cima
    # dos itens, e sem isso todo agregado exigiria um JOIN.
    data_compra: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    nota: Mapped[NotaFiscal] = relationship(back_populates="itens")


# Agrupar "itens semelhantes no mesmo período" é sempre um filtro por data
# seguido de group by nome — este índice cobre exatamente esse acesso.
Index("ix_itens_periodo_nome", Item.data_compra, Item.nome_normalizado)
