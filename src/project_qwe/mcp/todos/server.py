"""MCP server definition and Streamable HTTP ASGI sub-application."""

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

mcp_server = MCPServer(
    name="project-qwe-todos",
    instructions="Todo management and workflow automation protocol server.",
)

# Widen allowed hosts/origins to cover VS Code and other local clients that
# may omit the port from their Host header (e.g. "localhost" vs "localhost:8000").
_dev_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "127.0.0.1:*",
        "127.0.0.1",
        "localhost:*",
        "localhost",
        "[::1]:*",
        "[::1]",
    ],
    allowed_origins=[
        "http://127.0.0.1:*",
        "http://127.0.0.1",
        "http://localhost:*",
        "http://localhost",
        "http://[::1]:*",
        "http://[::1]",
    ],
)

# Streamable HTTP transport: single-endpoint, session-managed, no hot-reload session loss.
# All MCP traffic goes to /mcp (relative to the mount point, i.e. POST/GET /mcp/todos/mcp).
# The Starlette app returned here carries its own lifespan (StreamableHTTPSessionManager.run())
# which FastAPI propagates automatically when the sub-app is mounted.
mcp_todos_app: Starlette = mcp_server.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    transport_security=_dev_security,
)

# Import tools, resources, and prompts modules to trigger decorator registrations at module load time.
# These imports MUST come after mcp_server is defined.
from project_qwe.mcp.todos import prompts as _prompts  # noqa: E402, F401
from project_qwe.mcp.todos import resources as _resources  # noqa: E402, F401
from project_qwe.mcp.todos import tools as _tools  # noqa: E402, F401

__all__ = ["mcp_server", "mcp_todos_app"]

