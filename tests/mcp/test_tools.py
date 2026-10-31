"""Tests for the 6 MCP todo tools: happy paths, boundary validation, error handling, and AD-1 compliance."""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path

import pytest

# Importing the tools module also registers all @mcp_server.tool() decorators
from project_qwe.mcp.todos import tools as mcp_tools
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import TodoCreate, TodoUpdate
from project_qwe.services import todo_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_todo(db_session, **kwargs):
    """Create a todo directly via service using the test db_session."""
    return todo_service.create_todo(db_session, TodoCreate(**kwargs))


@pytest.fixture(autouse=True)
def run_async_mutation_tools(monkeypatch):
    """Keep direct legacy unit calls compatible with async MCP write handlers."""
    for name in ("create_todo", "update_todo", "delete_todo"):
        original = getattr(mcp_tools, name)
        monkeypatch.setattr(
            mcp_tools,
            name,
            lambda *args, _original=original, **kwargs: asyncio.run(
                _original(*args, **kwargs)
            ),
        )


# ---------------------------------------------------------------------------
# AD-1: No ORM model imports in mcp package
# ---------------------------------------------------------------------------

def test_ad1_no_orm_models_in_mcp_package() -> None:
    """Verify AD-1 invariant: no direct imports of SQLAlchemy ORM models in src/project_qwe/mcp/."""
    mcp_dir = Path(__file__).resolve().parent.parent.parent / "src" / "project_qwe" / "mcp"
    assert mcp_dir.is_dir()

    for py_file in mcp_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "project_qwe.models" not in alias.name, (
                        f"Prohibited ORM import '{alias.name}' in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "project_qwe.models" not in module, (
                    f"Prohibited ORM import from '{module}' in {py_file}"
                )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def test_all_six_tools_registered() -> None:
    """All 6 tools must be registered with mcp_server."""
    registered = {t.name for t in mcp_server._tool_manager.list_tools()}
    expected = {"list_todos", "get_todo_by_id", "search_todos", "create_todo", "update_todo", "delete_todo"}
    assert expected.issubset(registered)


# ---------------------------------------------------------------------------
# list_todos
# ---------------------------------------------------------------------------

def test_list_todos_default(db_session) -> None:
    """Returns JSON with items, page, per_page, has_next_page."""
    _make_todo(db_session, title="Task A")
    _make_todo(db_session, title="Task B")

    result = json.loads(mcp_tools.list_todos())
    assert "items" in result
    assert result["page"] == 1
    assert result["per_page"] == 10
    assert "has_next_page" in result
    assert len(result["items"]) == 2


def test_list_todos_per_page_too_low(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="per_page must be between 5 and 20"):
        mcp_tools.list_todos(per_page=4)


def test_list_todos_per_page_too_high(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="per_page must be between 5 and 20"):
        mcp_tools.list_todos(per_page=21)


def test_list_todos_per_page_boundary_valid(db_session) -> None:
    """per_page=5 and per_page=20 are valid boundaries."""
    result5 = json.loads(mcp_tools.list_todos(per_page=5))
    assert result5["per_page"] == 5
    result20 = json.loads(mcp_tools.list_todos(per_page=20))
    assert result20["per_page"] == 20


def test_list_todos_priority_filter(db_session) -> None:
    _make_todo(db_session, title="Urgent task", priority="urgent")
    _make_todo(db_session, title="Low task", priority="low")

    result = json.loads(mcp_tools.list_todos(priority="urgent"))
    assert all(item["priority"] == "urgent" for item in result["items"])
    assert len(result["items"]) == 1


def test_list_todos_invalid_priority(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="Invalid priority"):
        mcp_tools.list_todos(priority="super_high")


def test_list_todos_invalid_sort(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError):
        mcp_tools.list_todos(sort="badfield:asc")


def test_list_todos_pagination(db_session) -> None:
    for i in range(12):
        _make_todo(db_session, title=f"Task {i}")

    page1 = json.loads(mcp_tools.list_todos(per_page=10, page=1))
    assert len(page1["items"]) == 10
    assert page1["has_next_page"] is True

    page2 = json.loads(mcp_tools.list_todos(per_page=10, page=2))
    assert len(page2["items"]) == 2
    assert page2["has_next_page"] is False


def test_list_todos_default_sort_nulls_last(db_session) -> None:
    """Default sort due_at:asc,priority:desc — tasks with due_at appear before those without."""
    from datetime import datetime, timezone
    due = datetime(2026, 11, 1, tzinfo=timezone.utc)
    _make_todo(db_session, title="No due")
    t_due = _make_todo(db_session, title="Has due", due_at=due)

    result = json.loads(mcp_tools.list_todos())
    assert result["items"][0]["id"] == t_due.id


# ---------------------------------------------------------------------------
# get_todo_by_id
# ---------------------------------------------------------------------------

def test_get_todo_by_id_found(db_session) -> None:
    todo = _make_todo(db_session, title="Specific task", description="Details here")

    result = json.loads(mcp_tools.get_todo_by_id(todo_id=todo.id))
    assert result["id"] == todo.id
    assert result["title"] == "Specific task"
    assert result["description"] == "Details here"


def test_get_todo_by_id_not_found(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="not found"):
        mcp_tools.get_todo_by_id(todo_id=99999)


# ---------------------------------------------------------------------------
# search_todos
# ---------------------------------------------------------------------------

