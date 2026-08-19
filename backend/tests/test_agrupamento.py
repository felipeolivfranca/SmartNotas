"""Valida o requisito central: itens semelhantes somados no periodo.

Roda sem chave de API e sem tocar no banco real — usa um SQLite em memoria.

    cd backend
    .\\.venv\\Scripts\\python.exe tests\\test_agrupamento.py
"""

import sys
from datetime import date
from pathlib import Path

# Executado como script, o sys.path recebe tests/ e nao a raiz do backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Item, NotaFiscal
from app.services.dashboard import resumo
from app.services.normalizer import normalizar_nome

engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)


def nota(db, id_, dia, hash_):
    n = NotaFiscal(
        id=id_,
        arquivo_nome=f"nota{id_}.jpg",
        arquivo_hash=hash_,
        arquivo_path=f"/tmp/nota{id_}.jpg",
        estabelecimento="Mercado Teste",
        data_compra=dia,
    )
    db.add(n)
    return n


def item(db, nota_id, descricao, canonico, qtd, valor, dia, unidade="UN", categoria="outros"):
    db.add(
        Item(
            nota_id=nota_id,
            descricao_original=descricao,
            nome_canonico=canonico,
            nome_normalizado=normalizar_nome(canonico),
            categoria=categoria,
            quantidade=qtd,
            unidade=unidade,
            valor_total=valor,
            data_compra=dia,
        )
    )


falhas = []


def checar(rotulo, obtido, esperado):
    ok = obtido == esperado
    print(f"  [{'ok' if ok else 'FALHOU'}] {rotulo}: {obtido!r} (esperado {esperado!r})")
    if not ok:
        falhas.append(rotulo)


with Session(engine) as db:
    d7, d12 = date(2025, 9, 7), date(2025, 9, 12)

    nota(db, 1, d7, "h1")
    nota(db, 2, d12, "h2")
    nota(db, 3, date(2025, 10, 3), "h3")

    # O caso do enunciado: 1 requeijao em 7/9 + 2 em 12/9 = 3 em setembro.
    item(db, 1, "REQ CREM TIROL 200G", "requeijão", 1, 8.50, d7, categoria="laticinios")
    item(db, 2, "REQUEIJAO CREMOSO VIGOR", "Requeijões", 2, 19.80, d12, categoria="laticinios")

    # Variacao de acento/caixa deve cair no mesmo grupo.
    item(db, 1, "LEITE INT ITALAC 1L", "leite integral", 2, 11.00, d7, categoria="laticinios")
    item(db, 2, "LEITE INTEGRAL", "Leite Integral", 1, 5.60, d12, categoria="laticinios")

    # Mesma unidade diferente (KG) nao pode somar junto com UN.
    item(db, 1, "TOMATE KG", "tomate", 0.436, 4.30, d7, unidade="KG", categoria="hortifruti")
    item(db, 2, "TOMATE UNID", "tomate", 2, 3.00, d12, unidade="UN", categoria="hortifruti")

    # Outro mes nao pode entrar no resumo de setembro.
    item(db, 3, "REQ CREM 200G", "requeijão", 5, 45.00, date(2025, 10, 3), categoria="laticinios")

    db.commit()

    r = resumo(db, 2025, 9)

    print("Resumo setembro/2025")
    checar("periodo", r["periodo"], "2025-09")
    checar("total_notas", r["total_notas"], 2)
    checar("total_itens", r["total_itens"], 6)
    checar("produtos_distintos", r["produtos_distintos"], 4)
    checar("total_gasto", r["total_gasto"], round(8.50 + 19.80 + 11.00 + 5.60 + 4.30 + 3.00, 2))

    por_chave = {i["chave"]: i for i in r["itens"]}
    print()
    print("Itens agrupados:")
    for i in r["itens"]:
        print(f"  {i['chave']:<24} qtd={i['quantidade']:<7} total={i['valor_total']:<7} {i['datas']}")

    print()
    req = por_chave.get("requeijao|UN")
    checar("requeijao existe", req is not None, True)
    if req:
        # Entre "requeijão" e "Requeijões", o rotulo tem de ser a forma correta:
        # acentuada e no singular, nunca a chave sem acento nem o plural.
        checar("requeijao rotulo", req["nome"], "requeijão")
        checar("requeijao categoria", req["categoria"], "laticinios")
        checar("requeijao quantidade", req["quantidade"], 3.0)
        checar("requeijao valor_total", req["valor_total"], 28.30)
        checar("requeijao ocorrencias", req["ocorrencias"], 2)
        checar("requeijao datas", req["datas"], ["2025-09-07", "2025-09-12"])

    leite = por_chave.get("leite integral|UN")
    checar("leite existe", leite is not None, True)
    if leite:
        checar("leite quantidade", leite["quantidade"], 3.0)
        checar("leite valor_total", leite["valor_total"], 16.60)

    checar("tomate KG separado", "tomate|KG" in por_chave, True)
    checar("tomate UN separado", "tomate|UN" in por_chave, True)
    if "tomate|KG" in por_chave:
        checar("tomate KG quantidade", por_chave["tomate|KG"]["quantidade"], 0.436)

    checar("maior gasto e requeijao", r["maior_gasto"]["chave"], "requeijao|UN")

    cats = {c["categoria"]: c for c in r["categorias"]}
    checar("categoria laticinios", cats["laticinios"]["valor_total"], 44.90)
    checar("categoria hortifruti", cats["hortifruti"]["valor_total"], 7.30)

    # Outubro deve ficar isolado.
    r10 = resumo(db, 2025, 10)
    checar("outubro total_itens", r10["total_itens"], 1)
    checar("outubro requeijao qtd", r10["itens"][0]["quantidade"], 5.0)

print()
print("normalizar_nome:")
for entrada, esperado in [
    ("Requeijão Cremoso", "requeijao cremoso"),
    ("REQUEIJÕES", "requeijao"),
    ("Pães", "pao"),
    ("Ovos", "ovo"),
    ("Feijões", "feijao"),
    ("banana", "banana"),
]:
    checar(f"  {entrada}", normalizar_nome(entrada), esperado)

print()
if falhas:
    print(f"{len(falhas)} FALHA(S): {falhas}")
    raise SystemExit(1)
print("TODOS OS TESTES PASSARAM")
