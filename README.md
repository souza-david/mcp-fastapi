# FastAPI OpenAI MCP Sample

This repository provides a complete example of integrating a FastAPI MCP (Model Context Protocol) service with OpenAI's function calling API.

## Architecture

* `fastapi_openai_mcp/mcp_server.py` – A protected MCP server exposing `/server_time` endpoint that returns the current time with a unique identifier `[MCP Server Time]` to prove the response comes from the MCP server
* `fastapi_openai_mcp/api_server.py` – An API server that uses OpenAI's Chat Completions API with function calling to invoke the MCP server when needed

## Key Features

- **Proper OpenAI Integration**: Uses the official OpenAI SDK with function calling (tools)
- **MCP Verification**: The MCP server adds a `[MCP Server Time]` prefix to prove the time comes from MCP, not the model's internal knowledge
- **Bearer Token Authentication**: MCP server is protected with token-based auth
- **Comprehensive Tests**: 11 tests including unit tests, integration tests, and real E2E validation
- **Type Safety**: All functions are fully typed

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies with [uv](https://github.com/astral-sh/uv):
   ```bash
   uv pip install -e ".[dev]"
   ```
   
   Or with pip:
   ```bash
   pip install -e ".[dev]"
   ```

3. Create a `.env` file and configure:
   ```bash
   # Copy .env.example to .env and configure:
   # cp .env.example .env
   cat > .env <<'EOF'
   MCP_API_KEY=changeme
   MCP_SERVER_URL=http://localhost:8001
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=info
   EOF
   ```
   
   Required variables:
   - `MCP_API_KEY`: A secret key for MCP authentication (choose a strong value)
   - `MCP_SERVER_URL`: Base URL where the MCP server is reachable (default: `http://localhost:8001`)
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `LOG_LEVEL` (optional): `debug`, `info`, `warning`, `error` (default: `info`)

## Run with Docker (recommended quickstart)

This repo ships a single image capable of running either service via `SERVICE=api` or `SERVICE=mcp`.

1) Build the image:
```bash
docker build -t mcp-fastapi:dev .
```

2) Create a Docker network for the two containers:
```bash
docker network create mcpnet || true
```

3) Start the MCP server (reads secrets from `.env`):
```bash
docker run -d --name mcp-server --network mcpnet \
  --env-file .env -e SERVICE=mcp -e LOG_LEVEL=info \
  -p 8001:8001 mcp-fastapi:dev
```

4) Start the API server (also reads `.env`, but override `MCP_SERVER_URL` to the container name):

Important: If your `.env` has `MCP_SERVER_URL=http://localhost:8001`, that value is wrong from inside the container. Override it to `http://mcp-server:8001` so the API can reach the MCP container over the Docker network.
```bash
docker run -d --name api-server --network mcpnet \
  --env-file .env -e SERVICE=api -e LOG_LEVEL=info \
  -e MCP_SERVER_URL=http://mcp-server:8001 \
  -p 8000:8000 mcp-fastapi:dev
```

5) Verify logs (they show presence of secrets, never values):
```bash
docker logs mcp-server | tail -n +1
docker logs api-server | tail -n +1
```

6) Validate MCP auth behavior (401 without auth, OK with either header):
```bash
curl -i http://localhost:8001/server_time | head -n 1                # 401
curl -s -H "Authorization: Bearer ${MCP_API_KEY}" http://localhost:8001/server_time
curl -s -H "X-Api-Key: ${MCP_API_KEY}" http://localhost:8001/server_time
```

7) End-to-end chat (requires valid `OPENAI_API_KEY`):
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current server time?"}'
```
Response includes the `[MCP Server Time]` prefix proving the agent called the MCP.

## Running the Servers (local dev without Docker)

**Note**: Always activate the virtual environment before running servers.

Start the MCP server on port 8001:
```bash
source .venv/bin/activate
uvicorn fastapi_openai_mcp.mcp_server:app --port 8001
```

In another terminal, start the API server on port 8000:
```bash
source .venv/bin/activate
uvicorn fastapi_openai_mcp.api_server:app --port 8000
```

### Troubleshooting: Port Already in Use

If you get "address already in use" errors, check and kill existing processes:

```bash
# Check what's using the ports
lsof -i :8001
lsof -i :8000

