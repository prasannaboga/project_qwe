from sqlalchemy.orm import Session

from project_qwe.schemas.todo import TodoCreate, TodoUpdate
from project_qwe.services import todo_service


def test_create_todo(db_session: Session) -> None:
    todo = todo_service.create_todo(db_session, TodoCreate(title="Test Todo"))
    assert todo.id is not None
    assert todo.title == "Test Todo"
    assert todo.created_at is not None
    assert todo.updated_at is not None


def test_get_todos(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Task A"))
    todo_service.create_todo(db_session, TodoCreate(title="Task B"))

    todos = todo_service.get_todos(db_session)
    assert len(todos) == 2
    assert todos[0].title == "Task A"
    assert todos[1].title == "Task B"


def test_get_todo_by_id(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="Specific Task"))
    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Specific Task"

    not_found = todo_service.get_todo_by_id(db_session, 9999)
    assert not_found is None


def test_update_todo(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="Old Task"))
    updated = todo_service.update_todo(
        db_session, created.id, TodoUpdate(title="New Task")
    )
    assert updated is not None
    assert updated.title == "New Task"

    not_found = todo_service.update_todo(
        db_session, 9999, TodoUpdate(title="Nonexistent")
    )
    assert not_found is None


def test_delete_todo(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="To Delete"))
    deleted = todo_service.delete_todo(db_session, created.id)
    assert deleted is True

    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is None

    not_found = todo_service.delete_todo(db_session, 9999)
    assert not_found is False
