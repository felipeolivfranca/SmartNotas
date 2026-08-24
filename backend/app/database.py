"""Engine e sessão do SQLAlchemy."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    # SQLite + threads do uvicorn
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bancos criados antes do login não têm dono nas notas. Estas instruções levam
# um banco da versão 0.1 para a 0.2 sem precisar apagá-lo; `create_all` sozinho
# não faria isso, porque ele pula tabelas que já existem — índices inclusive.
_MIGRACAO_LOGIN = [
    # A coluna entra aceitando NULL porque o SQLite não sabe adicionar uma
    # coluna NOT NULL a uma tabela com linhas. Quem adota essas linhas órfãs é
    # o primeiro cadastro (ver services/auth.criar_usuario).
    "ALTER TABLE notas_fiscais ADD COLUMN usuario_id INTEGER",
    "ALTER TABLE itens ADD COLUMN usuario_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_notas_fiscais_usuario_id ON notas_fiscais (usuario_id)",
    "CREATE INDEX IF NOT EXISTS ix_itens_usuario_id ON itens (usuario_id)",
    # O hash do arquivo era único no banco inteiro; agora é único por usuário.
    "DROP INDEX IF EXISTS ix_notas_fiscais_arquivo_hash",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_nota_usuario_hash"
    " ON notas_fiscais (usuario_id, arquivo_hash)",
    # O índice de agrupamento passa a começar pelo dono.
    "DROP INDEX IF EXISTS ix_itens_periodo_nome",
    "CREATE INDEX IF NOT EXISTS ix_itens_periodo_nome"
    " ON itens (usuario_id, data_compra, nome_normalizado)",
]


def _migrar_para_multiusuario() -> None:
    """Adiciona a coluna de dono a um banco criado antes do login.

    Roda antes do `create_all` de propósito: com a tabela `notas_fiscais` já
    existente e sem `usuario_id`, criar o índice novo daria "no such column".
    """
    inspetor = inspect(engine)
    tabelas = set(inspetor.get_table_names())
    if "notas_fiscais" not in tabelas:
        return  # banco novo: o create_all já cria tudo na forma final
    if any(c["name"] == "usuario_id" for c in inspetor.get_columns("notas_fiscais")):
        return  # já migrado

    logger.info("Banco anterior ao login detectado — adicionando a coluna de dono.")
    with engine.begin() as conexao:
        for comando in _MIGRACAO_LOGIN:
            conexao.execute(text(comando))


def init_db() -> None:
    from . import models  # noqa: F401  (registra as tabelas no metadata)

    _migrar_para_multiusuario()
    Base.metadata.create_all(bind=engine)
