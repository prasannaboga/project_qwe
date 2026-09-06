from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from project_qwe.models.todo import TodoStatus
from project_qwe.schemas.todo import TodoCreate, TodoUpdate
from project_qwe.services import todo_service


def test_create_todo_defaults(db_session: Session) -> None:
    todo = todo_service.create_todo(db_session, TodoCreate(title="Test Todo"))
    assert todo.id is not None
    assert todo.title == "Test Todo"
    assert todo.description is None
    assert todo.status == TodoStatus.CREATED
    assert todo.due_at is None
    assert todo.created_at is not None
    assert todo.updated_at is not None


def test_create_todo_with_description(db_session: Session) -> None:
    todo = todo_service.create_todo(
        db_session,
        TodoCreate(
            title="Task with description",
            description="Detailed notes for the task",
        ),
    )
    assert todo.id is not None
    assert todo.title == "Task with description"
    assert todo.description == "Detailed notes for the task"


def test_create_todo_with_status_and_due(db_session: Session) -> None:
    due = datetime(2026, 8, 20, 18, 0, 0, tzinfo=timezone.utc)
    todo = todo_service.create_todo(
        db_session,
        TodoCreate(title="Test Todo with due", status=TodoStatus.INPROGRESS, due_at=due),
    )
    assert todo.id is not None
    assert todo.title == "Test Todo with due"
    assert todo.status == TodoStatus.INPROGRESS
    assert todo.due_at is not None


def test_get_todos(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Task A", description="Desc A"))
    todo_service.create_todo(db_session, TodoCreate(title="Task B", status=TodoStatus.COMPLETED))

    todos, has_next_page = todo_service.get_todos(db_session, page=1, per_page=20, sort="created_at:desc")
    assert len(todos) == 2
    assert has_next_page is False
    assert todos[0].title == "Task B"
    assert todos[1].title == "Task A"


def test_get_todos_pagination_limit_plus_one(db_session: Session) -> None:
    for i in range(5):
        todo_service.create_todo(db_session, TodoCreate(title=f"Task {i}"))

    page1, has_next = todo_service.get_todos(db_session, page=1, per_page=3, sort="id:asc")
    assert len(page1) == 3
    assert has_next is True
    assert [t.title for t in page1] == ["Task 0", "Task 1", "Task 2"]

    page2, has_next = todo_service.get_todos(db_session, page=2, per_page=3, sort="id:asc")
    assert len(page2) == 2
    assert has_next is False
    assert [t.title for t in page2] == ["Task 3", "Task 4"]


def test_get_todos_sorting_and_tie_breaking(db_session: Session) -> None:
    due = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    t1 = todo_service.create_todo(db_session, TodoCreate(title="Z Task", due_at=due))
    t2 = todo_service.create_todo(db_session, TodoCreate(title="A Task", due_at=due))

    # Same due_at, secondary tie breaker on ID ASC
    todos, _ = todo_service.get_todos(db_session, sort="due_at:asc")
    assert todos[0].id == t1.id
    assert todos[1].id == t2.id

    # Secondary tie breaker on ID DESC
    todos_desc, _ = todo_service.get_todos(db_session, sort="due_at:desc")
    assert todos_desc[0].id == t2.id
    assert todos_desc[1].id == t1.id


def test_get_todos_invalid_parameters(db_session: Session) -> None:
    with pytest.raises(ValueError, match="page must be between 1 and 100"):
        todo_service.get_todos(db_session, page=0)

    with pytest.raises(ValueError, match="per_page must be between 1 and 100"):
        todo_service.get_todos(db_session, per_page=101)

    with pytest.raises(ValueError, match="Invalid sort format"):
        todo_service.get_todos(db_session, sort="invalid_format")

    with pytest.raises(ValueError, match="Invalid sort field"):
        todo_service.get_todos(db_session, sort="nonexistent_field:asc")

    with pytest.raises(ValueError, match="Invalid sort direction"):
        todo_service.get_todos(db_session, sort="title:sideways")


def test_get_todo_by_id(db_session: Session) -> None:
    created = todo_service.create_todo(
        db_session,
        TodoCreate(title="Specific Task", description="Detailed description", status=TodoStatus.INPROGRESS),
    )
    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Specific Task"
    assert fetched.description == "Detailed description"
    assert fetched.status == TodoStatus.INPROGRESS

    not_found = todo_service.get_todo_by_id(db_session, 9999)
    assert not_found is None


def test_update_todo(db_session: Session) -> None:
    created = todo_service.create_todo(
        db_session, TodoCreate(title="Old Task", description="Old description")
    )
    due = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated = todo_service.update_todo(
        db_session,
        created.id,
        TodoUpdate(
            title="New Task",
            description="New description",
            status=TodoStatus.COMPLETED,
            due_at=due,
        ),
    )
    assert updated is not None
    assert updated.title == "New Task"
    assert updated.description == "New description"
    assert updated.status == TodoStatus.COMPLETED
    assert updated.due_at is not None
    assert updated.due_at.year == 2026
    assert updated.due_at.month == 9
    assert updated.due_at.day == 1


def test_update_todo_clear_description(db_session: Session) -> None:
    created = todo_service.create_todo(
        db_session, TodoCreate(title="Task to clear", description="Will be cleared")
    )
    assert created.description == "Will be cleared"

    updated = todo_service.update_todo(
        db_session,
        created.id,
        TodoUpdate(description=None),
    )
    assert updated is not None
    assert updated.description is None


def test_delete_todo(db_session: Session) -> None:
    created = todo_service.create_todo(db_session, TodoCreate(title="To Delete"))
    deleted = todo_service.delete_todo(db_session, created.id)
    assert deleted is True

    fetched = todo_service.get_todo_by_id(db_session, created.id)
    assert fetched is None

    not_found = todo_service.delete_todo(db_session, 9999)
    assert not_found is False
