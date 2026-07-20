FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install fastmcp requests

COPY utils /app/utils
COPY memory/memory_mcp ./memory_mcp
COPY memory/embedding ./embedding
COPY memory/vector_store.py ./vector_store.py
COPY memory/graph ./graph

RUN mkdir -p /app/data && chown 1000:1000 /app/data

ENV DB_PATH=/app/data/memory.db
ENV PYTHONPATH="/app"

EXPOSE 8081

CMD ["python", "-m", "memory_mcp.server"]
