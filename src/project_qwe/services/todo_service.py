from collections.abc import Sequence

from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo, TodoPriority, TodoStatus
from project_qwe.schemas.todo import TodoCreate, TodoUpdate

# Urgency weights for SQL-level priority ordering (higher = more urgent)
_PRIORITY_URGENCY: dict[str, int] = {
    TodoPriority.URGENT: 4,
    TodoPriority.HIGH: 3,
    TodoPriority.MEDIUM: 2,
    TodoPriority.LOW: 1,
}


def _priority_order_expr():
    """Return a SQLAlchemy case expression that maps priority values to urgency ints."""
    return case(_PRIORITY_URGENCY, value=Todo.priority)


# Note: 'priority' sorting uses semantic urgency order via SQL case, not alphabetical.
ALLOWED_SORT_FIELDS = {"id", "title", "due_at", "created_at", "updated_at", "priority"}
ALLOWED_SORT_DIRECTIONS = {"asc", "desc"}


def _build_sort_clauses(sort: str) -> list:
    """Parse a comma-separated sort directive string and return SQLAlchemy order-by clauses.

    Supports single directives (``"created_at:desc"``) and compound directives
    (``"due_at:asc,priority:desc"``). ``due_at:asc`` automatically applies
    ``NULLS LAST`` so tasks without a deadline appear after dated tasks.

    Args:
        sort: Sort directive string, e.g. ``"due_at:asc,priority:desc"``.

    Returns:
        List of SQLAlchemy column / expression order-by clauses.

    Raises:
        ValueError: If any directive token is malformed or references an invalid field/direction.
    """
    clauses: list = []
    for token in sort.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"Invalid sort token '{token}'. Expected '<field>:<direction>'")
        field, direction = token.split(":", 1)
        field = field.strip().lower()
        direction = direction.strip().lower()

        if field not in ALLOWED_SORT_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed fields: {sorted(ALLOWED_SORT_FIELDS)}"
            )
        if direction not in ALLOWED_SORT_DIRECTIONS:
            raise ValueError(
                f"Invalid sort direction '{direction}'. Allowed directions: 'asc', 'desc'"
            )

        if field == "priority":
            expr = _priority_order_expr()
            clause = expr.desc() if direction == "desc" else expr.asc()
        else:
            col = getattr(Todo, field)
            if field == "due_at" and direction == "asc":
                clause = col.asc().nulls_last()
            elif field == "due_at" and direction == "desc":
                clause = col.desc().nulls_last()
            else:
                clause = getattr(col, direction)()
        clauses.append(clause)

    if not clauses:
        raise ValueError("sort string produced no valid directives")

    return clauses


def create_todo(db: Session, todo_data: TodoCreate) -> Todo:
    """Create a new Todo item in the database with status, priority, description, and due_at.

    Args:
        db: Database session to persist the Todo.
        todo_data: Pydantic schema containing todo attributes.

    Returns:
        The newly created and committed Todo ORM instance.
    """
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
        status=todo_data.status or TodoStatus.CREATED,
        priority=todo_data.priority or TodoPriority.MEDIUM,
        due_at=todo_data.due_at,
    )
    db.add(todo)
    try:
        db.commit()
        db.refresh(todo)
        return todo
    except Exception:
        db.rollback()
        raise


def get_todos(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    sort: str = "created_at:desc",
    priority: TodoPriority | None = None,
) -> tuple[Sequence[Todo], bool]:
    """Retrieve paginated Todo items with deterministic compound sorting and limit+1 next-page detection.

    Supports comma-separated compound sort strings such as ``"due_at:asc,priority:desc"``.
    ``priority`` sort uses semantic urgency order (``urgent`` > ``high`` > ``medium`` > ``low``).
    ``due_at`` ascending automatically places ``NULL`` values last.

    Args:
        db: Database session to query against.
        page: Page number (1-based, 1 to 100).
        per_page: Number of items per page (1 to 100).
        sort: Sort directive(s) formatted as ``'<field>:<dir>'`` or ``'<f1>:<d1>,<f2>:<d2>'``.
        priority: Optional priority filter level.

    Returns:
        A tuple of (items, has_next_page) containing the fetched Todo items and next-page boolean.

    Raises:
        ValueError: If pagination or sort parameters are invalid.
    """
    if page < 1 or page > 100:
        raise ValueError("page must be between 1 and 100")
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100")

    order_clauses = _build_sort_clauses(sort)

    # Always append id as a deterministic tie-breaker when it isn't already in the sort
    sort_fields_used = {tok.split(":")[0].strip().lower() for tok in sort.split(",") if ":" in tok}
    if "id" not in sort_fields_used:
        # Use the same direction as the first sort clause for consistency
        first_token = sort.split(",")[0].strip()
        first_dir = first_token.split(":")[1].strip().lower() if ":" in first_token else "desc"
        order_clauses.append(getattr(Todo.id, first_dir)())

    stmt = select(Todo)
    if priority is not None:
        stmt = stmt.where(Todo.priority == priority)
    stmt = stmt.order_by(*order_clauses)

    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page + 1)

    results = db.scalars(stmt).all()
    has_next_page = len(results) > per_page
    items = results[:per_page]

    return items, has_next_page


