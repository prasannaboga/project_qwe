"""Todo MCP tool implementations registered with the MCP server.

All tools acquire database sessions exclusively from ``SessionLocal()`` via context
managers. No ORM model imports are permitted in this module (AD-1).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from project_qwe.config.database import SessionLocal
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


# ---------------------------------------------------------------------------
# MCP Tool Registrations
# ---------------------------------------------------------------------------

@mcp_server.tool()
def list_todos(
    page: int = 1,
    per_page: int = 10,
    sort: str = "due_at:asc,priority:desc",
    priority: str | None = None,
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
    if page < 1 or page > 100:
        raise ToolError("page must be between 1 and 100")

    priority_enum = _parse_priority(priority)

    try:
        with SessionLocal() as db:
            items, has_next_page = todo_service.get_todos(
                db, page=page, per_page=per_page, sort=sort, priority=priority_enum
            )
            serialized = [_serialize_todo(t) for t in items]
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    return json.dumps(
        {
            "items": serialized,
            "page": page,
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


@mcp_server.tool()
def create_todo(
    title: str,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: str | None = None,
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
    try:
        with SessionLocal() as db:
            todo = todo_service.create_todo(db, payload)
            result = _serialize_todo(todo)
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    return json.dumps(result)


@mcp_server.tool()
def update_todo(
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: str | None = None,
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
    try:
        with SessionLocal() as db:
            todo = todo_service.update_todo(db, todo_id, payload)
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    if todo is None:
        raise ToolError(f"Todo with id {todo_id} not found")
    return json.dumps(_serialize_todo(todo))


@mcp_server.tool()
def delete_todo(todo_id: int) -> str:
    """Permanently delete a todo item by ID.

    Args:
        todo_id: ID of the todo item to delete (required).

    Returns:
        JSON confirmation object on success.
    """
    try:
        with SessionLocal() as db:
            deleted = todo_service.delete_todo(db, todo_id)
    except Exception as exc:
        raise ToolError(str(exc)) from exc

    if not deleted:
        raise ToolError(f"Todo with id {todo_id} not found")
    return json.dumps({"success": True, "message": f"Todo {todo_id} deleted successfully"})


__all__ = [
    "list_todos",
    "get_todo_by_id",
    "search_todos",
    "create_todo",
    "update_todo",
    "delete_todo",
]
