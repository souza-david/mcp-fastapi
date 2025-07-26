import os
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MCP_API_KEY", "testkey")
os.environ.setdefault("MCP_SERVER_URL", "http://mcp")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from fastapi_openai_mcp.mcp_server import app as mcp_app, MCP_API_KEY
from fastapi_openai_mcp import api_server


def test_mcp_auth() -> None:
    """Test MCP server authentication."""
    client: TestClient = TestClient(mcp_app)
    r = client.get("/server_time")
    assert r.status_code == 401
    r = client.get("/server_time", headers={"Authorization": f"Bearer {MCP_API_KEY}"})
    assert r.status_code == 200
    data = r.json()
    assert "server_time" in data
    assert "[MCP Server Time]" in data["server_time"]

def test_chat_tool_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat endpoint with mocked OpenAI responses."""
    calls: List[Dict[str, Any]] = []

    # Mock tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "get_server_time"
    mock_tool_call.function.arguments = "{}"

    # Mock message with tool calls
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = None
    mock_message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_server_time",
                "arguments": "{}"
            }
        }]
    }

    # Mock second message without tool calls
    mock_final_message = MagicMock()
    mock_final_message.content = "The current time from the MCP server is [MCP Server Time] 2024-01-01T00:00:00Z"

    # Mock choice objects
    mock_choice1 = MagicMock()
    mock_choice1.message = mock_message
    
    mock_choice2 = MagicMock()
    mock_choice2.message = mock_final_message

    # Mock response objects
    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]
    
    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]

    async def fake_create(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        if len(calls) == 1:
            return mock_response1
        else:
            return mock_response2

    # Mock the MCP server call
    async def fake_call_mcp() -> str:
        return "[MCP Server Time] 2024-01-01T00:00:00Z"

    monkeypatch.setattr(api_server.openai_client.chat.completions, "create", fake_create)
    monkeypatch.setattr(api_server, "call_mcp_server", fake_call_mcp)

    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "what time is it?"})
    
    assert resp.status_code == 200
    answer = resp.json()["answer"]
    assert "[MCP Server Time]" in answer
    assert len(calls) == 2  # Two OpenAI API calls
    assert calls[0]["tools"][0]["type"] == "function"
    assert calls[0]["tools"][0]["function"]["name"] == "get_server_time"

def test_chat_without_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat endpoint when model doesn't use tool."""
    calls: List[Dict[str, Any]] = []

    # Mock message without tool calls
    mock_message = MagicMock()
    mock_message.tool_calls = None
    mock_message.content = "I don't need to check the server time for this."

    # Mock choice object
    mock_choice = MagicMock()
    mock_choice.message = mock_message

    # Mock response object
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    async def fake_create(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return mock_response

    monkeypatch.setattr(api_server.openai_client.chat.completions, "create", fake_create)

    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "tell me a joke"})
    
    assert resp.status_code == 200
    answer = resp.json()["answer"]
    assert answer == "I don't need to check the server time for this."
    assert len(calls) == 1  # Only one OpenAI API call

def test_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end test with the MCP server running locally."""
    from fastapi_openai_mcp import mcp_server
    
    # Mock tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_456"
    mock_tool_call.function.name = "get_server_time"
    mock_tool_call.function.arguments = "{}"

    # Mock message with tool calls
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = None
    mock_message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_456",
            "type": "function",
            "function": {
                "name": "get_server_time",
                "arguments": "{}"
            }
        }]
    }

    # We'll capture the actual MCP response
    actual_time: Optional[str] = None

    async def fake_create(*args: Any, **kwargs: Any) -> Any:
        nonlocal actual_time
        messages = kwargs.get("messages", [])
        
        # First call - return tool request (2 messages: system + user)
        if len(messages) == 2:
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response
        else:
            # Second call - we should have the tool response
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "tool":
                    actual_time = msg.get("content", "")
            
            mock_final_message = MagicMock()
            mock_final_message.content = f"The server time is: {actual_time}"
            mock_choice = MagicMock()
            mock_choice.message = mock_final_message
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response

    # Mock the MCP server call to use actual MCP server logic
    async def fake_call_mcp() -> str:
        # Simulate calling the actual MCP endpoint
        with TestClient(mcp_server.app) as mcp_client:
            resp = mcp_client.get("/server_time", headers={"Authorization": f"Bearer {MCP_API_KEY}"})
            return resp.json()["server_time"]

    monkeypatch.setattr(api_server.openai_client.chat.completions, "create", fake_create)
    monkeypatch.setattr(api_server, "call_mcp_server", fake_call_mcp)

    # Use real MCP client
    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "what time is it?"})
    
    assert resp.status_code == 200
    answer = resp.json()["answer"]
    assert "[MCP Server Time]" in answer
    assert actual_time is not None
    assert "[MCP Server Time]" in actual_time

def test_mcp_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of MCP server errors."""
    # Mock tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_789"
    mock_tool_call.function.name = "get_server_time"

    # Mock message with tool calls
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_789",
            "type": "function",
            "function": {
                "name": "get_server_time",
                "arguments": "{}"
            }
        }]
    }

    # Mock error response for MCP call
    async def fake_call_mcp() -> str:
        raise Exception("MCP server is down")

    # Track the error message passed to OpenAI
    error_message: Optional[str] = None

    async def fake_create(*args: Any, **kwargs: Any) -> Any:
        nonlocal error_message
        messages = kwargs.get("messages", [])
        
        if len(messages) == 2:  # system + user
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response
        else:
            # Capture the error message
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "tool":
                    error_message = msg.get("content", "")
            
            mock_final_message = MagicMock()
            mock_final_message.content = "I couldn't get the server time due to an error."
            mock_choice = MagicMock()
            mock_choice.message = mock_final_message
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response

    monkeypatch.setattr(api_server.openai_client.chat.completions, "create", fake_create)
    monkeypatch.setattr(api_server, "call_mcp_server", fake_call_mcp)

    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "what time?"})
    
    assert resp.status_code == 200
    assert error_message is not None
    assert "Error calling MCP server" in error_message