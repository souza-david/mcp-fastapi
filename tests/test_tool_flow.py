#!/usr/bin/env python3
"""Test the complete tool flow with logging."""

import pytest
import os
from dotenv import load_dotenv
from fastapi_openai_mcp import api_server
import httpx

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_tool_flow():
    """Test the complete flow with inline execution (requires OpenAI API key and MCP server)."""
    
    # Ensure we have required environment variables - fail if not
    openai_api_key = os.getenv("OPENAI_API_KEY")
    mcp_api_key = os.getenv("MCP_API_KEY")
    mcp_server_url = os.getenv("MCP_SERVER_URL")
    
    assert openai_api_key is not None, "OPENAI_API_KEY must be set in .env file"
    assert openai_api_key.startswith("sk-"), f"Invalid OpenAI API key format: {openai_api_key[:10]}..."
    assert mcp_api_key is not None, "MCP_API_KEY must be set in .env file"
    assert mcp_server_url is not None, "MCP_SERVER_URL must be set in .env file"
    
    # Create a chat request
    req = api_server.ChatRequest(message="What is the current server time?")
    
    # Call the chat endpoint directly - this will fail if OpenAI API key is invalid
    result = await api_server.chat(req)
    
    # Assertions
    assert "answer" in result, "Result should contain 'answer' field"
    assert isinstance(result["answer"], str), "Answer should be a string"
    
    # Also test the MCP server directly if it's running
    async with httpx.AsyncClient() as client:
        mcp_resp = await client.get(
            f"{mcp_server_url}/server_time",
            headers={"Authorization": f"Bearer {mcp_api_key}"}
        )
        assert mcp_resp.status_code == 200, f"MCP server returned {mcp_resp.status_code}: {mcp_resp.text}"
        mcp_data = mcp_resp.json()
        assert "server_time" in mcp_data, "MCP response should contain 'server_time'"
        assert "[MCP Server Time]" in mcp_data["server_time"], "Response should have MCP identifier"