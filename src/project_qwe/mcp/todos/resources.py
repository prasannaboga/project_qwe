"""Placeholder definitions for Todo MCP context resources."""


def items() -> str:
    """Read active items context feed (todo://items)."""
    raise NotImplementedError("Placeholder for Story 1.3 implementation")


def items_by_id(todo_id: int) -> str:
    """Read details for a single task by ID context feed (todo://items/{id})."""
    raise NotImplementedError("Placeholder for Story 1.3 implementation")


def summary() -> str:
    """Read aggregated overview of todos (todo://summary)."""
    raise NotImplementedError("Placeholder for Story 1.3 implementation")


def priorities(priority: str) -> str:
    """Read active items filtered by priority level (todo://priorities/{priority})."""
    raise NotImplementedError("Placeholder for Story 1.3 implementation")


__all__ = [
    "items",
    "items_by_id",
    "summary",
    "priorities",
]
