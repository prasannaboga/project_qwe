"""Placeholder definitions for Todo MCP guided prompts."""


def daily_planning(focus_area: str | None = None) -> str:
    """Guided prompt for daily planning with optional focus area."""
    raise NotImplementedError("Placeholder for Story 1.4 implementation")


def triage_backlog() -> str:
    """Guided prompt for evaluating backlog items."""
    raise NotImplementedError("Placeholder for Story 1.4 implementation")


def task_breakdown(todo_id: int) -> str:
    """Guided prompt for decomposing a todo into sub-tasks."""
    raise NotImplementedError("Placeholder for Story 1.4 implementation")


__all__ = [
    "daily_planning",
    "triage_backlog",
    "task_breakdown",
]
