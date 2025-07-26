"""Minimal MCP server exposing the current time."""

from datetime import datetime, timezone
import os
from typing import Dict

from fastapi import FastAPI, Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")

@app.get("/server_time")
async def get_server_time(authorization: str | None = Header(None)) -> Dict[str, str]:
    """Return the current server time if the bearer token matches."""

    if not MCP_API_KEY:
        raise RuntimeError("MCP_API_KEY not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    token = authorization.split(" ", 1)[1]
    if token != MCP_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    now = datetime.now(timezone.utc).isoformat()
    return {"server_time": f"[MCP Server Time] {now}"}
