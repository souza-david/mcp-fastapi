FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=info

WORKDIR /app

COPY pyproject.toml .
COPY fastapi_openai_mcp ./fastapi_openai_mcp
RUN pip install --no-cache-dir .

COPY . .

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000 8001

# SERVICE can be 'api' or 'mcp'; default to 'api'
ENV SERVICE=api

ENTRYPOINT ["/entrypoint.sh"]
