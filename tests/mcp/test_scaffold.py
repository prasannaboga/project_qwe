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
    """Verify mcp_todos_app defines the expected Streamable HTTP route at root."""
    route_paths = [getattr(r, "path", None) for r in mcp_todos_app.routes]
    assert "/" in route_paths


def test_tools_placeholders() -> None:
    """Verify the 6 MCP tools exist, are callable, and return valid JSON responses (implemented)."""
    import anyio
    import json as _json

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

    # Basic execution check asserting tools are fully implemented.
    # create_todo / update_todo / delete_todo are async; run them via anyio.
    async def _run() -> None:
        created = _json.loads(await tools.create_todo("Scaffold test todo"))
        assert created["title"] == "Scaffold test todo"
        todo_id = created["id"]

        fetched = _json.loads(tools.get_todo_by_id(todo_id))
        assert fetched["id"] == todo_id

        searched = _json.loads(tools.search_todos("Scaffold"))
        assert any(t["id"] == todo_id for t in searched)

        updated = _json.loads(await tools.update_todo(todo_id, title="Updated scaffold todo"))
        assert updated["title"] == "Updated scaffold todo"

        listed = _json.loads(tools.list_todos())
        assert "items" in listed
        assert listed["per_page"] == 10

        deleted = _json.loads(await tools.delete_todo(todo_id))
        assert deleted["success"] is True

    anyio.run(_run)



def test_resources_placeholders() -> None:
    """Verify the MCP context resources exist, are callable, and return valid responses (implemented)."""
    import json as _json

    resource_funcs = [
        resources.items,
        resources.items_by_id,
        resources.summary,
        resources.priorities,
    ]

    for func in resource_funcs:
        assert callable(func)

    # Basic execution check asserting resources are fully implemented
    items_out = _json.loads(resources.items())
    assert isinstance(items_out, list)

    summary_out = resources.summary()
    assert "# Todo Summary" in summary_out

    priorities_out = _json.loads(resources.priorities("medium"))
    assert isinstance(priorities_out, list)


def test_prompts_placeholders() -> None:
    """Verify the MCP prompts exist, are callable, and return valid prompt strings (implemented)."""
    prompt_funcs = [
        prompts.daily_planning,
        prompts.triage_backlog,
        prompts.task_breakdown,
    ]

    for func in prompt_funcs:
        assert callable(func)

    # Basic execution check asserting prompts are fully implemented
    dp_out = prompts.daily_planning()
    assert "daily task planning" in dp_out

    tb_out = prompts.triage_backlog()
    assert "Backlog Items" in tb_out


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
    # StreamableHTTPSessionManager requires its lifespan task-group to be running.
    # Using TestClient as a context manager triggers all sub-app lifespans.
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        # The Streamable HTTP transport is at the mount root, so the full path is /mcp/todos.
        # A POST without a valid MCP-Protocol-Version header should get 400.
        response = client.post(
            "/mcp/todos",
            headers={"Content-Type": "application/json"},
            json={},
        )
        # The transport rejects malformed MCP messages with 400 (bad request) or
        # 405 (method not allowed for GET-only streams); anything other than 404
        # confirms the endpoint is correctly mounted and reachable.
        assert response.status_code != 404


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

