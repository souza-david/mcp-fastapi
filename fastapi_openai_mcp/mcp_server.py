"""Minimal MCP server exposing the current time."""

from datetime import datetime, timezone
import os
import logging
from typing import Dict

from fastapi import FastAPI, Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("fastapi_openai_mcp.mcp_server")

app = FastAPI()

MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")

@app.on_event("startup")
async def _on_startup() -> None:
    logger.info(
        "MCP server startup: MCP_API_KEY set=%s",
        bool(MCP_API_KEY),
    )


@app.get("/server_time")
async def get_server_time(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> Dict[str, str]:
    """Return the current server time if a valid token is provided.

    Accepts either `Authorization: Bearer <token>` or `X-Api-Key: <token>`.
    """

    if not MCP_API_KEY:
        logger.error("MCP_API_KEY not configured")
        raise RuntimeError("MCP_API_KEY not configured")

    token_source = None
    token_value = None

    if x_api_key:
        token_source = "x-api-key"
        token_value = x_api_key
    elif authorization and authorization.startswith("Bearer "):
        token_source = "authorization"
        token_value = authorization.split(" ", 1)[1]

    if not token_value:
        logger.warning("Unauthorized request: missing token header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if token_value != MCP_API_KEY:
        logger.warning("Unauthorized request: invalid token (source=%s)", token_source)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    now = datetime.now(timezone.utc).isoformat()
    logger.info("Authorized request succeeded (source=%s)", token_source)
    return {"server_time": f"[MCP Server Time] {now}"}
