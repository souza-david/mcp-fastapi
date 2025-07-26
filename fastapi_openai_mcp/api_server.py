"""API server interacting with OpenAI and an MCP service."""

from typing import Any, Dict, List, Optional

import os
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai
import httpx

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
MCP_API_KEY: str | None = os.getenv("MCP_API_KEY")
MCP_SERVER_URL: str | None = os.getenv("MCP_SERVER_URL")

openai_client = openai.AsyncOpenAI()

# Model used for OpenAI tool calling
OPENAI_MODEL = "gpt-4.1"

app = FastAPI()

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
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

async def call_mcp_server() -> str:
    """Call the MCP server to get the current time."""
    if not MCP_SERVER_URL or not MCP_API_KEY:
        raise ValueError("MCP configuration missing")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MCP_SERVER_URL}/server_time",
            headers={"Authorization": f"Bearer {MCP_API_KEY}"}
        )
        response.raise_for_status()
        data = response.json()
        return data["server_time"]

@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, str]:
    """Handle a chat request, delegating to OpenAI and the MCP service."""

    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    if not MCP_API_KEY or not MCP_SERVER_URL:
        raise HTTPException(status_code=500, detail="MCP configuration missing")

    # First API call: Ask the model with tool definitions
    messages = [
        {"role": "system", "content": "You are a helpful assistant. When asked about the current time or server time, you MUST use the get_server_time tool to get the accurate time from the MCP server. When you receive the time from the MCP server, include the '[MCP Server Time]' prefix in your response to show that the time came from the MCP server."},
        {"role": "user", "content": req.message}
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
                    function_response = f"Error calling MCP server: {str(e)}"
                
                # Add the function response to the conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })
        
        # Get the final response from the model
        second_response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )
        
        final_message = second_response.choices[0].message.content
    else:
        # No tool call was made
        final_message = response_message.content

    return {"answer": final_message}