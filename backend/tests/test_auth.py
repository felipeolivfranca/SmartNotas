"""Valida o login: quem entra, e o que cada um consegue enxergar.

O ponto que mais doi se quebrar nao e "a senha confere", e sim o isolamento:
uma conta nunca pode ver, editar ou apagar nota de outra. Roda sem chave de
API e num banco SQLite temporario, nunca no banco real.

    cd backend
    .\\.venv\\Scripts\\python.exe tests\\test_auth.py
"""

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Precisa vir antes de importar o app: config.py le DATABASE_URL do ambiente,
# e sem isto o teste escreveria no banco de verdade.
_BANCO = Path(tempfile.mkdtemp(prefix="smartnotas-teste-")) / "teste.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_BANCO}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.database import SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Item, NotaFiscal  # noqa: E402
from app.services.normalizer import normalizar_nome  # noqa: E402

# O esquema exato da versao 0.1, antes de existir login. O teste comeca daqui
# para exercitar a migracao de verdade — e nao uma aproximacao dela.
ESQUEMA_ANTIGO = [
    """CREATE TABLE notas_fiscais (
        id INTEGER NOT NULL PRIMARY KEY,
        arquivo_nome VARCHAR(255) NOT NULL,
        arquivo_hash VARCHAR(64) NOT NULL,
        arquivo_path VARCHAR(512) NOT NULL,
        estabelecimento VARCHAR(255),
        cnpj VARCHAR(32),
        data_compra DATE,
        total_informado FLOAT,
        total_calculado FLOAT,
        status VARCHAR(16) NOT NULL,
        erro_msg TEXT,
        modelo_usado VARCHAR(64),
        criado_em DATETIME NOT NULL
    )""",
    "CREATE UNIQUE INDEX ix_notas_fiscais_arquivo_hash ON notas_fiscais (arquivo_hash)",
    "CREATE INDEX ix_notas_fiscais_data_compra ON notas_fiscais (data_compra)",
    """CREATE TABLE itens (
        id INTEGER NOT NULL PRIMARY KEY,
        nota_id INTEGER NOT NULL REFERENCES notas_fiscais(id) ON DELETE CASCADE,
        descricao_original VARCHAR(255) NOT NULL,
        nome_canonico VARCHAR(120) NOT NULL,
        nome_normalizado VARCHAR(120) NOT NULL,
        categoria VARCHAR(32) NOT NULL,
        quantidade FLOAT NOT NULL,
        unidade VARCHAR(8) NOT NULL,
        valor_unitario FLOAT,
        valor_total FLOAT NOT NULL,
        data_compra DATE
    )""",
    "CREATE INDEX ix_itens_nota_id ON itens (nota_id)",
    "CREATE INDEX ix_itens_nome_normalizado ON itens (nome_normalizado)",
    "CREATE INDEX ix_itens_categoria ON itens (categoria)",
    "CREATE INDEX ix_itens_data_compra ON itens (data_compra)",
    "CREATE INDEX ix_itens_periodo_nome ON itens (data_compra, nome_normalizado)",
    # Uma compra ja lancada na versao sem login: arroz de 15/01/2024, R$ 20.
    """INSERT INTO notas_fiscais
        (id, arquivo_nome, arquivo_hash, arquivo_path, estabelecimento,
         data_compra, total_calculado, status, criado_em)
       VALUES (1, 'antiga.jpg', 'hash-antigo', '/tmp/antiga.jpg', 'Mercado Antigo',
               '2024-01-15', 20.0, 'processada', '2024-01-15 10:00:00')""",
    """INSERT INTO itens
        (id, nota_id, descricao_original, nome_canonico, nome_normalizado,
         categoria, quantidade, unidade, valor_total, data_compra)
       VALUES (1, 1, 'ARROZ TIPO 1 5KG', 'arroz', 'arroz',
               'mercearia', 1, 'UN', 20.0, '2024-01-15')""",
]

falhas = []


def checar(rotulo, obtido, esperado):
    ok = obtido == esperado
    marca = "ok" if ok else "FALHOU"
    print(f"  [{marca}] {rotulo}: {obtido!r} (esperado {esperado!r})")
    if not ok:
        falhas.append(rotulo)


def semear_nota(usuario_id, dia, hash_, nome_item, valor):
    """Insere uma nota direto no banco — o upload de verdade exigiria a IA."""
    with SessionLocal() as db:
        nota = NotaFiscal(
            usuario_id=usuario_id,
            arquivo_nome=f"{hash_}.jpg",
            arquivo_hash=hash_,
            arquivo_path=f"/tmp/{hash_}.jpg",
            estabelecimento="Mercado Teste",
            data_compra=dia,
            total_calculado=valor,
        )
        nota.itens.append(
            Item(
                usuario_id=usuario_id,
                descricao_original=nome_item.upper(),
                nome_canonico=nome_item,
                nome_normalizado=normalizar_nome(nome_item),
                categoria="mercearia",
                quantidade=1,
                unidade="UN",
                valor_total=valor,
                data_compra=dia,
            )
        )
        db.add(nota)
        db.commit()
        return nota.id, nota.itens[0].id


