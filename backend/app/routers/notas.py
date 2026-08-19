"""Upload e gestão de notas fiscais."""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.extractor import ExtracaoError, extrair_nota
from ..ai.schemas import NotaExtraida
from ..config import settings
from ..database import get_db
from ..models import Item, NotaFiscal
from ..schemas import ItemUpdate, NotaDetalheOut, NotaResumoOut, ResultadoUpload
from ..services.normalizer import normalizar_nome

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notas", tags=["notas"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _parse_data(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return datetime.strptime(valor.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Data em formato inesperado devolvida pela IA: %r", valor)
        return None


def _persistir(
    db: Session,
    *,
    arquivo_nome: str,
    arquivo_hash: str,
    arquivo_path: str,
    dados: NotaExtraida,
    modelo: str,
) -> NotaFiscal:
    data_compra = _parse_data(dados.data_compra)
    total_calculado = round(sum(i.valor_total for i in dados.itens), 2)

    nota = NotaFiscal(
        arquivo_nome=arquivo_nome,
        arquivo_hash=arquivo_hash,
        arquivo_path=arquivo_path,
        estabelecimento=dados.estabelecimento,
        cnpj=dados.cnpj,
        data_compra=data_compra,
        total_informado=dados.total_informado,
        total_calculado=total_calculado,
        status="processada",
        erro_msg=dados.observacao,
        modelo_usado=modelo,
    )

    for extraido in dados.itens:
        nota.itens.append(
            Item(
                descricao_original=extraido.descricao_original,
                nome_canonico=extraido.nome_canonico.strip(),
                nome_normalizado=normalizar_nome(extraido.nome_canonico),
                categoria=extraido.categoria.value,
                quantidade=extraido.quantidade,
                unidade=extraido.unidade.value,
                valor_unitario=extraido.valor_unitario,
                valor_total=extraido.valor_total,
                data_compra=data_compra,
            )
        )

    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


@router.post("/upload", response_model=list[ResultadoUpload])
async def upload_notas(
    arquivos: list[UploadFile],
    db: Session = Depends(get_db),
) -> list[ResultadoUpload]:
    """Recebe uma ou mais fotos de nota, extrai os itens e grava no banco.

    Cada arquivo é independente: uma foto ilegível não impede as outras.
    """
    resultados: list[ResultadoUpload] = []

    for arquivo in arquivos:
        nome = arquivo.filename or "sem-nome"
        try:
            conteudo = await arquivo.read()

            if not conteudo:
                raise ExtracaoError("Arquivo vazio.")
            if len(conteudo) > MAX_UPLOAD_BYTES:
                raise ExtracaoError("Arquivo maior que 20 MB.")

            arquivo_hash = hashlib.sha256(conteudo).hexdigest()
            existente = db.scalar(
                select(NotaFiscal).where(NotaFiscal.arquivo_hash == arquivo_hash)
            )
            if existente is not None:
                resultados.append(
                    ResultadoUpload(
                        arquivo=nome,
                        sucesso=False,
                        nota_id=existente.id,
                        mensagem="Esta nota já foi enviada antes — ignorada para não duplicar o gasto.",
                    )
                )
                continue

            dados, modelo = extrair_nota(conteudo, arquivo.content_type or "")

            if not dados.itens:
                raise ExtracaoError(
                    dados.observacao or "Nenhum item legível foi encontrado na imagem."
                )

            destino = settings.UPLOAD_DIR / f"{arquivo_hash[:16]}_{nome}"
            destino.write_bytes(conteudo)

            nota = _persistir(
                db,
                arquivo_nome=nome,
                arquivo_hash=arquivo_hash,
                arquivo_path=str(destino),
                dados=dados,
                modelo=modelo,
            )

            resultados.append(
                ResultadoUpload(
                    arquivo=nome,
                    sucesso=True,
                    nota_id=nota.id,
                    qtd_itens=len(nota.itens),
                    total=nota.total_calculado,
                    mensagem=dados.observacao,
                )
            )

        except ExtracaoError as exc:
            resultados.append(ResultadoUpload(arquivo=nome, sucesso=False, mensagem=str(exc)))
        except Exception:
            logger.exception("Falha inesperada processando %s", nome)
            db.rollback()
            resultados.append(
                ResultadoUpload(
                    arquivo=nome,
                    sucesso=False,
                    mensagem="Erro inesperado ao processar o arquivo. Veja o log do servidor.",
                )
            )
        finally:
            await arquivo.close()

    return resultados


@router.get("", response_model=list[NotaResumoOut])
def listar_notas(db: Session = Depends(get_db)) -> list[NotaResumoOut]:
    notas = db.scalars(
        select(NotaFiscal).order_by(NotaFiscal.data_compra.desc(), NotaFiscal.id.desc())
    ).all()
    return [
        NotaResumoOut.model_validate(nota).model_copy(update={"qtd_itens": len(nota.itens)})
        for nota in notas
    ]


@router.get("/{nota_id}", response_model=NotaDetalheOut)
def obter_nota(nota_id: int, db: Session = Depends(get_db)) -> NotaDetalheOut:
    nota = db.get(NotaFiscal, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return NotaDetalheOut.model_validate(nota).model_copy(update={"qtd_itens": len(nota.itens)})


@router.get("/{nota_id}/imagem")
def imagem_nota(nota_id: int, db: Session = Depends(get_db)) -> FileResponse:
    nota = db.get(NotaFiscal, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    caminho = Path(nota.arquivo_path).resolve()
    # O caminho vem do banco, mas confinar na pasta de uploads mantém a rota
    # incapaz de servir arquivo arbitrário do disco.
    if not caminho.is_relative_to(settings.UPLOAD_DIR.resolve()) or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo original não está mais no disco")
    return FileResponse(caminho, filename=nota.arquivo_nome)


@router.delete("/{nota_id}", status_code=204)
def excluir_nota(nota_id: int, db: Session = Depends(get_db)) -> None:
    nota = db.get(NotaFiscal, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    db.delete(nota)
    db.commit()


itens_router = APIRouter(prefix="/api/itens", tags=["itens"])


@itens_router.patch("/{item_id}")
def atualizar_item(
    item_id: int, alteracao: ItemUpdate, db: Session = Depends(get_db)
) -> dict:
    """Corrige um item lido errado.

    Existe para o caso em que a IA separou o que era o mesmo produto: renomear
    o nome_canonico recalcula a chave de agrupamento e o item passa a somar
    junto com os demais no dashboard.
    """
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    if alteracao.nome_canonico is not None:
        item.nome_canonico = alteracao.nome_canonico.strip()
        item.nome_normalizado = normalizar_nome(item.nome_canonico)
    if alteracao.categoria is not None:
        item.categoria = alteracao.categoria
    if alteracao.quantidade is not None:
        item.quantidade = alteracao.quantidade
    if alteracao.valor_total is not None:
        item.valor_total = alteracao.valor_total

    if alteracao.quantidade is not None or alteracao.valor_total is not None:
        nota = item.nota
        nota.total_calculado = round(sum(i.valor_total for i in nota.itens), 2)

    db.commit()
    return {"ok": True, "nome_normalizado": item.nome_normalizado}
