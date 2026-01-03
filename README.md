# MoneyMap - Backend & Infraestrutura 🗄️

Este diretório contém a infraestrutura de backend do projeto **MoneyMap**, focada na persistência de dados utilizando PostgreSQL e Docker.

## 📂 Estrutura

*   `docker/`: Configurações de containerização e orquestração.
    *   `docker-compose.yml`: Definição do serviço de base de dados PostgreSQL.
    *   `.env`: Variáveis de ambiente (credenciais).

## 🛠️ Tecnologias

*   **Base de Dados**: PostgreSQL 15
*   **Infraestrutura**: Docker & Docker Compose

## 🚀 Como Iniciar a Infraestrutura

Para arrancar com a base de dados localmente:

1.  **Navegue para a pasta docker:**
    ```bash
    cd docker
    ```

2.  **Configure as variáveis de ambiente:**
    Crie um ficheiro `.env` nesta pasta (se ainda não existir) com o seguinte conteúdo:
    ```env
    POSTGRES_USER=admin
    POSTGRES_PASSWORD=segredo
    POSTGRES_DB=moneymap_db
    ```

3.  **Inicie o serviço:**
    ```bash
    docker-compose up -d
    ```

## 🔌 Detalhes de Conexão

Uma vez iniciado, o PostgreSQL estará acessível em:

*   **Host**: `localhost`
*   **Porta**: `5432`
*   **Username**: `admin` (ou o definido no .env)
*   **Password**: `segredo` (ou o definido no .env)
*   **Database**: `moneymap_db`