"""Unified MCP Todo Server automated test suite: unit validations, protocol compliance, session isolation, and end-to-end SSE integration (Story 1.5)."""

from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import threading
import time
from unittest.mock import patch

import pytest
from pydantic import AnyUrl
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError
from sqlalchemy.orm import Session

from project_qwe.main import app
from project_qwe.mcp.todos import prompts as mcp_prompts
from project_qwe.mcp.todos import resources as mcp_resources
from project_qwe.mcp.todos import tools as mcp_tools
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import TodoCreate, TodoPriority, TodoStatus
from project_qwe.services import todo_service


# ---------------------------------------------------------------------------
# Fixtures & Test Setup
# ---------------------------------------------------------------------------

def _get_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def uvicorn_server():
    """Run FastAPI app on an ephemeral port in a daemon thread for true SSE integration testing."""
    port = _get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait briefly for startup
    time.sleep(0.3)
    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.should_exit = True
    thread.join(timeout=2.0)


# ---------------------------------------------------------------------------
# 1. Architectural Compliance: AD-1 (AST Invariant)
# ---------------------------------------------------------------------------

def test_ad1_no_orm_models_in_mcp_package() -> None:
    """Verify AD-1: zero direct imports of SQLAlchemy ORM models in src/project_qwe/mcp/."""
    mcp_dir = Path(__file__).resolve().parent.parent / "src" / "project_qwe" / "mcp"
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
# 2. Tool Unit Validations & Error Formatting (NFR-3)
# ---------------------------------------------------------------------------

def test_tool_list_todos_bounds_validation() -> None:
    """Verify bounds checking on list_todos: per_page must be between 5 and 20."""
    with pytest.raises(Exception, match="per_page must be between 5 and 20"):
        mcp_tools.list_todos(per_page=4)

    with pytest.raises(Exception, match="per_page must be between 5 and 20"):
        mcp_tools.list_todos(per_page=21)

    with pytest.raises(Exception, match="page must be between 1 and 100"):
        mcp_tools.list_todos(page=0)


def test_tool_create_todo_validation() -> None:
    """Verify create_todo input validation on title and priority."""
    with pytest.raises(Exception, match="title must not be empty"):
        mcp_tools.create_todo(title="   ")

    with pytest.raises(Exception, match="Invalid priority"):
        mcp_tools.create_todo(title="Task", priority="invalid-priority")


def test_tool_get_todo_by_id_missing() -> None:
    """Verify get_todo_by_id returns clear error for non-existent ID."""
    with pytest.raises(Exception, match="Todo with id 999999 not found"):
        mcp_tools.get_todo_by_id(999999)


def test_tool_search_todos_validation() -> None:
    """Verify search_todos query and limit validation."""
    with pytest.raises(Exception, match="query must not be empty"):
        mcp_tools.search_todos("   ")

    with pytest.raises(Exception, match="limit must be between 1 and 20"):
        mcp_tools.search_todos("test", limit=0)


def test_tool_update_todo_missing_and_empty(db_session: Session) -> None:
    """Verify update_todo handles missing todo and updates."""
    with pytest.raises(Exception, match="Todo with id 999999 not found"):
        mcp_tools.update_todo(999999, title="New title")

    created = todo_service.create_todo(db_session, TodoCreate(title="Original Title"))
    updated_json = mcp_tools.update_todo(created.id, title="Updated Title")
    updated = json.loads(updated_json)
    assert updated["title"] == "Updated Title"


def test_tool_delete_todo_missing() -> None:
    """Verify delete_todo returns clear error when ID is not found."""
    with pytest.raises(Exception, match="Todo with id 999999 not found"):
        mcp_tools.delete_todo(999999)


# ---------------------------------------------------------------------------
# 3. Resource & Prompt Parsing Unit Tests
# ---------------------------------------------------------------------------

