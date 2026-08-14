from sqlalchemy.orm import Session

from project_qwe.models.todo import Todo


def test_todo_model_attributes(db_session: Session) -> None:
    todo = Todo(title="Model Test")
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.id is not None
    assert todo.title == "Model Test"
    assert todo.created_at is not None
    assert todo.updated_at is not None
    assert str(todo.__tablename__) == "todos"
