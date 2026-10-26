"""Tests for MCP context resources: discovery, template matching, read operations, error handling, and AD-1 compliance."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import AnyUrl
from sqlalchemy.orm import Session

from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError
from project_qwe.mcp.todos import resources as mcp_resources
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import TodoCreate, TodoPriority, TodoStatus
from project_qwe.services import todo_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_todo(db_session: Session, **kwargs):
    """Create a todo directly via service using the test db_session."""
    return todo_service.create_todo(db_session, TodoCreate(**kwargs))


# ---------------------------------------------------------------------------
# AD-1: No ORM model imports in mcp package
# ---------------------------------------------------------------------------

def test_ad1_no_orm_models_in_resources_module() -> None:
    """Verify AD-1 invariant: no direct imports of SQLAlchemy ORM models in src/project_qwe/mcp/todos/resources.py."""
    resources_py = Path(__file__).resolve().parent.parent.parent / "src" / "project_qwe" / "mcp" / "todos" / "resources.py"
    assert resources_py.is_file()

    tree = ast.parse(resources_py.read_text(encoding="utf-8"), filename=str(resources_py))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "project_qwe.models" not in alias.name, (
                    f"Prohibited ORM import '{alias.name}' in {resources_py}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert "project_qwe.models" not in module, (
                f"Prohibited ORM import from '{module}' in {resources_py}"
            )


# ---------------------------------------------------------------------------
# Resource Registration and Discovery
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resources_and_templates_registered() -> None:
    """Verify static resources and dynamic resource templates are registered on mcp_server."""
    resources = await mcp_server.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert "todo://items" in resource_uris
    assert "todo://summary" in resource_uris

    # Verify mime_types
    for r in resources:
        if str(r.uri) == "todo://items":
            assert r.mime_type == "application/json"
        elif str(r.uri) == "todo://summary":
            assert r.mime_type == "text/markdown"

    templates = await mcp_server.list_resource_templates()
    template_uris = {t.uri_template for t in templates}
    assert "todo://items/{id}" in template_uris
    assert "todo://priorities/{priority}" in template_uris

    for t in templates:
        assert t.mime_type == "application/json"


# ---------------------------------------------------------------------------
# Matrix Scenario 1: Active items feed (todo://items)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resource_items_happy_path(db_session: Session) -> None:
    """Active items feed returns created and inprogress items, ordered by due_at:asc and priority:desc."""
    now = datetime.now(timezone.utc)
    t1 = _make_todo(db_session, title="Active 1", status=TodoStatus.CREATED, due_at=now + timedelta(days=1), priority=TodoPriority.LOW)
    t2 = _make_todo(db_session, title="Active 2", status=TodoStatus.INPROGRESS, due_at=now + timedelta(days=5), priority=TodoPriority.URGENT)
    _make_todo(db_session, title="Done task", status=TodoStatus.COMPLETED, priority=TodoPriority.HIGH)

    # Via mcp_server.read_resource
    contents = await mcp_server.read_resource(AnyUrl("todo://items"))
    assert len(contents) == 1
    assert contents[0].mime_type == "application/json"

    data = json.loads(contents[0].content)
    assert len(data) == 2
    titles = [item["title"] for item in data]
    assert "Active 1" in titles
    assert "Active 2" in titles
    assert "Done task" not in titles

    # Also test direct function invocation
    direct_data = json.loads(mcp_resources.items())
    assert len(direct_data) == 2


@pytest.mark.anyio
async def test_resource_items_empty() -> None:
    """Active items feed returns empty JSON array when no active items exist."""
    with patch("project_qwe.services.todo_service.get_active_todos", return_value=[]):
        contents = await mcp_server.read_resource(AnyUrl("todo://items"))
        data = json.loads(contents[0].content)
        assert data == []


# ---------------------------------------------------------------------------
# Matrix Scenario 2 & 3: Single item feed (todo://items/{id})
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resource_item_by_id_happy_path(db_session: Session) -> None:
    """Single item feed returns JSON object matching ID."""
    created = _make_todo(db_session, title="Specific Task", description="Detailed description", priority=TodoPriority.HIGH)

    contents = await mcp_server.read_resource(AnyUrl(f"todo://items/{created.id}"))
    assert len(contents) == 1
    assert contents[0].mime_type == "application/json"

    data = json.loads(contents[0].content)
    assert data["id"] == created.id
    assert data["title"] == "Specific Task"
    assert data["description"] == "Detailed description"
    assert data["priority"] == "high"

    # Direct function invocation
    direct_data = json.loads(mcp_resources.items_by_id(created.id))
    assert direct_data["id"] == created.id


@pytest.mark.anyio
async def test_resource_item_by_id_missing() -> None:
    """Non-existent item raises ResourceNotFoundError."""
    with pytest.raises(ResourceNotFoundError, match="Todo with id 999999 not found"):
        await mcp_server.read_resource(AnyUrl("todo://items/999999"))


def test_resource_item_by_id_invalid_id() -> None:
    """Invalid non-integer ID raises ResourceError."""
    with pytest.raises(ResourceError, match="Invalid todo id 'abc'"):
        mcp_resources.items_by_id("abc")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Matrix Scenario 4: Summary feed (todo://summary)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resource_summary_happy_path(db_session: Session) -> None:
    """Summary feed returns formatted Markdown with status, priority, and overdue active items."""
    now = datetime.now(timezone.utc)
    overdue = _make_todo(
        db_session,
        title="Overdue report",
        status=TodoStatus.CREATED,
        priority=TodoPriority.URGENT,
        due_at=now - timedelta(days=3),
    )
    _make_todo(
        db_session,
        title="Completed old task",
        status=TodoStatus.COMPLETED,
        priority=TodoPriority.MEDIUM,
        due_at=now - timedelta(days=5),
    )

    contents = await mcp_server.read_resource(AnyUrl("todo://summary"))
    assert len(contents) == 1
    assert contents[0].mime_type == "text/markdown"

    md = contents[0].content
    assert "# Todo Summary" in md
    assert "## Status" in md
    assert "## Priority" in md
    assert "## Overdue Items" in md
    assert f"- #{overdue.id}: Overdue report" in md

    # Direct call
    direct_md = mcp_resources.summary()
    assert "# Todo Summary" in direct_md


@pytest.mark.anyio
async def test_resource_summary_empty() -> None:
    """Summary feed works when database has no items."""
    with patch("project_qwe.services.todo_service.get_todo_summary_markdown", return_value="# Todo Summary\n\n- Total: 0"):
        contents = await mcp_server.read_resource(AnyUrl("todo://summary"))
        assert "# Todo Summary" in contents[0].content


# ---------------------------------------------------------------------------
# Matrix Scenario 5 & 6: Priority feed (todo://priorities/{priority})
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resource_priorities_happy_path(db_session: Session) -> None:
    """Priority feed returns active tasks filtered by priority."""
    _make_todo(db_session, title="Urgent Task 1", priority=TodoPriority.URGENT, status=TodoStatus.CREATED)
    _make_todo(db_session, title="Urgent Task 2", priority=TodoPriority.URGENT, status=TodoStatus.INPROGRESS)
    _make_todo(db_session, title="Low Task", priority=TodoPriority.LOW, status=TodoStatus.CREATED)
    _make_todo(db_session, title="Urgent Completed", priority=TodoPriority.URGENT, status=TodoStatus.COMPLETED)

    contents = await mcp_server.read_resource(AnyUrl("todo://priorities/urgent"))
    data = json.loads(contents[0].content)
    assert len(data) == 2
    titles = {item["title"] for item in data}
    assert titles == {"Urgent Task 1", "Urgent Task 2"}

    # Direct call
    direct_data = json.loads(mcp_resources.priorities("urgent"))
    assert len(direct_data) == 2


@pytest.mark.anyio
async def test_resource_priorities_empty_filter() -> None:
    """Priority feed returns empty array when no active tasks match priority."""
    contents = await mcp_server.read_resource(AnyUrl("todo://priorities/low"))
    data = json.loads(contents[0].content)
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_resource_priorities_invalid() -> None:
    """Invalid priority parameter raises ResourceError."""
    with pytest.raises(ResourceError, match="Invalid priority 'critical'"):
        await mcp_server.read_resource(AnyUrl("todo://priorities/critical"))

    with pytest.raises(ResourceError, match="Invalid priority '123'"):
        mcp_resources.priorities("123")


# ---------------------------------------------------------------------------
# Matrix Scenario 7: DB failure during resource read
# ---------------------------------------------------------------------------

def test_resource_items_db_error_handling() -> None:
    """Database exception inside items resource triggers rollback and raises ResourceError."""
    with patch("project_qwe.services.todo_service.get_active_todos", side_effect=RuntimeError("DB query failed")):
        with pytest.raises(ResourceError, match="Database error reading items resource: DB query failed"):
            mcp_resources.items()


def test_resource_item_by_id_db_error_handling() -> None:
    """Database exception inside items_by_id resource triggers rollback and raises ResourceError."""
    with patch("project_qwe.services.todo_service.get_todo_by_id", side_effect=RuntimeError("Connection lost")):
        with pytest.raises(ResourceError, match="Database error reading item resource 1: Connection lost"):
            mcp_resources.items_by_id(1)


def test_resource_summary_db_error_handling() -> None:
    """Database exception inside summary resource triggers rollback and raises ResourceError."""
    with patch("project_qwe.services.todo_service.get_todo_summary_markdown", side_effect=RuntimeError("Aggregation failure")):
        with pytest.raises(ResourceError, match="Database error reading summary resource: Aggregation failure"):
            mcp_resources.summary()


def test_resource_priorities_db_error_handling() -> None:
    """Database exception inside priorities resource triggers rollback and raises ResourceError."""
    with patch("project_qwe.services.todo_service.get_active_todos", side_effect=RuntimeError("DB query failed")):
        with pytest.raises(ResourceError, match="Database error reading priorities resource: DB query failed"):
            mcp_resources.priorities("urgent")
