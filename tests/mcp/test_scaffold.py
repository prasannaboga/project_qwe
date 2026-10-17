"""Tests for MCP module scaffolding, placeholders, and FastAPI ASGI mount."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Mount

from project_qwe.main import app
from project_qwe.mcp.todos import prompts, resources, tools
from project_qwe.mcp.todos.__main__ import main as standalone_main
from project_qwe.mcp.todos.server import mcp_server, mcp_todos_app


def test_mcp_package_exports() -> None:
    """Verify package symbols are cleanly exported."""
    assert mcp_server is not None
    assert mcp_todos_app is not None
    assert isinstance(mcp_todos_app, Starlette)
    assert mcp_server.name == "project-qwe-todos"
    assert mcp_server.instructions == "Todo management and workflow automation protocol server."


def test_mcp_asgi_subapp_routes() -> None:
    """Verify mcp_todos_app defines the expected SSE routes."""
    route_paths = [getattr(r, "path", None) for r in mcp_todos_app.routes]
    assert "/sse" in route_paths
    assert "/messages" in route_paths


def test_tools_placeholders() -> None:
    """Verify the 6 MCP tools exist, are callable, and return valid responses rather than NotImplementedError."""
    tool_funcs = [
        tools.list_todos,
        tools.get_todo_by_id,
        tools.search_todos,
        tools.create_todo,
        tools.update_todo,
        tools.delete_todo,
    ]

    for func in tool_funcs:
        assert callable(func)

    # Basic execution check asserting tools are implemented
    created = tools.create_todo("Scaffold test todo")
    assert created["title"] == "Scaffold test todo"
    todo_id = created["id"]

    fetched = tools.get_todo_by_id(todo_id)
    assert fetched["id"] == todo_id

    searched = tools.search_todos("Scaffold")
    assert any(t["id"] == todo_id for t in searched)

    updated = tools.update_todo(todo_id, title="Updated scaffold todo")
    assert updated["title"] == "Updated scaffold todo"

    listed = tools.list_todos()
    assert "items" in listed
    assert listed["per_page"] == 10

    deleted = tools.delete_todo(todo_id)
    assert deleted["success"] is True



def test_resources_placeholders() -> None:
    """Verify the MCP context resource placeholders exist and raise NotImplementedError."""
    resource_funcs = [
        resources.items,
        resources.items_by_id,
        resources.summary,
        resources.priorities,
    ]

    for func in resource_funcs:
        assert callable(func)

    with pytest.raises(NotImplementedError, match="Placeholder"):
        resources.items()
    with pytest.raises(NotImplementedError, match="Placeholder"):
        resources.items_by_id(1)
    with pytest.raises(NotImplementedError, match="Placeholder"):
        resources.summary()
    with pytest.raises(NotImplementedError, match="Placeholder"):
        resources.priorities("high")


def test_prompts_placeholders() -> None:
    """Verify the MCP prompt placeholders exist and raise NotImplementedError."""
    prompt_funcs = [
        prompts.daily_planning,
        prompts.triage_backlog,
        prompts.task_breakdown,
    ]

    for func in prompt_funcs:
        assert callable(func)

    with pytest.raises(NotImplementedError, match="Placeholder"):
        prompts.daily_planning()
    with pytest.raises(NotImplementedError, match="Placeholder"):
        prompts.triage_backlog()
    with pytest.raises(NotImplementedError, match="Placeholder"):
        prompts.task_breakdown(1)


def test_standalone_main_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify standalone entry point executes uvicorn.run with expected arguments."""
    import uvicorn

    recorded_args: dict[str, object] = {}

    def mock_run(app_obj: object, **kwargs: object) -> None:
        recorded_args["app"] = app_obj
        recorded_args.update(kwargs)

    monkeypatch.setattr(uvicorn, "run", mock_run)
    standalone_main()

    assert recorded_args["app"] is mcp_todos_app
    assert recorded_args["host"] == "127.0.0.1"
    assert recorded_args["port"] == 8001
    assert recorded_args["log_level"] == "info"


def test_fastapi_mount_registration() -> None:
    """Verify mcp_todos_app is mounted at /mcp/todos as a Starlette Mount."""
    mounts = [route for route in app.routes if isinstance(route, Mount) and route.path == "/mcp/todos"]
    assert len(mounts) == 1
    mount = mounts[0]
    assert mount.app is mcp_todos_app


def test_fastapi_mount_http_dispatch() -> None:
    """Verify HTTP requests through FastAPI reach the mounted MCP sub-application."""
    client = TestClient(app, base_url="http://127.0.0.1:8000")
    response = client.post(
        "/mcp/todos/messages/",
        headers={"Content-Type": "application/json"},
        json={},
    )
    assert response.status_code == 400
    assert "session_id is required" in response.text


def test_non_regression_core_routes() -> None:
    """Verify existing root and health routes continue to operate without regression."""
    client = TestClient(app)

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.json() == {"message": "Hello from Project QWE"}

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}


def test_ad1_no_orm_models_in_mcp_package() -> None:
    """Verify AD-1 invariant: no direct imports of SQLAlchemy ORM models in src/project_qwe/mcp/."""
    mcp_dir = Path(__file__).resolve().parent.parent.parent / "src" / "project_qwe" / "mcp"
    assert mcp_dir.is_dir()

    for py_file in mcp_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "models" not in alias.name, (
                        f"Prohibited ORM import '{alias.name}' in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "models" not in module and not any("models" in n.name for n in node.names), (
                    f"Prohibited ORM import from '{module}' in {py_file}"
                )

