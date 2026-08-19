# SmartNotas

Sistema para descobrir **quais itens estão consumindo o orçamento das compras**.
Você fotografa a nota fiscal, a IA lê os produtos e o dashboard mostra tudo somado
por produto no mês — um requeijão comprado em 07/09 mais dois em 12/09 aparecem
como **3 requeijões**.

- **Backend:** Python + FastAPI + SQLAlchemy + SQLite
- **Frontend:** React + Vite
- **IA:** Gemini (visão + structured outputs) via SDK oficial `google-genai`

---

## Como o agrupamento funciona

É o coração do sistema, em três camadas:

1. **A IA devolve um `nome_canonico`** — o nome genérico do produto, minúsculo,
   no singular, sem marca e sem tamanho. `REQ CREM TIROL 200G` vira `requeijão`.
2. **O normalizador colapsa as variações** (`app/services/normalizer.py`) —
   remove acento, caixa e plural, então `Requeijão`, `requeijao` e `REQUEIJÕES`
   caem todos na chave `requeijao`.
3. **O dashboard agrupa por (chave, unidade)** — a unidade entra na chave porque
   somar `2 UN de tomate` com `0,436 KG de tomate` produziria um número sem
   significado. Os dois viram linhas separadas.

Quando a IA erra e separa o que era o mesmo produto, o botão **Corrigir** na
tabela renomeia todas as linhas do grupo de uma vez — digitar um nome que já
existe funde os dois grupos.

---

## Configuração

### 1. Chave da API

A leitura das notas usa a API do Gemini. Para gerar a chave:

1. Acesse <https://aistudio.google.com/apikey>
2. **Create API key**
3. Copie a chave (ela só aparece uma vez)

Depois crie o arquivo de configuração:

```powershell
cd backend
copy .env.example .env
```

Abra `backend/.env` e preencha `GEMINI_API_KEY`.

O resto do dashboard funciona sem a chave — só o upload de notas fica bloqueado,
e a interface avisa disso.

### 2. Escolha do modelo

`SMARTNOTAS_MODEL` no `.env` troca o modelo que lê as fotos, sem mexer no código:

| Modelo | Quando usar | Custo (por Mtok) |
|---|---|---|
| `gemini-3.7-flash` *(padrão)* | geração mais nova, melhor leitura em cupom amassado ou desbotado | US$ 0,75 / US$ 3,75 |
| `gemini-3.5-flash-lite` | o mais barato e rápido; erra mais em letra miúda | US$ 0,30 / US$ 2,50 |
| `gemini-2.5-pro` | raciocínio profundo, mais caro e mais lento | US$ 1,25 / US$ 10,00 |

---

## Instalação

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
npm install
```

---

## Rodando

Dois terminais:

```powershell
# terminal 1 — backend em http://127.0.0.1:8000
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```powershell
# terminal 2 — frontend em http://localhost:5173
cd frontend
npm run dev
```

Abra <http://localhost:5173>. O Vite faz proxy de `/api` para o backend, então
não há endereço de servidor espalhado pelo código do frontend.

A documentação interativa da API fica em <http://127.0.0.1:8000/docs>.

---

## Testes

O agrupamento é a regra de negócio que mais dói se quebrar, então ele tem um
teste próprio — que roda **sem chave de API** e num banco em memória:

```powershell
cd backend
.\.venv\Scripts\python.exe tests\test_agrupamento.py
```

Ele cobre o caso do enunciado (1 requeijão em 07/09 + 2 em 12/09 = 3), a fusão de
grafias diferentes, a separação por unidade (KG vs UN), o isolamento entre meses
e a escolha do nome de exibição do grupo.

---

## Estrutura

```
backend/
  app/
    ai/
      extractor.py     # chama o Gemini com a foto e recebe o JSON validado
      schemas.py       # o formato que o modelo é obrigado a devolver
    routers/
      notas.py         # upload, listagem, imagem, exclusão, correção de item
      dashboard.py     # resumo mensal e meses disponíveis
    services/
      normalizer.py    # chave de agrupamento (acento, caixa, plural)
      dashboard.py     # as agregações do mês
    models.py          # tabelas notas_fiscais e itens
    config.py          # lê o .env
  data/                # banco SQLite e fotos enviadas (criado ao rodar)

frontend/
  src/
    components/        # Upload, Tiles, BarList, TabelaItens, ListaNotas, EditarItem
    api.js             # cliente HTTP
    formato.js         # moeda, data e quantidade em pt-BR
```

---

## Detalhes que valem saber

- **Nota duplicada é recusada.** O hash SHA-256 do arquivo é único no banco, então
  reenviar a mesma foto não duplica o gasto.
- **Divergência de total é sinalizada.** O sistema compara o total impresso na nota
  com a soma dos itens que a IA extraiu; diferença acima de R$ 0,05 aparece em
  vermelho na lista de notas — é o sinal mais confiável de leitura incompleta.
- **A imagem é reduzida antes de subir** para no máximo 2400px na borda maior.
  Acima disso o modelo não aproveita a resolução extra, só custaria mais token.
- **Cada arquivo do upload é independente.** Uma foto ilegível não impede as outras
  do mesmo envio.
- **Sem login.** O app foi feito para rodar local, na sua máquina.
