"""Standalone runner entry point for local development execution."""

import uvicorn

from project_qwe.mcp.todos.server import mcp_todos_app


def main() -> None:
    """Run the Todo MCP ASGI application standalone using uvicorn."""
    uvicorn.run(
        mcp_todos_app,
        host="127.0.0.1",
        port=8001,
        log_level="info",
    )


if __name__ == "__main__":
    main()
