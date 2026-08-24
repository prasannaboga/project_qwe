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


def get_todos(db: Session) -> Sequence[Todo]:
    """Retrieve all Todo items ordered by ID."""
    stmt = select(Todo).order_by(Todo.id)
    return db.scalars(stmt).all()


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