# Kill processes by PID (replace XXXX with actual PID)
kill XXXX
```

## Using the API (for both Docker and local dev)

Send a chat request that requires server time:
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the current server time?"}'
```

The response will include `[MCP Server Time]` prefix, proving it came from the MCP server:
```json
{
  "answer": "[MCP Server Time] The current server time is 2025-07-26T13:57:32 (UTC)."
}
```

Test with a query that doesn't need time:
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me a joke"}'
```

This won't call the MCP server and won't include the `[MCP Server Time]` identifier.

## Testing

**Important**: Tests require proper `.env` configuration and will **fail** (not skip) when dependencies are missing.

Run unit tests (no external dependencies):
```bash
source .venv/bin/activate
pytest tests/test_api.py -v
```

Run all tests with servers and valid API key:
```bash
source .venv/bin/activate
pytest tests/ -v
```

## Integration Testing (local dev)

**Real end-to-end testing** with OpenAI API and running servers:

1. **Start both servers** (requires virtual environment):
   ```bash
   # Terminal 1: MCP Server
   source .venv/bin/activate
   uvicorn fastapi_openai_mcp.mcp_server:app --port 8001
   
   # Terminal 2: API Server  
   source .venv/bin/activate
   uvicorn fastapi_openai_mcp.api_server:app --port 8000
   ```

2. **Run integration tests**:
   ```bash
   # Terminal 3: Tests
   source .venv/bin/activate
   pytest tests/test_real_api.py tests/test_direct.py -v
   ```

3. **Test manual E2E**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the current server time?"}'
   ```

**Test behavior**:
- ✅ **Pass**: All dependencies available and configured properly
- ❌ **Fail**: Missing `.env` configuration, invalid API keys, or servers not running
- 🚫 **No skipping**: Tests fail with clear error messages, never skip

## How It Works

1. **User sends a message** to the `/chat` endpoint
2. **API server calls OpenAI** with the message and a `get_server_time` tool definition
3. **OpenAI decides** whether to use the tool based on the user's query
4. **If tool is called**, the API server invokes the MCP server's `/server_time` endpoint
5. **MCP server returns** the time with `[MCP Server Time]` prefix
6. **API server sends** the tool result back to OpenAI
7. **OpenAI generates** a final response incorporating the MCP data
8. **User receives** the final answer

## Project Structure

```
fastapi_openai_mcp/
├── __init__.py
├── api_server.py    # OpenAI integration with function calling
└── mcp_server.py    # MCP server with time endpoint

tests/
├── test_api.py      # Comprehensive unit test suite
├── test_real_api.py # Integration tests with real API calls
├── debug_test.py    # OpenAI tool calling functionality tests
├── test_direct.py   # Direct server endpoint tests
└── test_tool_flow.py # Complete tool flow tests

.env.example         # Environment variable template
pyproject.toml       # Project dependencies
```

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `httpx`: HTTP client for calling MCP server
- `python-dotenv`: Environment variable management
- `openai`: Official OpenAI SDK
- `pytest`, `pytest-asyncio`: Testing tools

## Cloud Run deployment notes

- The MCP server accepts either `Authorization: Bearer <token>` or `X-Api-Key: <token>`. Cloud Run may reserve or modify the `Authorization` header, so prefer calling with `X-Api-Key` from external clients. The API server in this repo sends both headers.
- Deploy two services from the same image:
  - MCP: set `SERVICE=mcp`, `MCP_API_KEY`, `LOG_LEVEL=info`.
  - API: set `SERVICE=api`, `OPENAI_API_KEY`, `MCP_API_KEY` (same value as MCP), and `MCP_SERVER_URL` to the MCP service URL.
- Logs only show boolean presence for secrets, not their values.