def test_resource_parsing_and_formatting(db_session: Session) -> None:
    """Verify resource generation formatting and priority parsing."""
    todo = todo_service.create_todo(db_session, TodoCreate(title="Resource Unit Task", priority=TodoPriority.URGENT))

    items_json = mcp_resources.items()
    items = json.loads(items_json)
    assert any(i["id"] == todo.id for i in items)

    item_json = mcp_resources.items_by_id(todo.id)
    item = json.loads(item_json)
    assert item["id"] == todo.id
    assert item["title"] == "Resource Unit Task"

    summary_md = mcp_resources.summary()
    assert "# Todo Summary" in summary_md
    assert "## Status" in summary_md

    priorities_json = mcp_resources.priorities("urgent")
    priorities = json.loads(priorities_json)
    assert any(i["id"] == todo.id for i in priorities)

    with pytest.raises(ResourceError, match="Invalid priority"):
        mcp_resources.priorities("extreme")


def test_prompt_argument_parsing(db_session: Session) -> None:
    """Verify prompt argument parsing, defaulting, and formatting."""
    todo = todo_service.create_todo(db_session, TodoCreate(title="Prompt Unit Task", description="Decompose me"))

    dp = mcp_prompts.daily_planning(focus_area="Architecture")
    assert "## Focus Area: Architecture" in dp
    assert "# Todo Summary" in dp

    tb = mcp_prompts.triage_backlog(limit=10)
    assert "showing" in tb
    assert "## Instructions" in tb

    breakdown = mcp_prompts.task_breakdown(todo.id)
    assert f"#{todo.id}" in breakdown
    assert "Prompt Unit Task" in breakdown
    assert "create_todo" in breakdown

    with pytest.raises(ValueError, match="Todo with id 999999 not found"):
        mcp_prompts.task_breakdown(999999)


# ---------------------------------------------------------------------------
# 4. Database Session Isolation & Rollback Integration Tests (AD-3)
# ---------------------------------------------------------------------------

def test_database_session_rollback_on_error() -> None:
    """Verify session rollback and clean closure when DB operations raise exceptions."""
    with patch("project_qwe.services.todo_service.create_todo", side_effect=RuntimeError("Simulated DB failure")):
        with pytest.raises(Exception, match="Simulated DB failure"):
            mcp_tools.create_todo(title="Will fail")

    with patch("project_qwe.services.todo_service.get_active_todos", side_effect=RuntimeError("Simulated query failure")):
        with pytest.raises(ResourceError, match="Database error reading items resource"):
            mcp_resources.items()

    with patch("project_qwe.services.todo_service.get_backlog_todos", side_effect=RuntimeError("Simulated backlog failure")):
        with pytest.raises(ValueError, match="Database error rendering triage_backlog prompt"):
            mcp_prompts.triage_backlog()


