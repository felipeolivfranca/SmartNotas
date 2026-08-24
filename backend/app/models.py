"""Tabelas do banco."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Sempre em minúsculo: e-mail não diferencia caixa, e deixar "Ana@x.com"
    # virar uma conta separada de "ana@x.com" só geraria confusão no login.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(128))

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notas: Mapped[list["NotaFiscal"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )


class Sessao(Base):
    """Login ativo. Uma linha por dispositivo/navegador conectado."""

    __tablename__ = "sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # Só o SHA-256 do token do cookie — ver app/security.py.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expira_em: Mapped[datetime] = mapped_column(DateTime, index=True)

    usuario: Mapped[Usuario] = relationship()


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )

    arquivo_nome: Mapped[str] = mapped_column(String(255))
    # Hash do conteúdo: impede subir a mesma foto duas vezes e duplicar o gasto.
    # A unicidade é por usuário (ver índice no fim do arquivo) — duas pessoas
    # que dividem a mesma casa podem fotografar a mesma nota.
    arquivo_hash: Mapped[str] = mapped_column(String(64))
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

    usuario: Mapped[Usuario] = relationship(back_populates="notas")

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
    # Desnormalizado a partir da nota, pelo mesmo motivo de data_compra: todo
    # agregado do dashboard filtra por dono, e sem esta coluna cada soma
    # precisaria de um JOIN com notas_fiscais.
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
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


# A mesma foto pode existir uma vez por usuário, nunca duas para o mesmo.
# É um índice (e não um UNIQUE de tabela) porque só assim ele pode ser criado
# sobre um banco que já existia — ver a migração em app/database.py.
Index("ux_nota_usuario_hash", NotaFiscal.usuario_id, NotaFiscal.arquivo_hash, unique=True)

# Agrupar "meus itens semelhantes no mesmo período" é sempre um filtro por dono
# e data seguido de group by nome — este índice cobre exatamente esse acesso.
Index("ix_itens_periodo_nome", Item.usuario_id, Item.data_compra, Item.nome_normalizado)
