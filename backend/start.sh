#!/bin/sh
# Este script espera o banco de dados estar pronto e depois inicia a aplicação.

# Espera o PostgreSQL ficar disponível
echo "Esperando PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL iniciado."

# Roda o script para popular o banco de dados
echo "Populando o banco de dados..."
python -m app.seed

# Inicia a aplicação FastAPI
echo "Iniciando servidor FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
