# project_qwe

A FastAPI REST service with a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server, letting AI agent clients manage, search, and prioritize todos directly from conversation and IDE workflows.

## Getting started

**Start the development server**

```bash
uv run fastapi dev src/project_qwe/main.py
# or
uv run uvicorn project_qwe.main:app --reload
```

**Run tests**

```bash
uv run pytest
```

**Open in Antigravity IDE**

```bash
agy-ide .
```

---

## Todos MCP Server

The MCP server is mounted at `/mcp/todos` over a Server-Sent Events (SSE) transport, exposing 6 tools, 4 resources, and 3 guided prompts to AI agent clients.

→ **[Full usage guide](src/project_qwe/mcp/todos/README.md)** — client setup, tools, resources, and prompts.
