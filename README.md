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
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies with [uv](https://github.com/astral-sh/uv):
   ```bash
   uv pip install -e .[dev]
   ```
   
   Or with pip:
   ```bash
   pip install -e .[dev]
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set:
   - `MCP_API_KEY`: A secret key for MCP authentication (e.g., `mysecretkey`)
   - `MCP_SERVER_URL`: URL where MCP server will run (default: `http://localhost:8001`)
   - `OPENAI_API_KEY`: Your OpenAI API key

## Running the Servers

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

## Using the API

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

## Integration Testing

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