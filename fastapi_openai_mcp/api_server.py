"""API server interacting with OpenAI and an MCP service."""

from typing import Any, Dict, List

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")
MCP_SERVER_URL: str | None = os.getenv("MCP_SERVER_URL")

openai_client = openai.AsyncOpenAI()

# Model used for OpenAI tool calling
OPENAI_MODEL = "openai-4.1"

app = FastAPI()

class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str

@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, str]:
    """Handle a chat request, delegating to OpenAI and the MCP service."""

    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    if not MCP_API_KEY or not MCP_SERVER_URL:
        raise HTTPException(status_code=500, detail="MCP configuration missing")

    tools: List[Dict[str, Any]] = [
        {
            "type": "mcp",
            "server_label": "local_mcp",
            "server_url": MCP_SERVER_URL,
            "headers": {"Authorization": f"Bearer {MCP_API_KEY}"},
            "allowed_tools": ["get_server_time"],
        }
    ]

    response = await openai_client.responses.create(
        model=OPENAI_MODEL,
        input=req.message,
        tools=tools,
    )

    output = response["output"][0]
    if output.get("type") == "message":
        final_message = output["content"][0]["text"]
    else:
        final_message = ""

    return {"answer": final_message}
