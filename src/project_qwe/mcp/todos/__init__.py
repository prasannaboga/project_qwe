"""Todo domain Model Context Protocol (MCP) package."""

from project_qwe.mcp.todos import prompts, resources, tools
from project_qwe.mcp.todos.server import mcp_server, mcp_todos_app

__all__ = [
    "mcp_server",
    "mcp_todos_app",
    "tools",
    "resources",
    "prompts",
]
