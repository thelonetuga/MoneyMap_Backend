# 💰 MoneyMap - Gestor Financeiro Pessoal

O **MoneyMap** é uma aplicação Full-Stack moderna para gestão de património pessoal. A aplicação centraliza contas bancárias, despesas e investimentos (Ações, ETFs, Crypto), oferecendo um dashboard com cálculos de lucros e perdas (P&L) em tempo real e visualização gráfica da alocação de ativos.

## 🚀 Stack Tecnológico

### Backend (API)
* **Python 3.10+**
* **FastAPI:** Framework web moderno e de alta performance.
* **SQLAlchemy 2.0:** ORM para interação com a base de dados.
* **Pydantic:** Validação de dados e serialização.

### Frontend (Dashboard)
* **Next.js 14/15:** Framework React com Server Components.
* **TypeScript:** Para tipagem estática e segurança no código.
* **Tailwind CSS:** Estilização rápida e responsiva.
* **Recharts:** Biblioteca para gráficos financeiros.

### Infraestrutura & Dados
* **PostgreSQL:** Base de dados relacional.
* **Docker:** Contentorização da base de dados para fácil setup.

---

## ⚙️ Pré-requisitos

Para rodar este projeto localmente, precisa de ter instalado:
* [Docker Desktop](https://www.docker.com/) (ou Docker Engine no Linux)
* [Python 3.10+](https://www.python.org/)
* [Node.js 20+](https://nodejs.org/) (Recomendado usar via NVM)

---

## 🛠️ Instalação e Configuração

Siga estes passos pela ordem indicada.

### 1. Base de Dados (Docker)
Inicie o contentor do PostgreSQL. Certifique-se que o Docker está a correr.
```bash
docker-compose up -d
2. Backend (API)
Abra um terminal na raiz do projeto:

Bash

# 1. Criar ambiente virtual (Recomendado)
python -m venv venv

# Ativar ambiente virtual:
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 2. Instalar dependências
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic

# 3. Criar as tabelas na Base de Dados
python init_db.py

# 4. Povoar com dados de teste (Seed)
# Gera utilizadores, contas, ativos e histórico de preços fictício
python seed.py

# 5. Iniciar o Servidor
uvicorn main:app --reload
✅ A API ficará disponível em: http://127.0.0.1:8000/docs

3. Frontend (Aplicação Web)
Abra um novo terminal e entre na pasta do frontend:

Bash

cd frontend

# 1. Instalar dependências (Node 20+)
npm install

# 2. Iniciar servidor de desenvolvimento
npm run dev
✅ Aceda à aplicação em: http://localhost:3000

📂 Estrutura do Projeto
Plaintext

/moneymap
├── database/        # Configuração da conexão à BD e Sessão
├── models/          # Modelos SQLAlchemy (Tabelas: User, Account, Transaction...)
├── schemas/         # Schemas Pydantic (Validação de Input/Output)
├── frontend/        # Aplicação Next.js (Pages, Components)
├── main.py          # Ponto de entrada da API (Rotas/Endpoints)
├── init_db.py       # Script para criar tabelas iniciais
├── seed.py          # Script para gerar dados dummy (Seed)
└── docker-compose.yml # Configuração do contentor Postgres
✨ Funcionalidades
Dashboard Unificado: Visão agregada do património líquido (Net Worth).

Investimentos Inteligentes: Cálculo automático de P&L (Lucro/Prejuízo) baseado no preço médio de compra vs. preço atual de mercado.

Histórico de Transações: Registo de despesas e receitas com suporte a categorias e subcategorias.

Normalização de Dados: Tipos de conta e tipos de transação padronizados.

Visualização: Gráfico de "Donut" para análise de alocação de portfólio.

📝 Licença
Este projeto foi desenvolvido para fins educativos e de gestão pessoal.


---

### Conteúdo para o ficheiro `.gitignore`

Copie também isto para o ficheiro `.gitignore` para manter o repositório limpo:

```text
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.env

# Node / Frontend
frontend/node_modules/
frontend/.next/
frontend/.DS_Store
frontend/npm-debug.log*
frontend/yarn-debug.log*
frontend/yarn-error.log*

# Base de Dados
*.sqlite3
*.db

# IDEs & OS
.vscode/
.idea/
.DS_Store
Thumbs.db