print("Migracao de um banco da versao sem login")
with engine.begin() as conexao:
    for comando in ESQUEMA_ANTIGO:
        conexao.execute(text(comando))

init_db()

colunas = {c["name"] for c in inspect(engine).get_columns("notas_fiscais")}
indices = {i["name"] for i in inspect(engine).get_indexes("notas_fiscais")}
checar("coluna de dono criada", "usuario_id" in colunas, True)
checar("hash deixou de ser unico no banco todo", "ix_notas_fiscais_arquivo_hash" in indices, False)
checar("hash virou unico por usuario", "ux_nota_usuario_hash" in indices, True)
checar("tabela de usuarios criada", "usuarios" in inspect(engine).get_table_names(), True)
# init_db roda a cada boot; rodar de novo num banco ja migrado nao pode quebrar.
init_db()
checar("migracao repetida e inofensiva", "usuario_id" in colunas, True)

print()
with TestClient(app) as ana, TestClient(app) as bruno:
    print("Rotas fechadas sem login")
    checar("GET /api/auth/eu", ana.get("/api/auth/eu").status_code, 401)
    checar("GET /api/notas", ana.get("/api/notas").status_code, 401)
    checar("GET /api/dashboard/resumo", ana.get("/api/dashboard/resumo").status_code, 401)
    checar("POST /api/notas/upload", ana.post("/api/notas/upload").status_code, 401)

    print()
    print("Cadastro")
    r = ana.post(
        "/api/auth/registrar",
        json={"nome": "Ana", "email": "  Ana@Teste.com ", "senha": "senha-forte-1"},
    )
    checar("registrar status", r.status_code, 201)
    checar("email normalizado", r.json()["email"], "ana@teste.com")
    checar("cookie de sessao entregue", bool(ana.cookies.get("smartnotas_sessao")), True)
    checar("eu depois do cadastro", ana.get("/api/auth/eu").json()["nome"], "Ana")

    # A conta nasce logada, entao o cookie ja da acesso as rotas de dado.
    checar("GET /api/notas logada", ana.get("/api/notas").status_code, 200)

    print()
    print("Notas anteriores ao login vao para a primeira conta")
    # Sem isto, quem ja usava a versao 0.1 abriria a 0.2 com dashboard vazio.
    checar("ana herdou a nota antiga", len(ana.get("/api/notas").json()), 1)
    checar(
        "resumo de jan/2024",
        ana.get("/api/dashboard/resumo?mes=2024-01").json()["total_gasto"],
        20.0,
    )

    print()
    print("Cadastro recusado")
    r = ana.post(
        "/api/auth/registrar",
        json={"nome": "Outra", "email": "ana@teste.com", "senha": "senha-forte-2"},
    )
    checar("e-mail repetido", r.status_code, 409)
    checar("motivo do 409", r.json()["detail"], "Já existe uma conta com este e-mail.")

    r = ana.post(
        "/api/auth/registrar",
        json={"nome": "Curta", "email": "curta@teste.com", "senha": "1234"},
    )
    checar("senha curta", r.status_code, 422)
    # O frontend mostra `detail` direto na tela: tem de ser frase, nao JSON.
    checar("motivo legivel", isinstance(r.json()["detail"], str), True)
    checar("motivo da senha curta", r.json()["detail"].startswith("A senha precisa"), True)

    r = ana.post(
        "/api/auth/registrar",
        json={"nome": "Torto", "email": "nao-e-email", "senha": "senha-forte-3"},
    )
    checar("e-mail invalido", r.status_code, 422)
    checar("motivo do e-mail", r.json()["detail"], "E-mail inválido.")

    print()
    print("Login e logout")
    r = bruno.post(
        "/api/auth/registrar",
        json={"nome": "Bruno", "email": "bruno@teste.com", "senha": "outra-senha-9"},
    )
    checar("bruno cadastrado", r.status_code, 201)
    checar("bruno comeca sem notas", len(bruno.get("/api/notas").json()), 0)

    r = bruno.post(
        "/api/auth/login", json={"email": "bruno@teste.com", "senha": "senha-errada"}
    )
    checar("senha errada", r.status_code, 401)
    # A mesma frase para e-mail inexistente e senha errada: dizer qual dos dois
    # falhou entregaria de graca a lista de quem tem conta no sistema.
    checar("motivo generico", r.json()["detail"], "E-mail ou senha incorretos.")

    r = bruno.post(
        "/api/auth/login", json={"email": "naoexiste@teste.com", "senha": "seja-la-o-que"}
    )
    checar(
        "e-mail inexistente da a mesma resposta",
        r.json()["detail"],
        "E-mail ou senha incorretos.",
    )

    r = bruno.post(
        "/api/auth/login", json={"email": "bruno@teste.com", "senha": "outra-senha-9"}
    )
    checar("login correto", r.status_code, 200)
    checar("login devolve o usuario", r.json()["email"], "bruno@teste.com")

    token_antigo = bruno.cookies.get("smartnotas_sessao")
    checar("logout", bruno.post("/api/auth/logout").status_code, 204)
    checar("eu depois do logout", bruno.get("/api/auth/eu").status_code, 401)

    # O logout apaga a sessao no servidor: um token copiado antes nao serve mais.
    bruno.cookies.set("smartnotas_sessao", token_antigo)
    checar("token antigo revogado", bruno.get("/api/auth/eu").status_code, 401)
    bruno.cookies.clear()

    bruno.post("/api/auth/login", json={"email": "bruno@teste.com", "senha": "outra-senha-9"})

    print()
    print("Isolamento entre contas")
    id_ana = ana.get("/api/auth/eu").json()["id"]
    id_bruno = bruno.get("/api/auth/eu").json()["id"]

    nota_ana, item_ana = semear_nota(id_ana, date(2025, 9, 7), "h-ana", "requeijão", 8.50)
    nota_bruno, item_bruno = semear_nota(id_bruno, date(2025, 9, 7), "h-bruno", "cerveja", 60.00)

    checar("ana ve as suas 2 notas", len(ana.get("/api/notas").json()), 2)
    checar("bruno ve 1 nota", len(bruno.get("/api/notas").json()), 1)

    resumo_ana = ana.get("/api/dashboard/resumo?mes=2025-09").json()
    resumo_bruno = bruno.get("/api/dashboard/resumo?mes=2025-09").json()
    checar("total de setembro da ana", resumo_ana["total_gasto"], 8.50)
    checar("total de setembro do bruno", resumo_bruno["total_gasto"], 60.00)
    checar("produto da ana", resumo_ana["itens"][0]["nome"], "requeijão")
    checar("produto do bruno", resumo_bruno["itens"][0]["nome"], "cerveja")

    meses_bruno = [m["periodo"] for m in bruno.get("/api/dashboard/meses").json()]
    checar("jan/2024 da ana nao aparece para o bruno", "2024-01" in meses_bruno, False)

    # O hash do arquivo passou a ser unico por usuario: a mesma nota de casa
    # pode ser lancada pelos dois, mas nenhum dos dois lanca a sua duas vezes.
    semear_nota(id_ana, date(2025, 9, 20), "h-igual", "pão", 7.00)
    semear_nota(id_bruno, date(2025, 9, 20), "h-igual", "pão", 7.00)
    checar("mesma nota em contas diferentes e aceita", len(ana.get("/api/notas").json()), 3)
    try:
        semear_nota(id_ana, date(2025, 9, 21), "h-igual", "pão", 7.00)
        repetida_barrada = False
    except IntegrityError:
        repetida_barrada = True
    checar("mesma nota na mesma conta e barrada", repetida_barrada, True)

    print()
    print("Nota alheia responde 404, nunca 403")
    checar("ler", ana.get(f"/api/notas/{nota_bruno}").status_code, 404)
    checar("baixar a imagem", ana.get(f"/api/notas/{nota_bruno}/imagem").status_code, 404)
    checar(
        "editar item",
        ana.patch(f"/api/itens/{item_bruno}", json={"nome_canonico": "invadido"}).status_code,
        404,
    )
    checar("apagar", ana.delete(f"/api/notas/{nota_bruno}").status_code, 404)
    checar("a nota do bruno continua la", bruno.get(f"/api/notas/{nota_bruno}").status_code, 200)

    # A propria nota, por contraste, responde normalmente.
    checar("ler a propria nota", ana.get(f"/api/notas/{nota_ana}").status_code, 200)
    checar(
        "editar o proprio item",
        ana.patch(f"/api/itens/{item_ana}", json={"nome_canonico": "requeijão"}).status_code,
        200,
    )

    print()
    print("Freio contra tentativa em massa de senha")
    alvo = {"email": "bruno@teste.com", "senha": "chute"}
    codigos = [TestClient(app).post("/api/auth/login", json=alvo).status_code for _ in range(6)]
    checar("as 5 primeiras sao 401", codigos[:5], [401] * 5)
    checar("a 6a e barrada com 429", codigos[5], 429)

print()
if falhas:
    print(f"{len(falhas)} FALHA(S): {falhas}")
    raise SystemExit(1)
print("TODOS OS TESTES PASSARAM")
