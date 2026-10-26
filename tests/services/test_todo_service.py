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

    with pytest.raises(ValueError, match="Invalid sort token"):
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


def test_update_todo_priority(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    created = todo_service.create_todo(
        db_session, TodoCreate(title="Priority task", priority=TodoPriority.LOW)
    )
    assert created.priority == TodoPriority.LOW

    updated = todo_service.update_todo(
        db_session, created.id, TodoUpdate(priority=TodoPriority.URGENT)
    )
    assert updated is not None
    assert updated.priority == TodoPriority.URGENT
    assert updated.title == "Priority task"


def test_update_todo_priority_none_preserves_existing(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    created = todo_service.create_todo(
        db_session, TodoCreate(title="Priority preserve task", priority=TodoPriority.HIGH)
    )
    assert created.priority == TodoPriority.HIGH

    updated = todo_service.update_todo(
        db_session, created.id, TodoUpdate(title="Updated title only", priority=None)
    )
    assert updated is not None
    assert updated.priority == TodoPriority.HIGH
    assert updated.title == "Updated title only"


def test_get_todos_filtered_by_priority(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    todo_service.create_todo(db_session, TodoCreate(title="Urgent 1", priority=TodoPriority.URGENT))
    todo_service.create_todo(db_session, TodoCreate(title="High 1", priority=TodoPriority.HIGH))
    todo_service.create_todo(db_session, TodoCreate(title="Low 1", priority=TodoPriority.LOW))

    urgent_todos, has_next = todo_service.get_todos(db_session, priority=TodoPriority.URGENT)
    assert len(urgent_todos) == 1
    assert urgent_todos[0].title == "Urgent 1"
    assert urgent_todos[0].priority == TodoPriority.URGENT
    assert has_next is False


def test_get_todos_priority_none_returns_all(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    todo_service.create_todo(db_session, TodoCreate(title="Urgent 1", priority=TodoPriority.URGENT))
    todo_service.create_todo(db_session, TodoCreate(title="High 1", priority=TodoPriority.HIGH))
    todo_service.create_todo(db_session, TodoCreate(title="Low 1", priority=TodoPriority.LOW))

    all_todos, _ = todo_service.get_todos(db_session, priority=None)
    assert len(all_todos) == 3




# ---------------------------------------------------------------------------
# search_todos tests
# ---------------------------------------------------------------------------

def test_search_todos_title_match(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    todo_service.create_todo(db_session, TodoCreate(title="Buy groceries", priority=TodoPriority.HIGH))
    todo_service.create_todo(db_session, TodoCreate(title="Call dentist"))
    todo_service.create_todo(db_session, TodoCreate(title="Buy flowers"))

    results = todo_service.search_todos(db_session, query="buy")
    assert len(results) == 2
    titles = {t.title for t in results}
    assert "Buy groceries" in titles
    assert "Buy flowers" in titles


def test_search_todos_description_match(db_session: Session) -> None:
    todo_service.create_todo(
        db_session,
        TodoCreate(title="Sprint planning", description="Discuss database migration strategy"),
    )
    todo_service.create_todo(db_session, TodoCreate(title="Code review"))

    results = todo_service.search_todos(db_session, query="migration")
    assert len(results) == 1
    assert results[0].title == "Sprint planning"


def test_search_todos_case_insensitive(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="URGENT: Fix production bug"))

    upper_results = todo_service.search_todos(db_session, query="urgent")
    lower_results = todo_service.search_todos(db_session, query="URGENT")
    assert len(upper_results) == 1
    assert len(lower_results) == 1


def test_search_todos_no_match(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Simple task"))

    results = todo_service.search_todos(db_session, query="xyznotfound")
    assert len(results) == 0


def test_search_todos_empty_query_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        todo_service.search_todos(db_session, query="")

    with pytest.raises(ValueError, match="query must not be empty"):
        todo_service.search_todos(db_session, query="   ")


def test_search_todos_limit_bounds(db_session: Session) -> None:
    with pytest.raises(ValueError, match="limit must be between 1 and 20"):
        todo_service.search_todos(db_session, query="test", limit=0)

    with pytest.raises(ValueError, match="limit must be between 1 and 20"):
        todo_service.search_todos(db_session, query="test", limit=21)


def test_search_todos_respects_limit(db_session: Session) -> None:
    for i in range(10):
        todo_service.create_todo(db_session, TodoCreate(title=f"Task {i} with keyword"))

    results = todo_service.search_todos(db_session, query="keyword", limit=3)
    assert len(results) == 3


def test_search_todos_ordered_by_updated_at_desc(db_session: Session) -> None:
    t1 = todo_service.create_todo(db_session, TodoCreate(title="Old keyword task"))
    t2 = todo_service.create_todo(db_session, TodoCreate(title="New keyword task"))
    # Update t1 so it has a newer updated_at
    from project_qwe.schemas.todo import TodoUpdate as _TU
    todo_service.update_todo(db_session, t1.id, _TU(title="Refreshed keyword task"))

    results = todo_service.search_todos(db_session, query="keyword")
    # t1 (now refreshed) should appear before t2
    assert results[0].id == t1.id


# ---------------------------------------------------------------------------
# compound sort / priority urgency tests
# ---------------------------------------------------------------------------

def test_get_todos_compound_sort_due_at_asc_priority_desc(db_session: Session) -> None:
    from datetime import timezone
    from project_qwe.models.todo import TodoPriority
    due_soon = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    due_late = datetime(2026, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

    t_urgent_late = todo_service.create_todo(
        db_session, TodoCreate(title="Urgent late", priority=TodoPriority.URGENT, due_at=due_late)
    )
    t_high_soon = todo_service.create_todo(
        db_session, TodoCreate(title="High soon", priority=TodoPriority.HIGH, due_at=due_soon)
    )
    t_urgent_soon = todo_service.create_todo(
        db_session, TodoCreate(title="Urgent soon", priority=TodoPriority.URGENT, due_at=due_soon)
    )

    todos, _ = todo_service.get_todos(db_session, sort="due_at:asc,priority:desc")
    # Both t_urgent_soon and t_high_soon have due_soon; urgent > high so urgent first
    assert todos[0].id == t_urgent_soon.id
    assert todos[1].id == t_high_soon.id
    # t_urgent_late has due_late so it comes last
    assert todos[2].id == t_urgent_late.id


def test_get_todos_due_at_asc_nulls_last(db_session: Session) -> None:
    from datetime import timezone

    due = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_no_due = todo_service.create_todo(db_session, TodoCreate(title="No due date"))
    t_with_due = todo_service.create_todo(db_session, TodoCreate(title="Has due date", due_at=due))

    todos, _ = todo_service.get_todos(db_session, sort="due_at:asc")
    assert todos[0].id == t_with_due.id
    assert todos[1].id == t_no_due.id


def test_get_todos_priority_urgency_sort_desc(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    todo_service.create_todo(db_session, TodoCreate(title="Low", priority=TodoPriority.LOW))
    todo_service.create_todo(db_session, TodoCreate(title="Urgent", priority=TodoPriority.URGENT))
    todo_service.create_todo(db_session, TodoCreate(title="Medium", priority=TodoPriority.MEDIUM))
    todo_service.create_todo(db_session, TodoCreate(title="High", priority=TodoPriority.HIGH))

    todos, _ = todo_service.get_todos(db_session, sort="priority:desc")
    priority_order = [t.priority.value for t in todos]
    assert priority_order == ["urgent", "high", "medium", "low"]


def test_get_todos_priority_sort_asc(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority
    todo_service.create_todo(db_session, TodoCreate(title="Low", priority=TodoPriority.LOW))
    todo_service.create_todo(db_session, TodoCreate(title="Urgent", priority=TodoPriority.URGENT))
    todo_service.create_todo(db_session, TodoCreate(title="Medium", priority=TodoPriority.MEDIUM))
    todo_service.create_todo(db_session, TodoCreate(title="High", priority=TodoPriority.HIGH))

    todos, _ = todo_service.get_todos(db_session, sort="priority:asc")
    priority_order = [t.priority.value for t in todos]
    assert priority_order == ["low", "medium", "high", "urgent"]


def test_get_todos_compound_sort_invalid_token(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Invalid sort token"):
        todo_service.get_todos(db_session, sort="nocolon")

    with pytest.raises(ValueError, match="Invalid sort field"):
        todo_service.get_todos(db_session, sort="badfield:asc")


def test_search_todos_wildcards_escaped(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Discount 50% off"))
    todo_service.create_todo(db_session, TodoCreate(title="Discount 500 off"))
    todo_service.create_todo(db_session, TodoCreate(title="Item_1 test"))
    todo_service.create_todo(db_session, TodoCreate(title="ItemA1 test"))

    # Literal % should match only "Discount 50% off", not "Discount 500 off"
    percent_results = todo_service.search_todos(db_session, query="50%")
    assert len(percent_results) == 1
    assert percent_results[0].title == "Discount 50% off"

    # Literal _ should match only "Item_1 test", not "ItemA1 test"
    underscore_results = todo_service.search_todos(db_session, query="Item_1")
    assert len(underscore_results) == 1
    assert underscore_results[0].title == "Item_1 test"


def test_get_active_todos_filters_completed(db_session: Session) -> None:
    todo_service.create_todo(db_session, TodoCreate(title="Active 1", status=TodoStatus.CREATED))
    todo_service.create_todo(db_session, TodoCreate(title="Active 2", status=TodoStatus.INPROGRESS))
    todo_service.create_todo(db_session, TodoCreate(title="Done", status=TodoStatus.COMPLETED))

    active = todo_service.get_active_todos(db_session)
    titles = [t.title for t in active]
    assert "Active 1" in titles
    assert "Active 2" in titles
    assert "Done" not in titles


def test_get_active_todos_priority_filter(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority

    todo_service.create_todo(db_session, TodoCreate(title="Urgent 1", priority=TodoPriority.URGENT))
    todo_service.create_todo(db_session, TodoCreate(title="Low 1", priority=TodoPriority.LOW))
    todo_service.create_todo(db_session, TodoCreate(title="Urgent Done", priority=TodoPriority.URGENT, status=TodoStatus.COMPLETED))

    urgent_items = todo_service.get_active_todos(db_session, priority=TodoPriority.URGENT)
    assert len(urgent_items) == 1
    assert urgent_items[0].title == "Urgent 1"

    # Test case-insensitive string priority filter
    urgent_by_str = todo_service.get_active_todos(db_session, priority="urgent")
    assert len(urgent_by_str) == 1
    assert urgent_by_str[0].title == "Urgent 1"


def test_get_active_todos_sorting(db_session: Session) -> None:
    from datetime import timedelta
    from project_qwe.models.todo import TodoPriority

    now = datetime.now(timezone.utc)
    # Earlier due date
    t1 = todo_service.create_todo(
        db_session,
        TodoCreate(title="Earlier due", due_at=now + timedelta(days=1), priority=TodoPriority.LOW),
    )
    # Later due date
    t2 = todo_service.create_todo(
        db_session,
        TodoCreate(title="Later due", due_at=now + timedelta(days=5), priority=TodoPriority.URGENT),
    )
    # No due date (nulls last) but urgent
    t3 = todo_service.create_todo(
        db_session,
        TodoCreate(title="No due date", due_at=None, priority=TodoPriority.URGENT),
    )

    items = todo_service.get_active_todos(db_session)
    ids = [t.id for t in items]
    # Earlier due date comes first, then later due date, then null due_at last
    assert ids == [t1.id, t2.id, t3.id]


def test_get_todo_summary_and_markdown(db_session: Session) -> None:
    from datetime import timedelta
    from project_qwe.models.todo import TodoPriority

    now = datetime.now(timezone.utc)
    # 1 Created, High, Overdue
    overdue_task = todo_service.create_todo(
        db_session,
        TodoCreate(
            title="Overdue task",
            status=TodoStatus.CREATED,
            priority=TodoPriority.HIGH,
            due_at=now - timedelta(days=2),
        ),
    )
    # 1 In Progress, Medium, Future
    todo_service.create_todo(
        db_session,
        TodoCreate(
            title="Future task",
            status=TodoStatus.INPROGRESS,
            priority=TodoPriority.MEDIUM,
            due_at=now + timedelta(days=2),
        ),
    )
    # 1 Completed, Urgent, Past (must NOT be counted in overdue_items because completed)
    todo_service.create_todo(
        db_session,
        TodoCreate(
            title="Completed past task",
            status=TodoStatus.COMPLETED,
            priority=TodoPriority.URGENT,
            due_at=now - timedelta(days=3),
        ),
    )

    summary_data = todo_service.get_todo_summary(db_session)
    assert summary_data["total"] == 3
    assert summary_data["status_counts"][TodoStatus.CREATED] == 1
    assert summary_data["status_counts"][TodoStatus.INPROGRESS] == 1
    assert summary_data["status_counts"][TodoStatus.COMPLETED] == 1
    assert summary_data["priority_counts"][TodoPriority.HIGH] == 1
    assert summary_data["priority_counts"][TodoPriority.MEDIUM] == 1
    assert summary_data["priority_counts"][TodoPriority.URGENT] == 1

    overdue_items = summary_data["overdue_items"]
    assert len(overdue_items) == 1
    assert overdue_items[0].id == overdue_task.id

    md = todo_service.get_todo_summary_markdown(db_session)
    assert "# Todo Summary" in md
    assert "## Status" in md
    assert "- Created: 1" in md
    assert "- In Progress: 1" in md
    assert "- Completed: 1" in md
    assert "- Total: 3" in md
    assert "## Priority" in md
    assert "- High: 1" in md
    assert "## Overdue Items" in md
    assert f"- #{overdue_task.id}: Overdue task" in md

    # Verify when no items are overdue
    empty_summary_md = todo_service.get_todo_summary_markdown(db_session)
    # Clear overdue tasks
    todo_service.delete_todo(db_session, overdue_task.id)
    no_overdue_md = todo_service.get_todo_summary_markdown(db_session)
    assert "- None" in no_overdue_md


def test_get_backlog_todos(db_session: Session) -> None:
    from project_qwe.models.todo import TodoPriority

    # Create backlog items (CREATED) with varying priorities
    b_low = todo_service.create_todo(db_session, TodoCreate(title="Backlog Low", priority=TodoPriority.LOW, status=TodoStatus.CREATED))
    b_urgent = todo_service.create_todo(db_session, TodoCreate(title="Backlog Urgent", priority=TodoPriority.URGENT, status=TodoStatus.CREATED))
    b_high = todo_service.create_todo(db_session, TodoCreate(title="Backlog High", priority=TodoPriority.HIGH, status=TodoStatus.CREATED))

    # Create non-backlog items (INPROGRESS, COMPLETED)
    todo_service.create_todo(db_session, TodoCreate(title="Inprogress item", status=TodoStatus.INPROGRESS))
    todo_service.create_todo(db_session, TodoCreate(title="Completed item", status=TodoStatus.COMPLETED))

    backlog = todo_service.get_backlog_todos(db_session, limit=10)
    assert len(backlog) == 3
    # Check ordering: urgent > high > low
    assert [b.id for b in backlog] == [b_urgent.id, b_high.id, b_low.id]

    # Test limit clamping
    limited = todo_service.get_backlog_todos(db_session, limit=2)
    assert len(limited) == 2
    assert [b.id for b in limited] == [b_urgent.id, b_high.id]

    # Test limit bounds validation
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        todo_service.get_backlog_todos(db_session, limit=0)
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        todo_service.get_backlog_todos(db_session, limit=51)

