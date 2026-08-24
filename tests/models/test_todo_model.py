from datetime import datetime, timezone
from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo, TodoStatus


def test_todo_model_attributes(db_session: Session) -> None:
    due = datetime(2026, 8, 20, 18, 0, 0, tzinfo=timezone.utc)
    todo = Todo(
        title="Model Test",
        description="Detailed description for model test",
        status=TodoStatus.INPROGRESS,
        due_at=due,
    )
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.id is not None
    assert todo.title == "Model Test"
    assert todo.description == "Detailed description for model test"
    assert todo.status == TodoStatus.INPROGRESS
    assert todo.due_at is not None
    assert todo.created_at is not None
    assert todo.updated_at is not None
    assert str(todo.__tablename__) == "todos"


def test_todo_model_description_default_none(db_session: Session) -> None:
    todo = Todo(title="Model Test Without Description")
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.id is not None
    assert todo.title == "Model Test Without Description"
    assert todo.description is None
    assert todo.status == TodoStatus.CREATED
    assert todo.due_at is None


def test_todo_model_update_and_clear_description(db_session: Session) -> None:
    todo = Todo(title="Initial Task", description="Initial description")
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.description == "Initial description"

    # Update description
    todo.description = "Updated description"
    db_session.commit()
    db_session.refresh(todo)
    assert todo.description == "Updated description"

    # Clear description
    todo.description = None
    db_session.commit()
    db_session.refresh(todo)
    assert todo.description is None


