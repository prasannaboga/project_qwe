from datetime import datetime, timezone
from sqlalchemy.orm import Session

from project_qwe.models.todo import TodoStatus
from project_qwe.schemas.todo import TodoCreate, TodoUpdate
from project_qwe.services import todo_service


def test_create_todo_defaults(db_session: Session) -> None:
    todo = todo_service.create_todo(db_session, TodoCreate(title="Test Todo"))
    assert todo.id is not None
    assert todo.title == "Test Todo"
    assert todo.status == TodoStatus.CREATED
    assert todo.due_at is None
    assert todo.created_at is not None
    assert todo.updated_at is not None


def test_create_todo_with_status_and_due(db_session: Session) -> None:
    due = datetime(2026, 8, 20, 18, 0, 0, tzinfo=timezone.utc)
    todo = todo_service.create_todo(
        db_session,
        TodoCreate(title="Test Todo with due", status=TodoStatus.PROCESS, due_at=due),
    )
    assert todo.id is not None
    assert todo.title == "Test Todo with due"
    assert todo.status == TodoStatus.PROCESS
    assert todo.due_at is not None


def test_get_todos(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Task A"))
    todo_service.create_todo(db_session, TodoCreate(title="Task B", status=TodoStatus.COMPLETED))

    todos = todo_service.get_todos(db_session)
    assert len(todos) == 2
    assert todos[0].title == "Task A"
    assert todos[0].status == TodoStatus.CREATED
    assert todos[1].title == "Task B"
    assert todos[1].status == TodoStatus.COMPLETED


def test_get_todo_by_id(db_session: Session) -> None:
    created = todo_service.create_todo(
        db_session, TodoCreate(title="Specific Task", status=TodoStatus.PROCESS)
    )
    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Specific Task"
    assert fetched.status == TodoStatus.PROCESS

    not_found = todo_service.get_todo_by_id(db_session, 9999)
    assert not_found is None


def test_update_todo(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="Old Task"))
    due = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated = todo_service.update_todo(
        db_session,
        created.id,
        TodoUpdate(title="New Task", status=TodoStatus.COMPLETED, due_at=due),
    )
    assert updated is not None
    assert updated.title == "New Task"
    assert updated.status == TodoStatus.COMPLETED
    assert updated.due_at is not None
    assert updated.due_at.year == 2026
    assert updated.due_at.month == 9
    assert updated.due_at.day == 1


def test_delete_todo(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="To Delete"))
    deleted = todo_service.delete_todo(db_session, created.id)
    assert deleted is True

    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is None

    not_found = todo_service.delete_todo(db_session, 9999)
    assert not_found is False