def get_todos_after_cursor(
    db: Session,
    *,
    per_page: int,
    priority: TodoPriority | None = None,
    cursor_created_at: datetime | None = None,
    cursor_id: int | None = None,
) -> tuple[Sequence[Todo], bool]:
    """Return one keyset-paginated Todo page in created-at descending order.

    The optional cursor boundary is exclusive, so a stable collection has neither
    duplicates nor gaps while a client follows returned page tokens.
    """
    if per_page < 5 or per_page > 20:
        raise ValueError("per_page must be between 5 and 20")
    if (cursor_created_at is None) != (cursor_id is None):
        raise ValueError("cursor timestamp and id must be supplied together")

    stmt = select(Todo)
    if priority is not None:
        stmt = stmt.where(Todo.priority == priority)
    if cursor_created_at is not None and cursor_id is not None:
        stmt = stmt.where(
            or_(
                Todo.created_at < cursor_created_at,
                and_(Todo.created_at == cursor_created_at, Todo.id < cursor_id),
            )
        )
    results = db.scalars(
        stmt.order_by(Todo.created_at.desc(), Todo.id.desc()).limit(per_page + 1)
    ).all()
    return results[:per_page], len(results) > per_page


def search_todos(db: Session, query: str, limit: int = 5) -> Sequence[Todo]:
    """Search Todo items by case-insensitive substring match on title and description.

    Args:
        db: Database session to query against.
        query: Search string (must be non-empty after stripping whitespace).
        limit: Maximum number of results to return (1 to 20, default 5).

    Returns:
        Sequence of matching Todo items ordered by ``updated_at`` descending.

    Raises:
        ValueError: If ``query`` is empty/whitespace-only, or ``limit`` is out of range.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if limit < 1 or limit > 20:
        raise ValueError("limit must be between 1 and 20")

    escaped_query = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    pattern = f"%{escaped_query}%"
    stmt = (
        select(Todo)
        .where(
            or_(
                func.lower(Todo.title).like(func.lower(pattern), escape="\\"),
                func.lower(func.coalesce(Todo.description, "")).like(func.lower(pattern), escape="\\"),
            )
        )
        .order_by(Todo.updated_at.desc(), Todo.id.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


def get_todo_by_id(db: Session, todo_id: int) -> Todo | None:
    """Retrieve a single Todo item by its ID."""
    stmt = select(Todo).where(Todo.id == todo_id)
    return db.scalars(stmt).first()


def update_todo(db: Session, todo_id: int, todo_data: TodoUpdate) -> Todo | None:
    """Update an existing Todo item's title, description, status, priority, or due_at.

    Args:
        db: Database session to persist updates.
        todo_id: ID of the Todo to update.
        todo_data: Pydantic update schema containing fields to modify.

    Returns:
        The updated Todo ORM instance if found, or None if no Todo with the ID exists.
    """
    todo = get_todo_by_id(db, todo_id)
    if todo is None:
        return None

    if todo_data.title is not None:
        todo.title = todo_data.title
    if todo_data.description is not None or "description" in todo_data.model_fields_set:
        todo.description = todo_data.description
    if todo_data.status is not None:
        todo.status = todo_data.status
    if todo_data.priority is not None:
        todo.priority = todo_data.priority
    if todo_data.due_at is not None or "due_at" in todo_data.model_fields_set:
        todo.due_at = todo_data.due_at

    try:
        db.commit()
        db.refresh(todo)
        return todo
    except Exception:
        db.rollback()
        raise


def delete_todo(db: Session, todo_id: int) -> bool:
    """Delete a Todo item by ID. Returns True if deleted, False if not found."""
    todo = get_todo_by_id(db, todo_id)
    if todo is None:
        return False

    try:
        db.delete(todo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def get_active_todos(
    db: Session,
    priority: TodoPriority | str | None = None,
) -> Sequence[Todo]:
    """Retrieve all active (created, inprogress) Todo items sorted by due date and priority.

    Active items are defined as tasks with status ``created`` or ``inprogress``.
    Results are sorted by ``due_at:asc`` (nulls last), ``priority:desc`` (semantic urgency order),
    and ``id:asc`` as a deterministic tie-breaker.

    Args:
        db: Database session to query against.
        priority: Optional priority filter (TodoPriority enum or case-insensitive string).

    Returns:
        Sequence of active Todo items matching the criteria.
    """
    stmt = select(Todo).where(
        Todo.status.in_([TodoStatus.CREATED, TodoStatus.INPROGRESS])
    )
    if priority is not None:
        if isinstance(priority, str):
            priority = TodoPriority(priority.lower())
        stmt = stmt.where(Todo.priority == priority)

    order_clauses = _build_sort_clauses("due_at:asc,priority:desc")
    order_clauses.append(Todo.id.asc())
    stmt = stmt.order_by(*order_clauses)

    return db.scalars(stmt).all()


def get_backlog_todos(
    db: Session,
    limit: int = 20,
) -> Sequence[Todo]:
    """Retrieve unstarted backlog Todo items (status='created') ordered by priority and age.

    Args:
        db: Database session to query against.
        limit: Maximum number of backlog items to return (1 to 50, default 20).

    Returns:
        Sequence of backlog Todo items.

    Raises:
        ValueError: If limit is not between 1 and 50.
    """
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    stmt = (
        select(Todo)
        .where(Todo.status == TodoStatus.CREATED)
        .order_by(_priority_order_expr().desc(), Todo.created_at.asc(), Todo.id.asc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


def get_todo_summary(db: Session) -> dict[str, object]:
    """Calculate aggregated todo summary statistics and overdue active items.

    Aggregates status counts across all TodoStatus values, priority counts across
    all TodoPriority values, calculates total items, and finds active items whose
    ``due_at`` timestamp is in the past.

    Args:
        db: Database session to query against.

    Returns:
        Dict containing ``status_counts``, ``priority_counts``, ``total``, and ``overdue_items``.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    status_counts: dict[TodoStatus, int] = {s: 0 for s in TodoStatus}
    for s, count in db.execute(select(Todo.status, func.count(Todo.id)).group_by(Todo.status)):
        status_enum = s if isinstance(s, TodoStatus) else TodoStatus(s)
        status_counts[status_enum] = count

    priority_counts: dict[TodoPriority, int] = {p: 0 for p in TodoPriority}
    for p, count in db.execute(select(Todo.priority, func.count(Todo.id)).group_by(Todo.priority)):
        priority_enum = p if isinstance(p, TodoPriority) else TodoPriority(p)
        priority_counts[priority_enum] = count

    total = sum(status_counts.values())

    overdue_stmt = (
        select(Todo)
        .where(
            Todo.status.in_([TodoStatus.CREATED, TodoStatus.INPROGRESS]),
            Todo.due_at.is_not(None),
            Todo.due_at < now,
        )
        .order_by(Todo.due_at.asc(), _priority_order_expr().desc(), Todo.id.asc())
    )
    overdue_items = db.scalars(overdue_stmt).all()

    return {
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "total": total,
        "overdue_items": overdue_items,
    }


