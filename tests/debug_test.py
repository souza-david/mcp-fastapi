#!/usr/bin/env python3
"""Test OpenAI tool calling functionality."""

import pytest
from dotenv import load_dotenv
import openai
import os

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_openai_tool_calling():
    """Test that OpenAI correctly identifies when to call the get_server_time tool."""
    
    # Ensure we have an API key - fail if not
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY must be set in .env file"
    assert api_key.startswith("sk-"), f"Invalid OpenAI API key format: {api_key[:10]}..."
    
    client = openai.AsyncOpenAI()
    
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
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. When asked about the current time or server time, you MUST use the get_server_time tool to get the accurate time from the MCP server."},
        {"role": "user", "content": "What is the current server time?"}
    ]
    
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
        tool_choice="required"
    )
    
    # Assertions to verify the tool calling works correctly
    assert response.choices[0].message.tool_calls is not None, "No tool calls were made"
    assert len(response.choices[0].message.tool_calls) == 1, "Expected exactly one tool call"
    assert response.choices[0].message.tool_calls[0].function.name == "get_server_time", "Wrong function called"
    assert response.choices[0].message.content is None, "Expected no content when tool_choice is required"