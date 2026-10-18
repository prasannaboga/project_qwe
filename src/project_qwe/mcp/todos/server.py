"""MCP server definition and SSE ASGI sub-application."""

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette

mcp_server = MCPServer(
    name="project-qwe-todos",
    instructions="Todo management and workflow automation protocol server.",
)

mcp_todos_app: Starlette = mcp_server.sse_app(
    sse_path="/sse",
    message_path="/messages",
)

# Import tools module to trigger @mcp_server.tool() registrations at module load time.
# This import MUST come after mcp_server is defined.
from project_qwe.mcp.todos import tools as _tools  # noqa: E402, F401

__all__ = ["mcp_server", "mcp_todos_app"]
