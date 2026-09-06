from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo, TodoStatus
from project_qwe.schemas.todo import TodoCreate, TodoUpdate


def create_todo(db: Session, todo_data: TodoCreate) -> Todo:
    """Create a new Todo item in the database with status, description, and due_at."""
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
        status=todo_data.status or TodoStatus.CREATED,
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


ALLOWED_SORT_FIELDS = {"id", "title", "due_at", "created_at", "updated_at"}
ALLOWED_SORT_DIRECTIONS = {"asc", "desc"}


def get_todos(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    sort: str = "created_at:desc",
) -> tuple[Sequence[Todo], bool]:
    """Retrieve paginated Todo items with deterministic sorting and limit+1 next-page detection.

    Returns a tuple of (items, has_next_page).
    """
    if page < 1 or page > 100:
        raise ValueError("page must be between 1 and 100")
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100")

    if ":" not in sort:
        raise ValueError("Invalid sort format. Expected '<field>:<direction>'")

    field, direction = sort.split(":", 1)
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

    stmt = select(Todo)
    column_attr = getattr(Todo, field)
    sort_func = getattr(column_attr, direction)

    if field == "id":
        stmt = stmt.order_by(sort_func())
    else:
        id_sort_func = getattr(Todo.id, direction)
        stmt = stmt.order_by(sort_func(), id_sort_func())

    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page + 1)

    results = db.scalars(stmt).all()
    has_next_page = len(results) > per_page
    items = results[:per_page]

    return items, has_next_page


def get_todo_by_id(db: Session, todo_id: int) -> Todo | None:
    """Retrieve a single Todo item by its ID."""
    stmt = select(Todo).where(Todo.id == todo_id)
    return db.scalars(stmt).first()


def update_todo(db: Session, todo_id: int, todo_data: TodoUpdate) -> Todo | None:
    """Update an existing Todo item's title, description, status, or due_at."""
    todo = get_todo_by_id(db, todo_id)
    if todo is None:
        return None

    if todo_data.title is not None:
        todo.title = todo_data.title
    if todo_data.description is not None or "description" in todo_data.model_fields_set:
        todo.description = todo_data.description
    if todo_data.status is not None:
        todo.status = todo_data.status
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
