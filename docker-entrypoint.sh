#!/bin/sh
set -e

log() {
  echo "[entrypoint] $1"
}

# If the user passes a command, run it
if [ "$#" -gt 0 ]; then
  log "Executing custom command: $*"
  exec "$@"
fi

SERVICE="${SERVICE:-api}"
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_LEVEL_LC=$(printf "%s" "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')

case "$SERVICE" in
  api)
    PORT="${PORT:-8000}"
    log "Starting API server on 0.0.0.0:${PORT} (LOG_LEVEL=${LOG_LEVEL_LC})"
    if [ -n "$MCP_SERVER_URL" ]; then log "MCP_SERVER_URL set"; else log "MCP_SERVER_URL NOT set"; fi
    if [ -n "$MCP_API_KEY" ]; then log "MCP_API_KEY set"; else log "MCP_API_KEY NOT set"; fi
    if [ -n "$OPENAI_API_KEY" ]; then log "OPENAI_API_KEY set"; else log "OPENAI_API_KEY NOT set"; fi
    exec uvicorn fastapi_openai_mcp.api_server:app --host 0.0.0.0 --port "${PORT}" --log-level "${LOG_LEVEL_LC}"
    ;;
  mcp)
    PORT="${PORT:-8001}"
    log "Starting MCP server on 0.0.0.0:${PORT} (LOG_LEVEL=${LOG_LEVEL_LC})"
    if [ -n "$MCP_API_KEY" ]; then log "MCP_API_KEY set"; else log "MCP_API_KEY NOT set"; fi
    exec uvicorn fastapi_openai_mcp.mcp_server:app --host 0.0.0.0 --port "${PORT}" --log-level "${LOG_LEVEL_LC}"
    ;;
  *)
    log "Unknown SERVICE='${SERVICE}'. Expected 'api' or 'mcp'."
    exit 1
    ;;
esac


