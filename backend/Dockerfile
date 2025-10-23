FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema (para nc no start.sh)
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./start.sh .
RUN chmod +x ./start.sh

# Copia a aplicação
COPY ./app /app/app

# Expõe a porta
EXPOSE 8000

# O CMD agora chama o script de inicialização
CMD ["/app/start.sh"]