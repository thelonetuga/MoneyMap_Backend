# MoneyMap Backend API 🚀

Backend da aplicação **MoneyMap**, desenvolvido em **FastAPI**.
Este sistema gere finanças pessoais, incluindo contas bancárias, transações, categorização automática e portfólio de investimentos (Ações/Crypto).

## 🛠️ Tecnologias

- **Framework:** FastAPI
- **Base de Dados:** SQLAlchemy (PostgreSQL/SQLite)
- **Validação:** Pydantic
- **Autenticação:** OAuth2 com JWT

---

## 🚀 Como Iniciar

### 1. Instalar Dependências
Certifica-te que tens o Python instalado e corre:
```bash
pip install -r requirements.txt
```

### 2. Popular a Base de Dados (Seed)
Para criar as tabelas e inserir dados de teste (Utilizadores, Contas, Transações, Ativos):
```bash
python -m app.seed
```
> **Credenciais de Teste:**
> - **Admin:** `admin@moneymap.com` / `123`
> - **Premium:** `premium@moneymap.com` / `123`
> - **Básico:** `basic@moneymap.com` / `123`

### 3. Correr o Servidor
```bash
uvicorn app.main:app --reload
```
A API ficará disponível em: `http://localhost:8000`
Documentação interativa (Swagger): `http://localhost:8000/docs`

---

## 📚 Visão Geral dos Endpoints

### 🔐 Autenticação (`/auth`)
- `POST /token`: Login (retorna *Access Token*).

### 👤 Utilizadores (`/users`)
- `POST /`: Registar novo utilizador.
- `GET /me`: Ver perfil do utilizador logado.
- `PUT /me`: Atualizar perfil (nome, moeda preferida).

### 🏦 Contas (`/accounts`)
- `GET /`: Listar todas as contas e saldos.
- `POST /`: Criar nova conta (Banco, Corretora, Poupança).

### 💸 Transações (`/transactions`)
- `GET /`: Listar transações (filtros: data, conta, tipo, pesquisa).
- `POST /`: Criar transação (gere automaticamente o saldo da conta e holdings de ativos).
- `PUT / DELETE`: Editar ou apagar transações (reverte saldos automaticamente).

### 📊 Analytics (`/analytics` & `/history`)
- `GET /analytics/spending`: Totais de despesas por categoria (para gráficos).
- `GET /history`: Evolução do património nos últimos 30 dias (cálculo retroativo diário).

### 📈 Portfólio (`/portfolio`)
- `GET /portfolio`: Resumo completo de investimentos.
  - Calcula valor atual das posições (Ações/Crypto).
  - Retorna Lucro/Prejuízo (P/L) e alocação de ativos.

### 📥 Importações (`/imports`)
- `POST /imports/upload`: Upload de ficheiros CSV/Excel.
  - Deteta automaticamente colunas (Data, Descrição, Valor).
  - Cria transações em massa e atualiza saldos.

### ⚙️ Configuração (`/lookups`, `/assets`, `/categories`)
- `GET /lookups/account-types`: Tipos de conta disponíveis.
- `GET /lookups/transaction-types`: Tipos de movimento (Despesa, Receita, Compra/Venda Ativo).
- `GET /assets`: Lista de ativos financeiros suportados (ex: AAPL, BTC).