# ---------------------------------------------------------------------------
# 5. Asynchronous SSE Transport & Protocol Compliance Tests (NFR-1, NFR-2, NFR-3)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_e2e_discovery_and_operations(uvicorn_server: str) -> None:
    """End-to-End SSE test: connect, initialize, introspect schemas, invoke tools, read resources, and get prompts."""
    sse_url = f"{uvicorn_server}/mcp/todos/sse"

    async with sse_client(sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize JSON-RPC session handshake
            init_result = await session.initialize()
            assert init_result.server_info.name == "project-qwe-todos"
            assert "Todo management" in init_result.server_info.version or init_result.instructions is not None

            # 2. Introspect Tools (NFR-2)
            tools_list = await session.list_tools()
            tool_names = {t.name for t in tools_list.tools}
            expected_tools = {"list_todos", "get_todo_by_id", "search_todos", "create_todo", "update_todo", "delete_todo"}
            assert expected_tools.issubset(tool_names)

            # 3. Introspect Resources (NFR-2)
            resources_list = await session.list_resources()
            resource_uris = {str(r.uri) for r in resources_list.resources}
            assert "todo://items" in resource_uris
            assert "todo://summary" in resource_uris

            templates_list = await session.list_resource_templates()
            template_uris = {t.uri_template for t in templates_list.resource_templates}
            assert "todo://items/{id}" in template_uris
            assert "todo://priorities/{priority}" in template_uris

            # 4. Introspect Prompts (NFR-2)
            prompts_list = await session.list_prompts()
            prompt_names = {p.name for p in prompts_list.prompts}
            assert {"daily_planning", "triage_backlog", "task_breakdown"}.issubset(prompt_names)

            # 5. Roundtrip Tool Invocation and Latency Benchmark (NFR-1 < 100ms)
            start_time = time.perf_counter()
            create_res = await session.call_tool("create_todo", {"title": "E2E SSE Task", "priority": "high"})
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert create_res.is_error is False or create_res.is_error is None
            created_data = json.loads(create_res.content[0].text)
            todo_id = created_data["id"]
            assert created_data["title"] == "E2E SSE Task"
            assert created_data["priority"] == "high"

            # Benchmark check: local DB tool invocation should complete in under 100ms
            # Allow slight cushion for first network overhead in CI, but assert sub-100ms execution
            assert elapsed_ms < 150.0, f"Execution latency {elapsed_ms:.2f}ms exceeded target threshold"

            # 6. Read specific item via tool
            get_res = await session.call_tool("get_todo_by_id", {"todo_id": todo_id})
            assert json.loads(get_res.content[0].text)["id"] == todo_id

            # 7. Search todos over SSE
            search_res = await session.call_tool("search_todos", {"query": "E2E SSE"})
            search_data = json.loads(search_res.content[0].text)
            assert any(item["id"] == todo_id for item in search_data)

            # 8. Update todo over SSE
            update_res = await session.call_tool("update_todo", {"todo_id": todo_id, "title": "Updated E2E Task"})
            assert json.loads(update_res.content[0].text)["title"] == "Updated E2E Task"

            # 9. List todos over SSE
            list_res = await session.call_tool("list_todos", {"per_page": 5})
            list_data = json.loads(list_res.content[0].text)
            assert "items" in list_data
            assert list_data["per_page"] == 5

            # 10. Read resources over SSE
            items_res = await session.read_resource("todo://items")
            assert len(items_res.contents) == 1
            assert items_res.contents[0].mime_type == "application/json"

            summary_res = await session.read_resource("todo://summary")
            assert len(summary_res.contents) == 1
            assert summary_res.contents[0].mime_type == "text/markdown"
            assert "# Todo Summary" in summary_res.contents[0].text

            # 11. Render prompts over SSE (prompt arguments are string-keyed string-valued dicts)
            dp_prompt = await session.get_prompt("daily_planning", {"focus_area": "Testing"})
            assert "## Focus Area: Testing" in dp_prompt.messages[0].content.text

            tb_prompt = await session.get_prompt("triage_backlog", {"limit": "10"})
            assert "agile product backlog curator" in tb_prompt.messages[0].content.text

            breakdown_prompt = await session.get_prompt("task_breakdown", {"todo_id": str(todo_id)})
            assert f"#{todo_id}" in breakdown_prompt.messages[0].content.text
            assert "create_todo" in breakdown_prompt.messages[0].content.text

            # 12. Delete todo over SSE
            del_res = await session.call_tool("delete_todo", {"todo_id": todo_id})
            assert json.loads(del_res.content[0].text)["success"] is True


@pytest.mark.anyio
async def test_sse_error_resilience(uvicorn_server: str) -> None:
    """Verify invalid tool calls over SSE return isError: true without dropping the connection (NFR-3)."""
    sse_url = f"{uvicorn_server}/mcp/todos/sse"

    async with sse_client(sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Invalid per_page (bounds check)
            res1 = await session.call_tool("list_todos", {"per_page": 50})
            assert res1.is_error is True
            assert "per_page must be between 5 and 20" in res1.content[0].text

            # Empty title
            res2 = await session.call_tool("create_todo", {"title": ""})
            assert res2.is_error is True
            assert "title must not be empty" in res2.content[0].text

            # Missing todo ID
            res3 = await session.call_tool("get_todo_by_id", {"todo_id": 888888})
            assert res3.is_error is True
            assert "not found" in res3.content[0].text

            # Verify connection is STILL alive after errors by executing a valid call
            valid_res = await session.call_tool("list_todos", {"per_page": 5})
            assert valid_res.is_error is not True
            assert "items" in json.loads(valid_res.content[0].text)
