# FastAPI OpenAI MCP Sample

This repository provides a minimal example of two FastAPI services working together with an OpenAI MCP tool‑calling agent.

* `fastapi_openai_mcp/mcp_server.py` – a protected MCP server exposing `/server_time`.
* `fastapi_openai_mcp/api_server.py` – an API server that calls OpenAI's **Responses API** which in turn invokes the MCP server via the tools feature.

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies with [uv](https://github.com/astral-sh/uv):
   ```bash
   uv pip install -e .[dev]
   ```
3. Copy `.env.example` to `.env` and fill in values for `MCP_API_KEY`, `MCP_SERVER_URL`, and `OPENAI_API_KEY`.

## Running the servers

Start the MCP server on port 8001:
```bash
uvicorn fastapi_openai_mcp.mcp_server:app --port 8001
```

In another terminal, start the API server on port 8000:
```bash
uvicorn fastapi_openai_mcp.api_server:app --port 8000
```
The API server uses OpenAI's `openai-4.1` model with MCP tool calling enabled via the **Responses API**.

## Using the API

Send a chat request via `curl`:
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What time is it?"}'
```

## Running tests

Install development dependencies as in the setup section and then run:
```bash
coverage run -m pytest
coverage report
```
The included unit and integration tests provide over 90% coverage.
