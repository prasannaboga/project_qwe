"""Todo MCP context resource implementations registered with the MCP server.

All resources acquire database sessions exclusively from ``SessionLocal()`` via context
managers. No ORM model imports are permitted in this module (AD-1).
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError
from mcp.types import Annotations

from project_qwe.config.database import SessionLocal
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import (
    TodoPriority,
    TodoResponse,
)
from project_qwe.services import todo_service


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialize_todo(todo: Any) -> dict[str, Any]:
    """Serialize a Todo ORM instance to a plain dict via TodoResponse."""
    return TodoResponse.model_validate(todo).model_dump(mode="json")


def _parse_priority(priority_str: str) -> TodoPriority:
    """Validate and coerce a priority string to the TodoPriority enum.

    Raises:
        ResourceError: If *priority_str* is not a recognized priority value.
    """
    allowed = {e.value: e for e in TodoPriority}
    val = priority_str.lower() if isinstance(priority_str, str) else ""
    if val not in allowed:
        raise ResourceError(
            f"Invalid priority '{priority_str}'. Allowed values: {sorted(allowed)}"
        )
    return allowed[val]


# ---------------------------------------------------------------------------
# MCP Resource Registrations
# ---------------------------------------------------------------------------

@mcp_server.resource("todo://items", mime_type="application/json")
def items() -> str:
    """Read active items context feed (todo://items).

    Returns:
        JSON string containing array of active items sorted by due date and priority.
    """
    try:
        with SessionLocal() as db:
            try:
                active_todos = todo_service.get_active_todos(db)
                serialized = [_serialize_todo(t) for t in active_todos]
            except Exception:
                db.rollback()
                raise
    except ResourceError:
        raise
    except Exception as exc:
        raise ResourceError(f"Database error reading items resource: {exc}") from exc

    return json.dumps(serialized)


@mcp_server.resource(
    "todo://items/{id}",
    name="todo-by-id",
    title="Todo by ID",
    description="Read one Todo as an application/json TodoResponse by its positive integer ID.",
    mime_type="application/json",
    annotations=Annotations(audience=["assistant"]),
)
def items_by_id(id: int) -> str:
    """Read details for a single task by ID context feed (todo://items/{id}).

    Args:
        id: Integer ID of the todo item to retrieve.

    Returns:
        JSON string representing the TodoResponse payload.

    Raises:
        ResourceNotFoundError: If no todo item exists with the specified ID.
    """
    try:
        todo_id = int(id)
    except (ValueError, TypeError):
        raise ResourceError(f"Invalid todo id '{id}'. Must be an integer.")
    if todo_id < 1:
        raise ResourceError(f"Invalid todo id '{id}'. Must be a positive integer.")

    try:
        with SessionLocal() as db:
            try:
                todo = todo_service.get_todo_by_id(db, todo_id)
            except Exception:
                db.rollback()
                raise
    except (ResourceNotFoundError, ResourceError):
        raise
    except Exception as exc:
        raise ResourceError(f"Database error reading item resource {id}: {exc}") from exc

    if todo is None:
        raise ResourceNotFoundError(f"Todo with id {id} not found")

    return json.dumps(_serialize_todo(todo))


@mcp_server.resource("todo://summary", mime_type="text/markdown")
def summary() -> str:
    """Read aggregated overview of todos (todo://summary).

    Returns:
        Markdown string formatted with status breakdown, priority breakdown,
        and list of overdue active items.
    """
    try:
        with SessionLocal() as db:
            try:
                return todo_service.get_todo_summary_markdown(db)
            except Exception:
                db.rollback()
                raise
    except ResourceError:
        raise
    except Exception as exc:
        raise ResourceError(f"Database error reading summary resource: {exc}") from exc


@mcp_server.resource("todo://priorities/{priority}", mime_type="application/json")
def priorities(priority: str) -> str:
    """Read active items filtered by priority level (todo://priorities/{priority}).

    Args:
        priority: Priority level string ('urgent', 'high', 'medium', 'low').

    Returns:
        JSON string containing array of active items matching the priority level.

    Raises:
        ResourceError: If the specified priority level is invalid.
    """
    priority_enum = _parse_priority(priority)

    try:
        with SessionLocal() as db:
            try:
                matching_todos = todo_service.get_active_todos(db, priority=priority_enum)
                serialized = [_serialize_todo(t) for t in matching_todos]
            except Exception:
                db.rollback()
                raise
    except ResourceError:
        raise
    except Exception as exc:
        raise ResourceError(f"Database error reading priorities resource: {exc}") from exc

    return json.dumps(serialized)


__all__ = [
    "items",
    "items_by_id",
    "summary",
    "priorities",
]

