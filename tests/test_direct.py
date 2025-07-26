#!/usr/bin/env python3
"""Direct test of the API endpoints when servers are running."""

import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_mcp_direct():
    """Test MCP server directly (requires running server)."""
    
    # Get MCP configuration
    mcp_api_key = os.getenv("MCP_API_KEY")
    mcp_server_url = os.getenv("MCP_SERVER_URL")
    
    assert mcp_api_key is not None, "MCP_API_KEY must be set in .env file"
    assert mcp_server_url is not None, "MCP_SERVER_URL must be set in .env file"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{mcp_server_url}/server_time",
            headers={"Authorization": f"Bearer {mcp_api_key}"}
        )
        
        # Assertions - will fail if server isn't running
        assert response.status_code == 200, f"MCP server request failed with {response.status_code}: {response.text}"
        data = response.json()
        assert "server_time" in data, "Response should contain 'server_time' field"
        assert "[MCP Server Time]" in data["server_time"], "Response should have MCP identifier"

@pytest.mark.asyncio
async def test_api_with_logging():
    """Test API server (requires running server and OpenAI API key)."""
    
    # Check for required environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY must be set in .env file"
    assert openai_api_key.startswith("sk-"), f"Invalid OpenAI API key format: {openai_api_key[:10]}..."
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/chat",
            json={"message": "What is the current server time?"}
        )
        
        # Assertions - will fail if API server isn't running or configured properly
        assert response.status_code == 200, f"API server request failed with {response.status_code}: {response.text}"
        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        assert isinstance(data["answer"], str), "Answer should be a string"