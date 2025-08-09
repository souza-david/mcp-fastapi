"""API server interacting with OpenAI and an MCP service."""

import json
import os
import logging
from typing import Dict

import httpx
import openai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")
MCP_SERVER_URL: str | None = os.getenv("MCP_SERVER_URL")

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("fastapi_openai_mcp.api_server")

openai_client = openai.AsyncOpenAI()

# Model used for OpenAI tool calling
OPENAI_MODEL = "gpt-4.1"

app = FastAPI()

@app.on_event("startup")
async def _on_startup() -> None:
    logger.info(
        "API server startup: OPENAI_API_KEY set=%s, MCP_API_KEY set=%s, MCP_SERVER_URL=%s",
        bool(openai.api_key),
        bool(MCP_API_KEY),
        MCP_SERVER_URL,
    )


class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str


# Define the function/tool for OpenAI to use
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_server_time",
            "description": "Get the current server time from the MCP server",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }
]


async def call_mcp_server() -> str:
    """Call the MCP server to get the current time."""
    if not MCP_SERVER_URL or not MCP_API_KEY:
        raise ValueError("MCP configuration missing")

    url = f"{MCP_SERVER_URL}/server_time"
    headers = {
        # Send both headers to be compatible with Cloud Run (Authorization may be reserved)
        "Authorization": f"Bearer {MCP_API_KEY}",
        "X-Api-Key": MCP_API_KEY,
    }
    logger.debug("Calling MCP server", extra={"url": url})
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            logger.info(
                "MCP server responded", extra={"status_code": response.status_code}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as http_err:
            logger.error(
                "MCP server HTTP error",
                extra={
                    "status_code": getattr(http_err.response, "status_code", None),
                    "text": getattr(http_err.response, "text", None),
                },
            )
            raise
        data = response.json()
        return data["server_time"]


@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, str]:
    """Handle a chat request, delegating to OpenAI and the MCP service."""

    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    if not MCP_API_KEY or not MCP_SERVER_URL:
        raise HTTPException(status_code=500, detail="MCP configuration missing")

    logger.info(
        "Handling chat request", extra={"message_preview": req.message[:80]}
    )

    # First API call: Ask the model with tool definitions
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. When asked about the current time or server time, you MUST use the get_server_time tool to get the accurate time from the MCP server. When you receive the time from the MCP server, include the '[MCP Server Time]' prefix in your response to show that the time came from the MCP server.",
        },
        {"role": "user", "content": req.message},
    ]

    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # If the model wants to use a tool
    if tool_calls:
        logger.info("Model requested tool calls", extra={"num_calls": len(tool_calls)})
        # Add the assistant's response to the conversation
        assistant_msg = response_message.model_dump()
        messages.append(assistant_msg)

        # Process each tool call
        for tool_call in tool_calls:
            function_name = tool_call.function.name

            if function_name == "get_server_time":
                # Call the MCP server
                try:
                    server_time = await call_mcp_server()
                    function_response = server_time
                except Exception as e:
                    logger.exception("Error calling MCP server")
                    function_response = f"Error calling MCP server: {str(e)}"

                # Add the function response to the conversation
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

        # Get the final response from the model
        second_response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )

        final_message = second_response.choices[0].message.content
    else:
        # No tool call was made
        logger.info("Model did not request any tool calls")
        final_message = response_message.content

    return {"answer": final_message}
