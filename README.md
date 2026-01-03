# MoneyMap 💰

O **MoneyMap** é uma aplicação de gestão financeira pessoal projetada para monitorizar o património líquido, investimentos e despesas. A solução combina um dashboard interativo no frontend com uma infraestrutura de dados robusta.

## 🏗️ Arquitetura do Projeto

O projeto segue uma arquitetura cliente-servidor:

*   **Frontend (`MoneyMap_Frontend`)**: Aplicação *Single Page Application* (SPA) construída com Next.js.
*   **Backend (`MoneyMap_Backend`)**: Infraestrutura de dados suportada por PostgreSQL e Docker.
*   **API**: O frontend comunica com uma API REST (a correr localmente na porta 8000).

## 🚀 Tecnologias Utilizadas

### Frontend
*   **Framework**: Next.js (React) com TypeScript.
*   **Estilos**: Tailwind CSS para design responsivo.
*   **Visualização de Dados**: Recharts para gráficos de área e circulares.
*   **Qualidade de Código**: ESLint e Axe-core para acessibilidade (a11y).

### Infraestrutura (Backend)
*   **Base de Dados**: PostgreSQL 15.
*   **Containerização**: Docker e Docker Compose.

## ⚙️ Configuração e Instalação

### Pré-requisitos
*   Node.js (v18+)
*   Docker e Docker Compose

### 1. Configurar a Base de Dados
A base de dados é gerida via Docker. É necessário configurar as variáveis de ambiente antes de iniciar.

1.  Navegue até à pasta do docker:
    ```bash
    cd MoneyMap_Backend/docker
    ```
2.  Crie um ficheiro `.env` com as credenciais (se ainda não existir):
    ```env
    POSTGRES_USER=admin
    POSTGRES_PASSWORD=segredo
    POSTGRES_DB=moneymap_db
    ```
3.  Inicie o serviço:
    ```bash
    docker-compose up -d
    ```

### 2. Iniciar o Frontend

1.  Navegue até à pasta do frontend:
    ```bash
    cd MoneyMap_Frontend
    ```
2.  Instale as dependências:
    ```bash
    npm install
    ```
3.  Inicie o servidor de desenvolvimento:
    ```bash
    npm run dev
    ```
4.  Aceda a `http://localhost:3000` no seu browser.

## 📊 Funcionalidades do Dashboard

O painel principal (`src/app/page.tsx`) oferece:

1.  **Resumo Financeiro**: Património Total, Liquidez e Total Investido.
2.  **Visualização Gráfica**: Evolução Patrimonial (30 dias), Despesas e Alocação de Portfólio.
3.  **Gestão de Ativos**: Tabela detalhada com cálculo automático de Lucro/Prejuízo.

## 🔌 Integração com API

O frontend consome endpoints em `http://127.0.0.1:8000` (`/portfolio`, `/history`, `/analytics/spending`).

**Autenticação**: As requisições utilizam um token `Bearer` armazenado no `localStorage`.