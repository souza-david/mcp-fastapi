#!/usr/bin/env python3
"""Integration tests to verify the MCP integration with real OpenAI API."""

import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_mcp_server_integration():
    """Test the MCP server directly (requires running server)."""
    
    # Get required configuration - fail if not available
    mcp_api_key = os.getenv("MCP_API_KEY")
    mcp_server_url = os.getenv("MCP_SERVER_URL")
    
    assert mcp_api_key is not None, "MCP_API_KEY must be set in .env file"
    assert mcp_server_url is not None, "MCP_SERVER_URL must be set in .env file"
    
    async with httpx.AsyncClient() as client:
        # Test without auth - should fail
        try:
            resp = await client.get(f"{mcp_server_url}/server_time")
            assert resp.status_code == 401, f"Expected 401 for unauthorized request, got {resp.status_code}"
        except httpx.HTTPStatusError as e:
            assert e.response.status_code == 401, "Should return 401 for unauthorized access"
        
        # Test with auth - should succeed (will fail if server not running)
        headers = {"Authorization": f"Bearer {mcp_api_key}"}
        resp = await client.get(f"{mcp_server_url}/server_time", headers=headers)
        assert resp.status_code == 200, f"MCP server failed with {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "server_time" in data, "Response should contain 'server_time' field"
        assert "[MCP Server Time]" in data["server_time"], "Should have MCP identifier"
        
        # Verify it's a valid timestamp (basic check)
        time_str = data["server_time"]
        assert "T" in time_str and ":" in time_str, f"Should be ISO format timestamp: {time_str}"

@pytest.mark.asyncio
async def test_api_server_integration():
    """Test the API server with real OpenAI integration (requires running servers and API key)."""
    
    # Check for required environment variables - fail if not available
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY must be set in .env file"
    assert openai_api_key.startswith("sk-"), f"Invalid OpenAI API key format: {openai_api_key[:10]}..."
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test with time-related query - should trigger MCP
        response = await client.post(
            "http://localhost:8000/chat",
            json={"message": "What is the current server time?"}
        )
        assert response.status_code == 200, f"API server failed with {response.status_code}: {response.text}"
        
        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        answer = data["answer"]
        assert "[MCP Server Time]" in answer, f"Answer should contain MCP time identifier. Got: {answer}"
        
        # Test with non-time query - should not trigger MCP
        response = await client.post(
            "http://localhost:8000/chat", 
            json={"message": "Tell me a joke"}
        )
        assert response.status_code == 200, f"API server failed with {response.status_code}: {response.text}"
        
        data = response.json()
        assert "answer" in data, "Response should contain 'answer' field"
        # This should not contain MCP time identifier
        answer = data["answer"]
        assert isinstance(answer, str), "Answer should be a string"