def test_search_todos_title_match(db_session) -> None:
    _make_todo(db_session, title="Meeting with team")
    _make_todo(db_session, title="Buy coffee")

    result = json.loads(mcp_tools.search_todos(query="meeting"))
    assert len(result) == 1
    assert result[0]["title"] == "Meeting with team"


def test_search_todos_description_match(db_session) -> None:
    _make_todo(db_session, title="Sprint planning", description="Discuss DB migration")
    _make_todo(db_session, title="Code review")

    result = json.loads(mcp_tools.search_todos(query="migration"))
    assert len(result) == 1
    assert result[0]["title"] == "Sprint planning"


def test_search_todos_empty_query_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="query must not be empty"):
        mcp_tools.search_todos(query="   ")


def test_search_todos_limit_out_of_range(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="limit must be between 1 and 20"):
        mcp_tools.search_todos(query="test", limit=50)


def test_search_todos_no_match(db_session) -> None:
    _make_todo(db_session, title="Unrelated task")
    result = json.loads(mcp_tools.search_todos(query="xyznotfound"))
    assert result == []


def test_search_todos_respects_limit(db_session) -> None:
    for i in range(10):
        _make_todo(db_session, title=f"Task {i} keyword")

    result = json.loads(mcp_tools.search_todos(query="keyword", limit=3))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# create_todo
# ---------------------------------------------------------------------------

def test_create_todo_success(db_session) -> None:
    result = json.loads(mcp_tools.create_todo(title="Buy milk"))
    assert result["id"] is not None
    assert result["title"] == "Buy milk"
    assert result["status"] == "created"
    assert result["priority"] == "medium"


def test_create_todo_with_all_fields(db_session) -> None:
    result = json.loads(
        mcp_tools.create_todo(
            title="Full task",
            description="Some details",
            status="inprogress",
            priority="high",
            due_at="2026-12-01T18:00:00",
        )
    )
    assert result["title"] == "Full task"
    assert result["description"] == "Some details"
    assert result["status"] == "inprogress"
    assert result["priority"] == "high"
    assert result["due_at"] is not None


def test_create_todo_empty_title_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="title must not be empty"):
        mcp_tools.create_todo(title="   ")


def test_create_todo_invalid_priority_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="Invalid priority"):
        mcp_tools.create_todo(title="Task", priority="critical")


def test_create_todo_invalid_status_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="Invalid status"):
        mcp_tools.create_todo(title="Task", status="unknown")


def test_create_todo_invalid_due_at_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="ISO-8601"):
        mcp_tools.create_todo(title="Task", due_at="not-a-date")


def test_create_todo_description_too_long_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="1000 characters"):
        mcp_tools.create_todo(title="Task", description="x" * 1001)


# ---------------------------------------------------------------------------
# update_todo
# ---------------------------------------------------------------------------

def test_update_todo_partial(db_session) -> None:
    from datetime import datetime, timezone
    due = datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
    todo = _make_todo(
        db_session,
        title="Old title",
        description="Preserve this notes",
        status="created",
        priority="high",
        due_at=due,
    )

    result = json.loads(mcp_tools.update_todo(todo_id=todo.id, status="inprogress"))
    assert result["id"] == todo.id
    assert result["title"] == "Old title"
    assert result["status"] == "inprogress"
    assert result["description"] == "Preserve this notes"
    assert result["priority"] == "high"
    assert result["due_at"] is not None


def test_update_todo_update_description_and_due_at(db_session) -> None:
    todo = _make_todo(db_session, title="Old title")
    result = json.loads(
        mcp_tools.update_todo(
            todo_id=todo.id,
            description="Updated description",
            due_at="2026-12-15T18:00:00",
        )
    )
    assert result["description"] == "Updated description"
    assert "2026-12-15" in result["due_at"]


def test_update_todo_not_found(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="not found"):
        mcp_tools.update_todo(todo_id=99999, title="New title")


def test_update_todo_invalid_priority(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    todo = _make_todo(db_session, title="Task")
    with pytest.raises(ToolError, match="Invalid priority"):
        mcp_tools.update_todo(todo_id=todo.id, priority="badvalue")


def test_update_todo_empty_title_raises(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    todo = _make_todo(db_session, title="Task")
    with pytest.raises(ToolError, match="title must not be empty"):
        mcp_tools.update_todo(todo_id=todo.id, title="   ")


def test_update_todo_invalid_due_at(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    todo = _make_todo(db_session, title="Task")
    with pytest.raises(ToolError, match="ISO-8601"):
        mcp_tools.update_todo(todo_id=todo.id, due_at="not-a-date")


# ---------------------------------------------------------------------------
# delete_todo
# ---------------------------------------------------------------------------

def test_delete_todo_success(db_session) -> None:
    todo = _make_todo(db_session, title="To delete")

    result = json.loads(mcp_tools.delete_todo(todo_id=todo.id))
    assert result["success"] is True
    assert "deleted" in result["message"].lower() or str(todo.id) in result["message"]


def test_delete_todo_not_found(db_session) -> None:
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="not found"):
        mcp_tools.delete_todo(todo_id=99999)


def test_delete_todo_removes_from_db(db_session) -> None:
    todo = _make_todo(db_session, title="Ephemeral task")
    mcp_tools.delete_todo(todo_id=todo.id)

    fetched = todo_service.get_todo_by_id(db_session, todo.id)
    assert fetched is None
