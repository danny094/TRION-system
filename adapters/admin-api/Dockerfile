FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY adapters/admin-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code from project root
COPY core /app/core
COPY utils /app/utils
COPY mcp /app/mcp
COPY tools /app/tools
COPY config /app/config
COPY intelligence_modules /app/intelligence_modules
COPY plugins /app/plugins
COPY personas /app/persona_defaults
COPY memory/memory_mcp/tool_intents.json /app/memory/memory_mcp/tool_intents.json

# Copy application last
COPY adapters/*.py /app/adapters/
COPY adapters/admin-api/commander_api /app/commander_api
COPY adapters/admin-api/docker-entrypoint.sh /usr/local/bin/trion-admin-api-entrypoint
COPY adapters/admin-api/*.py ./

ENV PYTHONPATH="/app"

RUN mkdir -p /app/data \
    && chmod +x /usr/local/bin/trion-admin-api-entrypoint

EXPOSE 8200

ENTRYPOINT ["trion-admin-api-entrypoint"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200", "--log-level", "info"]
