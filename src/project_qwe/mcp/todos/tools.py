"""Todo MCP tool implementations registered with the MCP server.

All tools acquire database sessions exclusively from ``SessionLocal()`` via context
managers. No ORM model imports are permitted in this module (AD-1).
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime
from typing import Annotated, Any, Callable

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from project_qwe.config.database import SessionLocal
from project_qwe.config.settings import settings
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import (
    TodoCreate,
    TodoPriority,
    TodoResponse,
    TodoStatus,
    TodoUpdate,
)
from project_qwe.services import todo_service


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CURSOR_VERSION = 1
_CURSOR_MODE = "created_at_desc_id_desc"
_CURSOR_SORT = "created_at:desc,id:desc"
_MAX_CURSOR_LENGTH = 1024

def _serialize_todo(todo: Any) -> dict[str, Any]:
    """Serialize a Todo ORM instance to a plain dict via TodoResponse."""
    return TodoResponse.model_validate(todo).model_dump(mode="json")


def _parse_priority(priority_str: str | None) -> TodoPriority | None:
    """Validate and coerce a priority string to the TodoPriority enum.

    Returns None if *priority_str* is None.

    Raises:
        ToolError: If *priority_str* is not a recognized priority value.
    """
    if priority_str is None:
        return None
    allowed = {e.value: e for e in TodoPriority}
    if priority_str not in allowed:
        raise ToolError(
            f"Invalid priority '{priority_str}'. Allowed values: {sorted(allowed)}"
        )
    return allowed[priority_str]


def _parse_status(status_str: str | None) -> TodoStatus | None:
    """Validate and coerce a status string to the TodoStatus enum.

    Returns None if *status_str* is None.

    Raises:
        ToolError: If *status_str* is not a recognized status value.
    """
    if status_str is None:
        return None
    allowed = {e.value: e for e in TodoStatus}
    if status_str not in allowed:
        raise ToolError(
            f"Invalid status '{status_str}'. Allowed values: {sorted(allowed)}"
        )
    return allowed[status_str]


def _encode_cursor(todo: Any, priority: str | None, per_page: int) -> str:
    """Encode the final Todo in a cursor page as an opaque continuation token."""
    payload = {
        "v": _CURSOR_VERSION,
        "mode": _CURSOR_MODE,
        "priority": priority,
        "per_page": per_page,
        "created_at": todo.created_at.isoformat(),
        "id": todo.id,
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(encoded).decode().rstrip("=")


def _decode_cursor(cursor: str, priority: str | None, per_page: int) -> tuple[datetime, int]:
    """Validate and decode a list-Todo continuation token."""
    if not cursor or len(cursor) > _MAX_CURSOR_LENGTH:
        raise ToolError("Invalid cursor")
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(payload, dict):
            raise ValueError("cursor must be an object")
        if payload.get("v") != _CURSOR_VERSION or payload.get("mode") != _CURSOR_MODE:
            raise ValueError("unsupported cursor")
        if payload.get("priority") != priority or payload.get("per_page") != per_page:
            raise ValueError("cursor request does not match")
        created_at = datetime.fromisoformat(payload["created_at"])
        todo_id = payload["id"]
        if not isinstance(todo_id, int) or isinstance(todo_id, bool) or todo_id < 1:
            raise ValueError("invalid todo id")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError("Invalid cursor") from exc
    return created_at, todo_id


async def _report_progress(
    ctx: Context | None, progress: int, message: str
) -> None:
    """Report an optional progress update without affecting direct unit calls."""
    if ctx is not None:
        await ctx.report_progress(progress, 3, message)


async def _await_demo_delay(ctx: Context | None) -> None:
    """Emit mutation progress around the optional non-blocking demonstration delay."""
    await _report_progress(ctx, 1, "Validation complete")
    if settings.MCP_TODOS_PROGRESS_DELAY_SECONDS:
        await asyncio.sleep(settings.MCP_TODOS_PROGRESS_DELAY_SECONDS)
    await _report_progress(ctx, 2, "Ready to persist")


def _with_session(operation: Callable[[Any], Any]) -> Any:
    """Run one synchronous Todo service operation in a short-lived database session."""
    with SessionLocal() as db:
        return operation(db)


# ---------------------------------------------------------------------------
# MCP Tool Registrations
# ---------------------------------------------------------------------------

@mcp_server.tool(
    title="List Todos",
    description="List Todo items using existing offset pagination or opaque cursor continuations.",
    annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
)
def list_todos(
    page: Annotated[int | None, Field(title="Page", description="Legacy offset page (1-100).", json_schema_extra={"minimum": 1, "maximum": 100})] = None,
    per_page: Annotated[int, Field(title="Items per page", description="Page size from 5 through 20.", json_schema_extra={"minimum": 5, "maximum": 20})] = 10,
    sort: Annotated[str | None, Field(title="Sort", description="Legacy sort; cursor mode requires created_at:desc,id:desc.")] = None,
    priority: Annotated[str | None, Field(title="Priority filter", description="Optional priority: urgent, high, medium, or low.")] = None,
    cursor: Annotated[str | None, Field(title="Cursor", description="Opaque continuation returned by a previous cursor-mode result.")] = None,
) -> str:
    """Retrieve a paginated list of todo items with default sorting optimized for LLM planning.

    Args:
        page: Page number (1-100, default 1).
        per_page: Items per page, bounded between 5 and 20 (default 10).
        sort: Sort directive(s), e.g. ``"due_at:asc,priority:desc"``.
        priority: Optional filter by priority level (urgent, high, medium, low).

    Returns:
        JSON string with ``items``, ``page``, ``per_page``, and ``has_next_page``.
    """
    if per_page < 5 or per_page > 20:
        raise ToolError("per_page must be between 5 and 20")
    if page is not None and (page < 1 or page > 100):
        raise ToolError("page must be between 1 and 100")

    priority_enum = _parse_priority(priority)
    if cursor is not None:
        if page is not None:
            raise ToolError("page cannot be used with cursor")
        if sort not in (None, _CURSOR_SORT):
            raise ToolError(f"cursor mode requires sort '{_CURSOR_SORT}'")
        cursor_created_at, cursor_id = _decode_cursor(cursor, priority, per_page)
        try:
            with SessionLocal() as db:
                items, has_next_page = todo_service.get_todos_after_cursor(
                    db,
                    per_page=per_page,
                    priority=priority_enum,
                    cursor_created_at=cursor_created_at,
                    cursor_id=cursor_id,
                )
                serialized = [_serialize_todo(t) for t in items]
        except Exception as exc:
            raise ToolError(str(exc)) from exc
        next_cursor = _encode_cursor(items[-1], priority, per_page) if has_next_page else None
        return json.dumps({"items": serialized, "per_page": per_page, "next_cursor": next_cursor})

    try:
        with SessionLocal() as db:
            items, has_next_page = todo_service.get_todos(
                db,
                page=page or 1,
                per_page=per_page,
                sort=sort or "due_at:asc,priority:desc",
                priority=priority_enum,
            )
            serialized = [_serialize_todo(t) for t in items]
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    return json.dumps(
        {
            "items": serialized,
            "page": page or 1,
            "per_page": per_page,
            "has_next_page": has_next_page,
        }
    )


@mcp_server.tool()
def get_todo_by_id(todo_id: int) -> str:
    """Fetch complete details of a specific todo item by its unique integer identifier.

    Args:
        todo_id: ID of the todo item to retrieve.

    Returns:
        JSON representation of the todo item.
    """
    try:
        with SessionLocal() as db:
            todo = todo_service.get_todo_by_id(db, todo_id)
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    if todo is None:
        raise ToolError(f"Todo with id {todo_id} not found")
    return json.dumps(_serialize_todo(todo))


@mcp_server.tool()
def search_todos(query: str, limit: int = 5) -> str:
    """Search for todo items matching text in their title or description.

    Args:
        query: Keywords to match (case-insensitive substring, min length 1).
        limit: Maximum results to return (1-20, default 5).

    Returns:
        JSON string containing an array of matching todo items ordered by update time.
    """
    try:
        with SessionLocal() as db:
            items = todo_service.search_todos(db, query=query, limit=limit)
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    return json.dumps([_serialize_todo(t) for t in items])


@mcp_server.tool(
    title="Create Todo",
    description="Create a Todo and report progress to capable MCP clients.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False),
)
async def create_todo(
    title: Annotated[str, Field(title="Title", description="Required nonblank Todo title.", json_schema_extra={"minLength": 1})],
    description: Annotated[str | None, Field(title="Description", description="Optional Todo detail, at most 1000 characters.", json_schema_extra={"maxLength": 1000})] = None,
    status: Annotated[str | None, Field(title="Status", description="Optional status: created, inprogress, or completed.")] = None,
    priority: Annotated[str | None, Field(title="Priority", description="Optional priority: urgent, high, medium, or low.")] = None,
    due_at: Annotated[str | None, Field(title="Due date", description="Optional ISO-8601 due date-time.")] = None,
    ctx: Context | None = None,
) -> str:
    """Create a new todo item in the database.

    Args:
        title: Task title (required, min length 1).
        description: Optional detailed task notes (max 1000 chars).
        status: Initial status (created | inprogress | completed, default: created).
        priority: Priority level (urgent | high | medium | low, default: medium).
        due_at: ISO-8601 datetime string for the target completion timestamp (optional).

    Returns:
        JSON representation of the newly created todo item with generated id and timestamps.
    """
    if not title or not title.strip():
        raise ToolError("title must not be empty")
    if description is not None and len(description) > 1000:
        raise ToolError("description must not exceed 1000 characters")

    status_enum = _parse_status(status)
    priority_enum = _parse_priority(priority)

    due_at_dt: datetime | None = None
    if due_at is not None:
        try:
            due_at_dt = datetime.fromisoformat(due_at)
        except ValueError as exc:
            raise ToolError(f"due_at must be a valid ISO-8601 datetime string: {exc}") from exc

    # Only pass status/priority when explicitly supplied so schema defaults apply when omitted
    create_kwargs: dict[str, Any] = {"title": title, "description": description, "due_at": due_at_dt}
    if status_enum is not None:
        create_kwargs["status"] = status_enum
    if priority_enum is not None:
        create_kwargs["priority"] = priority_enum

    payload = TodoCreate(**create_kwargs)
    await _await_demo_delay(ctx)
    try:
        todo = await asyncio.to_thread(
            _with_session, lambda db: todo_service.create_todo(db, payload)
        )
        result = _serialize_todo(todo)
    except Exception as exc:
        raise ToolError(str(exc)) from exc
    await _report_progress(ctx, 3, "Todo created")
    return json.dumps(result)


@mcp_server.tool(
    title="Update Todo",
    description="Partially update a Todo and report progress to capable MCP clients.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False),
)
async def update_todo(
    todo_id: Annotated[int, Field(title="Todo ID", description="Positive identifier of the Todo to update.", json_schema_extra={"minimum": 1})],
    title: Annotated[str | None, Field(title="Title", description="Optional nonblank replacement title.", json_schema_extra={"minLength": 1})] = None,
    description: Annotated[str | None, Field(title="Description", description="Optional replacement detail, at most 1000 characters.", json_schema_extra={"maxLength": 1000})] = None,
    status: Annotated[str | None, Field(title="Status", description="Optional status: created, inprogress, or completed.")] = None,
    priority: Annotated[str | None, Field(title="Priority", description="Optional priority: urgent, high, medium, or low.")] = None,
    due_at: Annotated[str | None, Field(title="Due date", description="Optional ISO-8601 replacement due date-time.")] = None,
    ctx: Context | None = None,
) -> str:
    """Update fields of an existing todo item.

    Args:
        todo_id: ID of the todo to modify (required).
        title: Updated title (optional, min length 1).
        description: Updated description (optional, max 1000 chars).
        status: New status (created | inprogress | completed).
        priority: New priority (urgent | high | medium | low).
        due_at: New due date as ISO-8601 datetime string.

    Returns:
        JSON representation of the updated todo item.
    """
    if title is not None and not title.strip():
        raise ToolError("title must not be empty")
    if description is not None and len(description) > 1000:
        raise ToolError("description must not exceed 1000 characters")

    status_enum = _parse_status(status)
    priority_enum = _parse_priority(priority)

    due_at_dt: datetime | None = None
    if due_at is not None:
        try:
            due_at_dt = datetime.fromisoformat(due_at)
        except ValueError as exc:
            raise ToolError(f"due_at must be a valid ISO-8601 datetime string: {exc}") from exc

    # Only include explicitly provided fields so omitted fields are not erased
    update_kwargs: dict[str, Any] = {}
    if title is not None:
        update_kwargs["title"] = title
    if description is not None:
        update_kwargs["description"] = description
    if status_enum is not None:
        update_kwargs["status"] = status_enum
    if priority_enum is not None:
        update_kwargs["priority"] = priority_enum
    if due_at_dt is not None:
        update_kwargs["due_at"] = due_at_dt

    payload = TodoUpdate(**update_kwargs)
    await _await_demo_delay(ctx)
    try:
        todo = await asyncio.to_thread(
            _with_session, lambda db: todo_service.update_todo(db, todo_id, payload)
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    if todo is None:
        raise ToolError(f"Todo with id {todo_id} not found")
    await _report_progress(ctx, 3, "Todo updated")
    return json.dumps(_serialize_todo(todo))


@mcp_server.tool(
    title="Delete Todo",
    description="Permanently delete a Todo and report progress to capable MCP clients.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True),
)
async def delete_todo(
    todo_id: Annotated[int, Field(title="Todo ID", description="Positive identifier of the Todo to delete.", json_schema_extra={"minimum": 1})],
    ctx: Context | None = None,
) -> str:
    """Permanently delete a todo item by ID.

    Args:
        todo_id: ID of the todo item to delete (required).

    Returns:
        JSON confirmation object on success.
    """
    await _await_demo_delay(ctx)
    try:
        deleted = await asyncio.to_thread(
            _with_session, lambda db: todo_service.delete_todo(db, todo_id)
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    if not deleted:
        raise ToolError(f"Todo with id {todo_id} not found")
    await _report_progress(ctx, 3, "Todo deleted")
    return json.dumps({"success": True, "message": f"Todo {todo_id} deleted successfully"})


__all__ = [
    "list_todos",
    "get_todo_by_id",
    "search_todos",
    "create_todo",
    "update_todo",
    "delete_todo",
]
