#!/bin/sh

# Parar o script se houver algum erro
set -e

echo "🚀 A iniciar MoneyMap Backend..."

# 1. Correr Migrações da Base de Dados
echo "🔄 A verificar e aplicar migrações de base de dados..."
alembic upgrade head

# 2. Iniciar a Aplicação
echo "✅ Base de dados pronta. A iniciar servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000