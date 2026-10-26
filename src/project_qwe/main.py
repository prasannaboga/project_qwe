from fastapi import FastAPI

from project_qwe.api.todos import router as todos_router
from project_qwe.mcp.todos.server import mcp_todos_app

app = FastAPI(title="Project QWE API")

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
