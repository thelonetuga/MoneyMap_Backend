FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY ./app ./app

# Copiar ficheiros de migração (Alembic)
COPY ./alembic ./alembic
COPY alembic.ini .

# Copiar script de entrada
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Usar o script como ponto de entrada
ENTRYPOINT ["./entrypoint.sh"]