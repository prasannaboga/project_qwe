from collections.abc import Sequence

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo, TodoPriority, TodoStatus
from project_qwe.schemas.todo import TodoCreate, TodoUpdate


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


ALLOWED_SORT_FIELDS = {"id", "title", "due_at", "created_at", "updated_at", "priority"}
ALLOWED_SORT_DIRECTIONS = {"asc", "desc"}


def get_todos(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    sort: str = "due_at:asc,priority:desc",
    priority: TodoPriority | None = None,
) -> tuple[Sequence[Todo], bool]:
    """Retrieve paginated Todo items with deterministic sorting and limit+1 next-page detection.

    Args:
        db: Database session to query against.
        page: Page number (1-based, 1 to 100).
        per_page: Number of items per page (1 to 100).
        sort: Comma-separated sort directives formatted as '<field>:<direction>'.
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

    if not sort or not sort.strip():
        raise ValueError("Invalid sort format. Expected '<field>:<direction>'")

    sort_parts = [part.strip() for part in sort.split(",")]
    if not sort_parts or any(not part for part in sort_parts):
        raise ValueError("Invalid sort format. Expected '<field>:<direction>'")

    order_clauses = []
    seen_fields = set()
    last_direction = "asc"

    for part in sort_parts:
        if ":" not in part:
            raise ValueError("Invalid sort format. Expected '<field>:<direction>'")

        field, direction = part.split(":", 1)
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

        seen_fields.add(field)
        last_direction = direction

        if field == "priority":
            priority_order = case(
                {
                    TodoPriority.URGENT: 4,
                    TodoPriority.HIGH: 3,
                    TodoPriority.MEDIUM: 2,
                    TodoPriority.LOW: 1,
                },
                value=Todo.priority,
            )
            order_clauses.append(
                priority_order.desc() if direction == "desc" else priority_order.asc()
            )
        elif field == "due_at":
            order_clauses.append(
                Todo.due_at.asc().nulls_last()
                if direction == "asc"
                else Todo.due_at.desc().nulls_last()
            )
        else:
            column_attr = getattr(Todo, field)
            sort_func = getattr(column_attr, direction)
            order_clauses.append(sort_func())

    if "id" not in seen_fields:
        id_sort_func = getattr(Todo.id, last_direction)
        order_clauses.append(id_sort_func())

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


def search_todos(
    db: Session,
    query: str,
    limit: int = 5,
) -> Sequence[Todo]:
    """Search Todo items across title and description with a configurable limit.

    Args:
        db: Database session to query against.
        query: Search string to match in title or description.
        limit: Maximum number of items to return (1 to 20).

    Returns:
        A sequence of matching Todo items ordered by updated_at:desc.

    Raises:
        ValueError: If query is empty or limit is not between 1 and 20.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1 or limit > 20:
        raise ValueError("limit must be between 1 and 20")

    clean_query = query.strip()
    stmt = (
        select(Todo)
        .where(
            or_(
                Todo.title.ilike(f"%{clean_query}%"),
                Todo.description.ilike(f"%{clean_query}%"),
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
