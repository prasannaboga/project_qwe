from datetime import datetime, timezone
from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo, TodoStatus


def test_todo_model_attributes(db_session: Session) -> None:
    due = datetime(2026, 8, 20, 18, 0, 0, tzinfo=timezone.utc)
    todo = Todo(title="Model Test", status=TodoStatus.PROCESS, due_at=due)
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.id is not None
    assert todo.title == "Model Test"
    assert todo.status == TodoStatus.PROCESS
    assert todo.due_at is not None
    assert todo.created_at is not None
    assert todo.updated_at is not None
    assert str(todo.__tablename__) == "todos"