def get_todo_summary_markdown(db: Session) -> str:
    """Generate a GitHub Flavored Markdown summary document of all todos.

    Formats status breakdown, priority breakdown, and a bulleted list of
    overdue active items.

    Args:
        db: Database session to query against.

    Returns:
        Markdown string formatted according to the PRD FR-14 specification.
    """
    summary = get_todo_summary(db)
    status_counts: dict[TodoStatus, int] = summary["status_counts"]  # type: ignore[assignment]
    priority_counts: dict[TodoPriority, int] = summary["priority_counts"]  # type: ignore[assignment]
    total: int = summary["total"]  # type: ignore[assignment]
    overdue_items: Sequence[Todo] = summary["overdue_items"]  # type: ignore[assignment]

    lines = [
        "# Todo Summary",
        "",
        "## Status",
        f"- Created: {status_counts.get(TodoStatus.CREATED, 0)}",
        f"- In Progress: {status_counts.get(TodoStatus.INPROGRESS, 0)}",
        f"- Completed: {status_counts.get(TodoStatus.COMPLETED, 0)}",
        f"- Total: {total}",
        "",
        "## Priority",
        f"- Urgent: {priority_counts.get(TodoPriority.URGENT, 0)}",
        f"- High: {priority_counts.get(TodoPriority.HIGH, 0)}",
        f"- Medium: {priority_counts.get(TodoPriority.MEDIUM, 0)}",
        f"- Low: {priority_counts.get(TodoPriority.LOW, 0)}",
        "",
        "## Overdue Items",
    ]

    if not overdue_items:
        lines.append("- None")
    else:
        for item in overdue_items:
            priority_val = item.priority.value if hasattr(item.priority, "value") else str(item.priority)
            lines.append(f"- #{item.id}: {item.title} (due: {item.due_at}, priority: {priority_val})")

    return "\n".join(lines)

