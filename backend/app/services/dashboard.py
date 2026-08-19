"""Agregações do dashboard.

O requisito central: itens semelhantes comprados no mesmo período aparecem
somados. Um requeijão em 07/09 + dois em 12/09 = 3 requeijões em setembro.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from ..models import Item, NotaFiscal
from .normalizer import remover_acentos


def limites_do_mes(ano: int, mes: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return inicio, fim


def meses_disponiveis(db: Session) -> list[dict]:
    """Meses que têm itens, do mais recente para o mais antigo."""
    periodo = func.strftime("%Y-%m", Item.data_compra)
    linhas = db.execute(
        select(
            periodo.label("periodo"),
            func.sum(Item.valor_total).label("total"),
            func.count(func.distinct(Item.nota_id)).label("notas"),
        )
        .where(Item.data_compra.is_not(None))
        .group_by(periodo)
        .order_by(periodo.desc())
    ).all()

    return [
        {
            "periodo": linha.periodo,
            "total_gasto": round(linha.total or 0.0, 2),
            "total_notas": linha.notas,
        }
        for linha in linhas
    ]


def _rotulos_do_grupo(
    db: Session, inicio: date, fim: date
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
    """Escolhe o nome e a categoria de exibição de cada grupo.

    A chave de agrupamento é sem acento e sem plural, então ela não serve de
    rótulo ("requeijao"). Entre as grafias que caíram no grupo, vence a mais
    frequente; no empate, a acentuada e mais curta — que é a forma correta em
    português ("requeijão" em vez de "Requeijões" ou "requeijao").
    """
    linhas = db.execute(
        select(
            Item.nome_normalizado,
            Item.unidade,
            Item.nome_canonico,
            Item.categoria,
            func.count(Item.id).label("vezes"),
        )
        .where(Item.data_compra >= inicio, Item.data_compra < fim)
        .group_by(Item.nome_normalizado, Item.unidade, Item.nome_canonico, Item.categoria)
    ).all()

    nomes: dict[tuple[str, str], tuple] = {}
    categorias: dict[tuple[str, str], tuple] = {}

    for linha in linhas:
        chave = (linha.nome_normalizado, linha.unidade)

        tem_acento = linha.nome_canonico != remover_acentos(linha.nome_canonico)
        candidato = (
            -linha.vezes,
            not tem_acento,
            len(linha.nome_canonico),
            linha.nome_canonico.lower(),
        )
        if chave not in nomes or candidato < nomes[chave][0]:
            nomes[chave] = (candidato, linha.nome_canonico)

        cat = (-linha.vezes, linha.categoria)
        if chave not in categorias or cat < categorias[chave][0]:
            categorias[chave] = (cat, linha.categoria)

    return (
        {chave: valor[1] for chave, valor in nomes.items()},
        {chave: valor[1] for chave, valor in categorias.items()},
    )


def itens_agrupados(db: Session, inicio: date, fim: date) -> list[dict]:
    """Um registro por produto, com quantidade e valor somados no período.

    Agrupa por (nome_normalizado, unidade): somar 2 UN de tomate com 0,4 KG de
    tomate na mesma linha produziria uma quantidade sem significado.
    """
    nomes, categorias = _rotulos_do_grupo(db, inicio, fim)

    linhas = db.execute(
        select(
            Item.nome_normalizado,
            Item.unidade,
            func.sum(Item.quantidade).label("quantidade"),
            func.sum(Item.valor_total).label("valor_total"),
            func.count(Item.id).label("ocorrencias"),
            func.avg(cast(Item.valor_total, Float) / func.nullif(Item.quantidade, 0)).label(
                "preco_medio"
            ),
            func.min(Item.valor_total / func.nullif(Item.quantidade, 0)).label("preco_min"),
            func.max(Item.valor_total / func.nullif(Item.quantidade, 0)).label("preco_max"),
            func.group_concat(func.distinct(Item.data_compra)).label("datas"),
            # Os ids do grupo permitem que a correção manual de nome atinja
            # todas as linhas que hoje caem nele, e não só uma delas.
            func.group_concat(Item.id).label("ids"),
        )
        .where(Item.data_compra >= inicio, Item.data_compra < fim)
        .group_by(Item.nome_normalizado, Item.unidade)
        .order_by(func.sum(Item.valor_total).desc())
    ).all()

    resultado: list[dict] = []
    for linha in linhas:
        datas = sorted((linha.datas or "").split(",")) if linha.datas else []
        chave = (linha.nome_normalizado, linha.unidade)
        resultado.append(
            {
                "chave": f"{linha.nome_normalizado}|{linha.unidade}",
                "nome": nomes.get(chave, linha.nome_normalizado),
                "categoria": categorias.get(chave, "outros"),
                "unidade": linha.unidade,
                "quantidade": round(linha.quantidade or 0.0, 3),
                "valor_total": round(linha.valor_total or 0.0, 2),
                "ocorrencias": linha.ocorrencias,
                "preco_medio": round(linha.preco_medio, 2) if linha.preco_medio else None,
                "preco_min": round(linha.preco_min, 2) if linha.preco_min else None,
                "preco_max": round(linha.preco_max, 2) if linha.preco_max else None,
                "datas": datas,
                "ids": [int(i) for i in (linha.ids or "").split(",") if i],
            }
        )
    return resultado


def por_categoria(db: Session, inicio: date, fim: date) -> list[dict]:
    linhas = db.execute(
        select(
            Item.categoria,
            func.sum(Item.valor_total).label("valor_total"),
            func.count(Item.id).label("itens"),
        )
        .where(Item.data_compra >= inicio, Item.data_compra < fim)
        .group_by(Item.categoria)
        .order_by(func.sum(Item.valor_total).desc())
    ).all()

    return [
        {
            "categoria": linha.categoria,
            "valor_total": round(linha.valor_total or 0.0, 2),
            "itens": linha.itens,
        }
        for linha in linhas
    ]


def resumo(db: Session, ano: int, mes: int) -> dict:
    inicio, fim = limites_do_mes(ano, mes)

    agrupados = itens_agrupados(db, inicio, fim)
    total_gasto = round(sum(i["valor_total"] for i in agrupados), 2)

    total_notas = db.scalar(
        select(func.count(NotaFiscal.id)).where(
            NotaFiscal.data_compra >= inicio, NotaFiscal.data_compra < fim
        )
    )
    total_itens = db.scalar(
        select(func.count(Item.id)).where(Item.data_compra >= inicio, Item.data_compra < fim)
    )

    return {
        "periodo": f"{ano:04d}-{mes:02d}",
        "total_gasto": total_gasto,
        "total_notas": total_notas or 0,
        "total_itens": total_itens or 0,
        "produtos_distintos": len(agrupados),
        # O item mais caro do mês é a resposta direta para "o que está pesando".
        "maior_gasto": agrupados[0] if agrupados else None,
        "itens": agrupados,
        "categorias": por_categoria(db, inicio, fim),
    }
