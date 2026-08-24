# SmartNotas

Sistema para descobrir **quais itens estão consumindo o orçamento das compras**.
Você fotografa a nota fiscal, a IA lê os produtos e o dashboard mostra tudo somado
por produto no mês.

Cada pessoa tem a sua conta: você entra com e-mail e senha e vê apenas as
suas notas.

- **Backend:** Python + FastAPI + SQLAlchemy + SQLite
- **Frontend:** React + Vite
- **IA:** Gemini (visão + structured outputs) via SDK oficial `google-genai`
- **Login:** senha em hash bcrypt + sessão em cookie httpOnly

---

## Contas e login

Ao abrir o app pela primeira vez, use **Criar conta** — o cadastro é aberto,
qualquer pessoa com acesso ao endereço pode criar a sua.

O que cada conta enxerga:

- **As notas são privadas.** Toda consulta do dashboard filtra por dono, e uma
  nota de outra conta responde `404` — inclusive na foto original e na exclusão.
- **A mesma nota pode ser lançada por duas contas.** O hash do arquivo, que
  impede o envio em duplicata, é único por usuário e não no banco inteiro: duas
  pessoas da mesma casa podem fotografar a mesma compra.
- **Quem já usava a versão sem login não perde nada.** Na primeira vez que o
  backend sobe, ele adiciona a coluna de dono às tabelas que já existiam, e as
  notas antigas passam para a **primeira conta criada**.

Como a senha e a sessão são guardadas:

| | Como funciona | Por quê |
|---|---|---|
| Senha | hash **bcrypt**, com salt por conta | o fator de trabalho fica dentro do hash, então dá para aumentá-lo depois sem invalidar as senhas já cadastradas |
| Sessão | cookie `httpOnly`, `SameSite=Lax` | fora do alcance do JavaScript da página e não acompanha requisição vinda de outro site |
| Token | só o SHA-256 dele vai para o banco | quem copiar o `smartnotas.db` não consegue reconstruir o cookie e entrar como você |
| Logout | apaga a sessão no servidor | um token copiado antes do logout para de valer na hora |

Login errado responde sempre **"E-mail ou senha incorretos"**, sem dizer qual dos
dois falhou — a resposta contrária entregaria a lista de quem tem conta. Depois
de 5 tentativas erradas no mesmo e-mail, novas tentativas são barradas por 15
minutos.

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

### 3. Sessão (opcional)

| Variável | Padrão | Para que serve |
|---|---|---|
| `SMARTNOTAS_SESSION_DIAS` | `14` | dias que um login vale antes de pedir a senha de novo |
| `SMARTNOTAS_COOKIE_SECURE` | `false` | ligue **só** se servir o app por HTTPS: um cookie `Secure` não é enviado em `http://localhost` e o login pararia de funcionar em desenvolvimento |

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

Dois testes, ambos rodando **sem chave de API** e sem tocar o banco real:

```powershell
cd backend
.\.venv\Scripts\python.exe tests\test_agrupamento.py
.\.venv\Scripts\python.exe tests\test_auth.py
```

**`test_agrupamento.py`** — a regra de negócio que mais dói se quebrar. Cobre o
caso do enunciado (1 requeijão em 07/09 + 2 em 12/09 = 3), a fusão de grafias
diferentes, a separação por unidade (KG vs UN), o isolamento entre meses e a
escolha do nome de exibição do grupo.

**`test_auth.py`** — o login, ponta a ponta pelas rotas HTTP de verdade. Ele
começa criando um banco no formato **da versão sem login** para exercitar a
migração, e daí cobre: rotas fechadas sem cookie, cadastro e suas recusas, a
adoção das notas antigas pela primeira conta, logout revogando a sessão no
servidor, o freio de 5 tentativas — e o isolamento: uma conta não lê, não edita
e não apaga a nota da outra.

---

## Estrutura

```
backend/
  app/
    ai/
      extractor.py     # chama o Gemini com a foto e recebe o JSON validado
      schemas.py       # o formato que o modelo é obrigado a devolver
    routers/
      auth.py          # cadastro, login, logout
      notas.py         # upload, listagem, imagem, exclusão, correção de item
      dashboard.py     # resumo mensal e meses disponíveis
    services/
      auth.py          # senha, sessão e o freio de tentativas
      normalizer.py    # chave de agrupamento (acento, caixa, plural)
      dashboard.py     # as agregações do mês
    security.py        # hash bcrypt da senha e token de sessão
    dependencies.py    # resolve o dono da requisição pelo cookie
    models.py          # tabelas usuarios, sessoes, notas_fiscais e itens
    database.py        # engine, sessão e a migração do banco sem login
    config.py          # lê o .env
  data/                # banco SQLite e fotos enviadas (criado ao rodar)

frontend/
  src/
    components/        # Login, Upload, Tiles, BarList, TabelaItens, ListaNotas, EditarItem
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
- **Nota de outra conta responde 404, nunca 403.** Um 403 confirmaria que aquele
  id existe, o que já é informação sobre o dado alheio.
- **O freio de tentativas vive em memória.** Ele reinicia junto com o servidor e
  não vale entre processos — suficiente para um app que roda local, e o ponto a
  trocar por Redis se o app um dia for publicado na internet.
