# MoneyMap - Backend API 🚀

Backend robusto para gestão financeira pessoal, construído com **FastAPI**, **PostgreSQL** e **Docker**.

## 🛠️ Tecnologias

*   **Framework**: FastAPI (Python 3.11)
*   **Base de Dados**: PostgreSQL 15
*   **ORM**: SQLAlchemy
*   **Migrações**: Alembic
*   **Infraestrutura**: Docker & Docker Compose
*   **Testes**: Pytest

## 🚀 Como Iniciar (Produção / Docker)

A forma mais fácil de correr o projeto completo (API + Base de Dados):

1.  **Configurar Ambiente:**
    ```bash
    cp .env.example .env
    # Edite o .env com as suas credenciais se necessário
    ```

2.  **Arrancar Serviços:**
    ```bash
    docker compose up -d --build
    ```

A API ficará disponível em: `http://localhost:8000`
Documentação Interativa (Swagger): `http://localhost:8000/docs`

## 💻 Desenvolvimento Local

Se preferir correr o Python localmente:

1.  **Instalar Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Arrancar Base de Dados (via Docker):**
    ```bash
    docker compose up -d db
    ```

3.  **Aplicar Migrações:**
    ```bash
    alembic upgrade head
    ```

4.  **Popular com Dados de Teste (Seed):**
    ```bash
    python -m app.seed
    ```

5.  **Correr Servidor:**
    ```bash
    uvicorn app.main:app --reload
    ```

## 🧪 Testes

Para garantir a estabilidade e segurança:

```bash
pytest
```

## 📂 Estrutura do Projeto

*   `app/`: Código fonte da API.
    *   `routers/`: Endpoints organizados por domínio (Auth, Accounts, Analytics...).
    *   `models/`: Tabelas da Base de Dados.
    *   `schemas/`: Validação de dados (Pydantic).
*   `alembic/`: Scripts de migração de base de dados.
*   `tests/`: Testes unitários e de integração.

## 📊 Funcionalidades Principais

*   **Autenticação JWT**: Registo e Login seguro.
*   **Gestão de Contas**: Bancárias, Investimento e Crypto.
*   **Transações**: Receitas e Despesas categorizadas.
*   **Analytics**:
    *   Gráficos de Despesas por Categoria.
    *   Evolução Patrimonial (Net Worth vs Liquidez).
    *   Sincronização em tempo real (Live Sync).
*   **Portfolio**: Integração com dados de mercado para valorização de ativos.

---
Desenvolvido com ❤️ para o MoneyMap.