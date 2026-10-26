"""Tests for MCP guided prompts: discovery, argument schema, rendering, error handling, and AD-1 compliance."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from project_qwe.mcp.todos import prompts as mcp_prompts
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
# AD-1: No ORM model imports in prompts module
# ---------------------------------------------------------------------------

def test_ad1_no_orm_models_in_prompts_module() -> None:
    """Verify AD-1 invariant: no direct imports of SQLAlchemy ORM models in src/project_qwe/mcp/todos/prompts.py."""
    prompts_py = Path(__file__).resolve().parent.parent.parent / "src" / "project_qwe" / "mcp" / "todos" / "prompts.py"
    assert prompts_py.is_file()

    tree = ast.parse(prompts_py.read_text(encoding="utf-8"), filename=str(prompts_py))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "project_qwe.models" not in alias.name, (
                    f"Prohibited ORM import '{alias.name}' in {prompts_py}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert "project_qwe.models" not in module, (
                f"Prohibited ORM import from '{module}' in {prompts_py}"
            )


# ---------------------------------------------------------------------------
# Prompt Registration and Discovery
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_all_three_prompts_registered() -> None:
    """Verify daily_planning, triage_backlog, and task_breakdown are registered with mcp_server."""
    prompts_list = await mcp_server.list_prompts()
    prompt_map = {p.name: p for p in prompts_list}

    assert "daily_planning" in prompt_map
    assert "triage_backlog" in prompt_map
    assert "task_breakdown" in prompt_map

    # Check argument definitions
    dp_args = {arg.name: arg for arg in prompt_map["daily_planning"].arguments or []}
    assert "focus_area" in dp_args
    assert dp_args["focus_area"].required is False

    tb_args = {arg.name: arg for arg in prompt_map["triage_backlog"].arguments or []}
    assert "limit" in tb_args
    assert tb_args["limit"].required is False

    breakdown_args = {arg.name: arg for arg in prompt_map["task_breakdown"].arguments or []}
    assert "todo_id" in breakdown_args
    assert breakdown_args["todo_id"].required is True


# ---------------------------------------------------------------------------
# Matrix Scenario 1 & 2: Daily Planning Prompt
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_prompt_daily_planning_default(db_session: Session) -> None:
    """daily_planning without arguments embeds live summary and provides 3-5 item agenda instructions."""
    _make_todo(db_session, title="Morning Review Task", priority=TodoPriority.HIGH)

    # Render via server
    result = await mcp_server.get_prompt("daily_planning", {})
    assert len(result.messages) == 1
    text = result.messages[0].content.text
    assert "executive productivity assistant" in text
    assert "## Current Todo Context" in text
    assert "# Todo Summary" in text
    assert "Morning Review Task" not in text  # summary only has aggregated numbers
    assert "3 to 5 high-impact, realistic tasks" in text

    # Direct call
    direct_text = mcp_prompts.daily_planning()
    assert "executive productivity assistant" in direct_text


@pytest.mark.anyio
async def test_prompt_daily_planning_with_focus_area(db_session: Session) -> None:
    """daily_planning with focus_area highlights the specified domain in the guidance."""
    result = await mcp_server.get_prompt("daily_planning", {"focus_area": "Infrastructure Reliability"})
    text = result.messages[0].content.text
    assert "## Focus Area: Infrastructure Reliability" in text
    assert "Pay special attention to tasks aligning with 'Infrastructure Reliability'" in text


# ---------------------------------------------------------------------------
# Matrix Scenario 3 & 4: Triage Backlog Prompt
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_prompt_triage_backlog_with_items(db_session: Session) -> None:
    """triage_backlog lists created/backlog tasks and provides auditing instructions."""
    _make_todo(db_session, title="Backlog Task A", priority=TodoPriority.URGENT, status=TodoStatus.CREATED)
    _make_todo(db_session, title="Backlog Task B", priority=TodoPriority.LOW, status=TodoStatus.CREATED)
    _make_todo(db_session, title="Inprogress Task", status=TodoStatus.INPROGRESS)

    result = await mcp_server.get_prompt("triage_backlog", {})
    text = result.messages[0].content.text
    assert "agile product backlog curator" in text
    assert "Backlog Task A" in text
    assert "Backlog Task B" in text
    assert "Inprogress Task" not in text
    assert "Audit the clarity, specificity, and completeness" in text


@pytest.mark.anyio
async def test_prompt_triage_backlog_custom_limit(db_session: Session) -> None:
    """triage_backlog respects custom limit argument."""
    for i in range(5):
        _make_todo(db_session, title=f"Backlog Item {i}", status=TodoStatus.CREATED)

    result = await mcp_server.get_prompt("triage_backlog", {"limit": 2})
    text = result.messages[0].content.text
    assert "showing 2 of up to 2 requested" in text


@pytest.mark.anyio
async def test_prompt_triage_backlog_empty() -> None:
    """triage_backlog handles empty backlog with friendly notice."""
    with patch("project_qwe.services.todo_service.get_backlog_todos", return_value=[]):
        text = mcp_prompts.triage_backlog()
        assert "No unstarted tasks found in the backlog" in text


# ---------------------------------------------------------------------------
# Matrix Scenario 5, 6, 7: Task Breakdown Prompt
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_prompt_task_breakdown_happy_path(db_session: Session) -> None:
    """task_breakdown embeds parent task details and instructs create_todo sub-task formatting."""
    due = datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
    todo = _make_todo(
        db_session,
        title="Epic Database Migration",
        description="Migrate PostgreSQL database to distributed cluster",
        priority=TodoPriority.URGENT,
        due_at=due,
    )

    result = await mcp_server.get_prompt("task_breakdown", {"todo_id": todo.id})
    text = result.messages[0].content.text
    assert "expert technical project lead" in text
    assert f"#{todo.id}" in text
    assert "Epic Database Migration" in text
    assert "Migrate PostgreSQL database to distributed cluster" in text
    assert "urgent" in text
    assert "create_todo" in text
    assert '"tool": "create_todo"' in text

    # Direct call
    direct_text = mcp_prompts.task_breakdown(todo.id)
    assert "Epic Database Migration" in direct_text


@pytest.mark.anyio
async def test_prompt_task_breakdown_missing_id() -> None:
    """task_breakdown with non-existent ID raises ValueError."""
    with pytest.raises(ValueError, match="Error rendering prompt task_breakdown") as exc_info:
        await mcp_server.get_prompt("task_breakdown", {"todo_id": 999999})
    # MCPServer wraps render exception
    cause = exc_info.value.__cause__
    root_cause = cause.__cause__ if cause else None
    assert root_cause is not None
    assert "Todo with id 999999 not found" in str(root_cause)

    # Direct function invocation raises ValueError directly
    with pytest.raises(ValueError, match="Todo with id 999999 not found"):
        mcp_prompts.task_breakdown(999999)


def test_prompt_task_breakdown_invalid_id() -> None:
    """task_breakdown with invalid non-integer ID raises ValueError."""
    with pytest.raises(ValueError, match="Invalid todo_id 'invalid'. Must be an integer."):
        mcp_prompts.task_breakdown("invalid")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Matrix Scenario 8: DB Failure during Prompt Rendering
# ---------------------------------------------------------------------------

def test_prompt_daily_planning_db_error() -> None:
    """Database exception inside daily_planning triggers rollback and raises ValueError."""
    with patch("project_qwe.services.todo_service.get_todo_summary_markdown", side_effect=RuntimeError("DB query failed")):
        with pytest.raises(ValueError, match="Database error rendering daily_planning prompt: DB query failed"):
            mcp_prompts.daily_planning()


def test_prompt_triage_backlog_db_error() -> None:
    """Database exception inside triage_backlog triggers rollback and raises ValueError."""
    with patch("project_qwe.services.todo_service.get_backlog_todos", side_effect=RuntimeError("DB timeout")):
        with pytest.raises(ValueError, match="Database error rendering triage_backlog prompt: DB timeout"):
            mcp_prompts.triage_backlog()


def test_prompt_task_breakdown_db_error() -> None:
    """Database exception inside task_breakdown triggers rollback and raises ValueError."""
    with patch("project_qwe.services.todo_service.get_todo_by_id", side_effect=RuntimeError("Connection closed")):
        with pytest.raises(ValueError, match="Database error rendering task_breakdown prompt: Connection closed"):
            mcp_prompts.task_breakdown(1)
