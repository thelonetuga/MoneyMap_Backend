# 💰 MoneyMap - Gestor Financeiro Pessoal

O **MoneyMap** é uma aplicação Full-Stack moderna para gestão de património. Permite monitorizar contas bancárias, despesas e investimentos (Ações, ETFs, Crypto) num único dashboard, com atualizações de lucros e perdas (P&L) em tempo real.

## 🚀 Tecnologias Utilizadas

### Backend (API & Lógica)
* **Python 3.10+**
* **FastAPI:** Framework de alta performance para a API.
* **SQLAlchemy 2.0:** ORM para interação com a base de dados.
* **Pydantic:** Validação de dados e schemas.

### Frontend (Interface)
* **Next.js 14/15:** Framework React com TypeScript.
* **Tailwind CSS:** Estilização moderna e responsiva.
* **Recharts:** Visualização de dados (Gráficos de alocação).

### Base de Dados & Infraestrutura
* **PostgreSQL:** Base de dados relacional.
* **Docker:** Contentorização da base de dados.

---

## ⚙️ Pré-requisitos

Antes de começar, certifique-se de que tem instalado:
* [Docker Desktop](https://www.docker.com/) (ou Docker Engine)
* [Python 3.10+](https://www.python.org/)
* [Node.js 20+](https://nodejs.org/) (Recomendado usar via NVM)

---

## 🛠️ Instalação e Configuração

Siga estes passos para colocar o projeto a funcionar localmente.

### 1. Base de Dados (Docker)
Inicie o contentor do PostgreSQL:
```bash
docker-compose up -d
