"""Todo MCP tools implementation."""

from datetime import datetime
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from project_qwe.config.database import SessionLocal
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.schemas.todo import (
    TodoCreate,
    TodoPaginationResponse,
    TodoPriority,
    TodoResponse,
    TodoStatus,
    TodoUpdate,
)
from project_qwe.services import todo_service


@mcp_server.tool()
def list_todos(
    page: int = 1,
    per_page: int = 10,
    priority: str | None = None,
) -> dict[str, Any]:
    """List todos with pagination and optional priority filtering."""
    if per_page < 5 or per_page > 20:
        raise ToolError("per_page must be between 5 and 20")
    if page < 1 or page > 100:
        raise ToolError("page must be between 1 and 100")

    priority_enum: TodoPriority | None = None
    if priority is not None:
        try:
            priority_enum = TodoPriority(priority.strip().lower())
        except ValueError:
            valid_priorities = [p.value for p in TodoPriority]
            raise ToolError(
                f"Invalid priority '{priority}'. Allowed values: {', '.join(valid_priorities)}"
            )

    try:
        with SessionLocal() as db:
            items, has_next_page = todo_service.get_todos(
                db,
                page=page,
                per_page=per_page,
                sort="due_at:asc,priority:desc",
                priority=priority_enum,
            )
            response = TodoPaginationResponse(
                items=[TodoResponse.model_validate(item) for item in items],
                page=page,
                per_page=per_page,
                has_next_page=has_next_page,
            )
            return response.model_dump(mode="json")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


@mcp_server.tool()
def get_todo_by_id(todo_id: int) -> dict[str, Any]:
    """Retrieve a single todo item by its integer ID."""
    try:
        with SessionLocal() as db:
            todo = todo_service.get_todo_by_id(db, todo_id)
            if todo is None:
                raise ToolError(f"Todo with id {todo_id} not found")
            return TodoResponse.model_validate(todo).model_dump(mode="json")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


@mcp_server.tool()
def search_todos(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search todos across title and description with a configurable limit."""
    if not query or not query.strip():
        raise ToolError("query must not be empty")
    if limit < 1 or limit > 20:
        raise ToolError("limit must be between 1 and 20")

    try:
        with SessionLocal() as db:
            todos = todo_service.search_todos(db, query=query.strip(), limit=limit)
            return [TodoResponse.model_validate(todo).model_dump(mode="json") for todo in todos]
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


@mcp_server.tool()
def create_todo(
    title: str,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Create a new todo item."""
    payload: dict[str, Any] = {"title": title}
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    if priority is not None:
        payload["priority"] = priority
    if due_at is not None:
        payload["due_at"] = due_at

    try:
        todo_data = TodoCreate.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise ToolError(f"Validation error: {exc}")

    try:
        with SessionLocal() as db:
            todo = todo_service.create_todo(db, todo_data)
            return TodoResponse.model_validate(todo).model_dump(mode="json")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


@mcp_server.tool()
def update_todo(
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Update an existing todo item by its integer ID."""
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    if priority is not None:
        payload["priority"] = priority
    if due_at is not None:
        payload["due_at"] = due_at

    try:
        todo_data = TodoUpdate.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise ToolError(f"Validation error: {exc}")

    try:
        with SessionLocal() as db:
            updated = todo_service.update_todo(db, todo_id, todo_data)
            if updated is None:
                raise ToolError(f"Todo with id {todo_id} not found")
            return TodoResponse.model_validate(updated).model_dump(mode="json")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


@mcp_server.tool()
def delete_todo(todo_id: int) -> dict[str, Any]:
    """Delete a todo item by its integer ID."""
    try:
        with SessionLocal() as db:
            deleted = todo_service.delete_todo(db, todo_id)
            if not deleted:
                raise ToolError(f"Todo with id {todo_id} not found")
            return {
                "success": True,
                "message": f"Todo with id {todo_id} deleted successfully",
            }
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc))


__all__ = [
    "list_todos",
    "get_todo_by_id",
    "search_todos",
    "create_todo",
    "update_todo",
    "delete_todo",
]
