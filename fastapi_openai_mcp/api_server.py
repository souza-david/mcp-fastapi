"""API server interacting with OpenAI and an MCP service."""

from typing import Any, Dict

import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")
MCP_SERVER_URL: str | None = os.getenv("MCP_SERVER_URL")

openai_client = openai.AsyncOpenAI()

# Model used for OpenAI function calling
OPENAI_MODEL = "gpt-4-turbo"

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
            "type": "function",
            "function": {
                "name": "get_server_time",
                "description": "Get the server time from the MCP service",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    response = await openai_client.responses.create(
        model=OPENAI_MODEL,
        input=req.message,
        tools=tools,
    )
    output = response["output"][0]
    if output.get("type") == "function_call":
        call = output
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MCP_SERVER_URL}/server_time",
                headers={"Authorization": f"Bearer {MCP_API_KEY}"},
            )
            resp.raise_for_status()
            tool_result = resp.json()
        followup = await openai_client.responses.create(
            model=OPENAI_MODEL,
            previous_response_id=response["id"],
            input=json.dumps(tool_result),
        )
        final_output = followup["output"][0]
        if final_output.get("type") == "message":
            final_message = final_output["content"][0]["text"]
        else:
            final_message = ""
    else:
        if output.get("type") == "message":
            final_message = output["content"][0]["text"]
        else:
            final_message = ""

    return {"answer": final_message}
