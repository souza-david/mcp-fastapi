import os
import json
import httpx
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MCP_API_KEY", "testkey")
os.environ.setdefault("MCP_SERVER_URL", "http://mcp")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from fastapi_openai_mcp.mcp_server import app as mcp_app, MCP_API_KEY
from fastapi_openai_mcp import api_server


def test_mcp_auth() -> None:
    client: TestClient = TestClient(mcp_app)
    r = client.get("/server_time")
    assert r.status_code == 401
    r = client.get("/server_time", headers={"Authorization": f"Bearer {MCP_API_KEY}"})
    assert r.status_code == 200
    assert "server_time" in r.json()

def test_chat_tool_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    async def fake_create(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        if "previous_response_id" not in kwargs:
            return {
                "id": "resp1",
                "output": [
                    {
                        "type": "function_call",
                        "name": "get_server_time",
                        "call_id": "1",
                        "arguments": "{}",
                    }
                ],
            }
        else:
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "The time is 2024-01-01T00:00:00Z"}],
                    }
                ]
            }

    monkeypatch.setattr(api_server.openai_client.responses, "create", fake_create)

    class Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, str]:
            return {"server_time": "2024-01-01T00:00:00Z"}

    async def fake_get(self: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None) -> Resp:
        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "what time"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "The time is 2024-01-01T00:00:00Z"
    assert len(calls) == 2

def test_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end test with the MCP server running locally."""
    from fastapi_openai_mcp import mcp_server

    async def fake_create(*args: object, **kwargs: object) -> dict[str, object]:
        if "previous_response_id" not in kwargs:
            return {
                "id": "resp1",
                "output": [
                    {
                        "type": "function_call",
                        "name": "get_server_time",
                        "call_id": "1",
                        "arguments": "{}",
                    }
                ],
            }
        else:
            tool_data = json.loads(kwargs["input"])
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": f"The time is {tool_data['server_time']}"}
                        ],
                    }
                ],
            }

    monkeypatch.setattr(api_server.openai_client.responses, "create", fake_create)

    mcp_client: TestClient = TestClient(mcp_server.app)

    async def local_get(self: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        return mcp_client.get(url.replace("http://mcp", ""), headers=headers)

    monkeypatch.setattr(httpx.AsyncClient, "get", local_get)

    with TestClient(api_server.app) as client:
        resp = client.post("/chat", json={"message": "time"})
    assert resp.status_code == 200
    assert "The time is" in resp.json()["answer"]
