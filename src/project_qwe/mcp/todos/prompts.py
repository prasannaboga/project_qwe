"""Todo MCP guided prompt implementations registered with the MCP server.

All prompts acquire database sessions exclusively from ``SessionLocal()`` via context
managers. No ORM model imports are permitted in this module (AD-1).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from project_qwe.config.database import SessionLocal
from project_qwe.mcp.todos.server import mcp_server
from project_qwe.services import todo_service


@mcp_server.prompt(
    "daily_planning",
    title="Daily Planning",
    description="Guided prompt for daily planning with optional focus area.",
)
def daily_planning(
    focus_area: Annotated[
        str | None,
        Field(
            title="Focus Area",
            description="Optional domain or topic to emphasize during planning.",
        ),
    ] = None,
) -> str:
    """Guided prompt for daily planning with optional focus area.

    Args:
        focus_area: Optional domain or topic to emphasize during planning.

    Returns:
        Rendered prompt text embedding live todo summary and planning instructions.
    """
    try:
        with SessionLocal() as db:
            try:
                summary_md = todo_service.get_todo_summary_markdown(db)
            except Exception:
                db.rollback()
                raise
    except Exception as exc:
        raise ValueError(f"Database error rendering daily_planning prompt: {exc}") from exc

    lines = [
        "You are an executive productivity assistant guiding a daily task planning session.",
        "",
        "## Current Todo Context",
        summary_md,
        "",
    ]

    if focus_area:
        lines.extend([
            f"## Focus Area: {focus_area}",
            f"Pay special attention to tasks aligning with '{focus_area}'.",
            "",
        ])

    lines.extend([
        "## Instructions",
        "1. Review the current status breakdown, priority distribution, and overdue items above.",
        "2. Select 3 to 5 high-impact, realistic tasks to complete today based on priority and deadlines.",
        "3. If overdue items exist, address them first or propose rescheduling them.",
        "4. Present the selected tasks as a structured daily agenda with estimated order of execution and rationale.",
    ])

    return "\n".join(lines)


@mcp_server.prompt(
    "triage_backlog",
    title="Triage Backlog",
    description="Guided prompt for evaluating backlog items.",
)
def triage_backlog(
    limit: Annotated[
        int,
        Field(
            title="Limit",
            description="Maximum number of backlog items to inspect (1-50, default 20).",
            json_schema_extra={"minimum": 1, "maximum": 50},
        ),
    ] = 20,
) -> str:
    """Guided prompt for evaluating backlog items.

    Args:
        limit: Maximum number of backlog items to inspect (default 20, bounded between 1 and 50).

    Returns:
        Rendered prompt text listing unstarted backlog items with auditing instructions.
    """
    try:
        limit_int = int(limit)
        if limit_int < 1:
            limit_int = 1
        elif limit_int > 50:
            limit_int = 50
    except (ValueError, TypeError):
        limit_int = 20

    try:
        with SessionLocal() as db:
            try:
                backlog_items = todo_service.get_backlog_todos(db, limit=limit_int)
            except Exception:
                db.rollback()
                raise
    except Exception as exc:
        raise ValueError(f"Database error rendering triage_backlog prompt: {exc}") from exc

    lines = [
        "You are an agile product backlog curator auditing unstarted tasks.",
        "",
        f"## Backlog Items (showing {len(backlog_items)} of up to {limit_int} requested)",
    ]

    if not backlog_items:
        lines.append("- No unstarted tasks found in the backlog.")
    else:
        for item in backlog_items:
            priority_val = item.priority.value if hasattr(item.priority, "value") else str(item.priority)
            due_str = f", due: {item.due_at}" if item.due_at else ""
            desc_str = f" - {item.description}" if item.description else ""
            lines.append(f"- #{item.id}: {item.title} (priority: {priority_val}{due_str}){desc_str}")

    lines.extend([
        "",
        "## Instructions",
        "1. Audit the clarity, specificity, and completeness of each task title and description.",
        "2. Identify any tasks missing realistic due dates or carrying misaligned priorities.",
        "3. Flag redundant or duplicate items, and recommend merging or deleting them.",
        "4. Identify complex or oversized tasks that should be decomposed into sub-tasks.",
        "5. Provide actionable recommendations for each reviewed item.",
    ])

    return "\n".join(lines)


@mcp_server.prompt(
    "task_breakdown",
    title="Task Breakdown",
    description="Guided prompt for decomposing a todo into sub-tasks.",
)
def task_breakdown(
    todo_id: Annotated[
        int,
        Field(
            title="Todo ID",
            description="Required positive integer ID of the parent todo to decompose.",
            json_schema_extra={"minimum": 1},
        ),
    ],
) -> str:
    """Guided prompt for decomposing a todo into sub-tasks.

    Args:
        todo_id: Required integer ID of the parent todo to decompose.

    Returns:
        Rendered prompt text embedding parent task details and sub-task creation instructions.

    Raises:
        ValueError: If todo_id is invalid or the parent task is not found.
    """
    try:
        todo_id_int = int(todo_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid todo_id '{todo_id}'. Must be an integer.")

    try:
        with SessionLocal() as db:
            try:
                todo = todo_service.get_todo_by_id(db, todo_id_int)
            except Exception:
                db.rollback()
                raise
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Database error rendering task_breakdown prompt: {exc}") from exc

    if todo is None:
        raise ValueError(f"Todo with id {todo_id} not found")

    priority_val = todo.priority.value if hasattr(todo.priority, "value") else str(todo.priority)
    status_val = todo.status.value if hasattr(todo.status, "value") else str(todo.status)

    lines = [
        "You are an expert technical project lead decomposing a high-level task into concrete sub-tasks.",
        "",
        "## Parent Task",
        f"- ID: #{todo.id}",
        f"- Title: {todo.title}",
        f"- Description: {todo.description or 'No description provided'}",
        f"- Status: {status_val}",
        f"- Priority: {priority_val}",
        f"- Due Date: {todo.due_at or 'None'}",
        "",
        "## Instructions",
        "1. Analyze the parent task and break it down into 2 to 5 actionable sub-tasks.",
        "2. Ensure each sub-task has a concise, clear title and an informative description.",
        "3. Assign appropriate priority levels ('urgent', 'high', 'medium', 'low') and realistic due dates relative to the parent task.",
        "4. For EACH sub-task, provide an executable `create_todo` tool call formatted as JSON:",
        "```json",
        "{",
        '  "tool": "create_todo",',
        '  "arguments": {',
        '    "title": "Sub-task title",',
        '    "description": "Sub-task description",',
        '    "priority": "medium",',
        '    "due_at": "YYYY-MM-DDTHH:MM:SSZ"',
        "  }",
        "}",
        "```",
    ]

    return "\n".join(lines)


__all__ = [
    "daily_planning",
    "triage_backlog",
    "task_breakdown",
]
