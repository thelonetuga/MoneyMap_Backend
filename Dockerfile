FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema necessárias (opcional, mas recomendado para psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# Executa o servidor uvicorn na porta 8000 (sem reload para produção)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]