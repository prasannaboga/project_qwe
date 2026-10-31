from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from project_qwe.api.todos import router as todos_router
from project_qwe.mcp.todos.server import mcp_todos_app


class TrailingSlashMiddleware:
    """Rewrite requests to /mcp/todos to /mcp/todos/ without issuing a 307 redirect.

    Starlette's Mount routes expect a trailing slash to match sub-applications.
    Rewriting the ASGI scope path directly allows clients that do not follow POST
    redirects (such as VS Code MCP client) to connect to /mcp/todos or /mcp/todos/.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == "/mcp/todos":
            scope = dict(scope)
            scope["path"] = "/mcp/todos/"
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the MCP session manager alongside the FastAPI app.

    FastAPI does not propagate lifespan events to mounted Starlette sub-apps,
    so we explicitly run the sub-app's own lifespan context here to ensure the
    StreamableHTTPSessionManager's internal task group is initialised before
    any MCP request arrives.
    """
    async with mcp_todos_app.router.lifespan_context(mcp_todos_app):
        yield


app = FastAPI(title="Project QWE API", lifespan=lifespan)
app.add_middleware(TrailingSlashMiddleware)

app.include_router(todos_router)
app.mount("/mcp/todos", mcp_todos_app)


@app.get("/")
def read_root() -> dict[str, str]:
    """Home API endpoint."""
    return {"message": "Hello from Project QWE"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check API endpoint."""
    return {"status": "ok"}
