---
title: 'Add description column to Todo model and create Alembic migration'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_commit: '279d5463e72c451607acf92d5df3cf40d0b23253'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The `Todo` model currently lacks a `description` field, preventing persistent storage of task notes and detailed context.

**Approach:** Add an optional, nullable `description` column (`String(1000)`) to the `Todo` ORM model and create a new forward-only Alembic migration to update the database schema.

## Boundaries & Constraints

**Always:**
- Use a new forward-only Alembic migration revision; never modify existing migration files (`91db0bbf0fd7`, `9372e3b3c98f`).
- `description` column must be nullable (`nullable=True`, `default=None`) and type `String(1000)` in SQLAlchemy.
- Ensure existing rows default to NULL without requiring data backfills.

**Ask First:**
- Any change to existing model fields or column types.

**Never:**
- Do not modify existing migrations.
- Do not instantiate database sessions inside ORM models.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Instantiate Todo with description | `Todo(title="Task", description="Some details")` | Instance created with `description == "Some details"` | N/A |
| Instantiate Todo without description | `Todo(title="Task")` | Instance created with `description is None` | N/A |
| Database migration upgrade | `uv run alembic upgrade head` | `todos` table has `description VARCHAR(1000)` column nullable | N/A |
| Database migration downgrade | `uv run alembic downgrade -1` | `description` column dropped cleanly | N/A |

</frozen-after-approval>

## Code Map

- `src/project_qwe/models/todo.py` -- Add `description: Mapped[str | None] = mapped_column(String(1000), nullable=True, default=None)` to `Todo` model.
- `migrations/versions/` -- New generated Alembic migration revision adding `description` column.
- `tests/models/test_todo_model.py` -- Unit tests verifying `Todo` model instantiation and attributes with and without `description`.

## Tasks & Acceptance

**Execution:**
- [x] `src/project_qwe/models/todo.py` -- Add `description` column (`String(1000)`, `nullable=True`, `default=None`) to `Todo` ORM model.
- [x] `migrations/versions/` -- Generate new Alembic migration using `uv run alembic revision --autogenerate -m "add description to todos"` and apply with `uv run alembic upgrade head`.
- [x] `tests/models/test_todo_model.py` -- Update model tests to assert `description` attribute persistence and nullable defaults.

**Acceptance Criteria:**
- Given a `Todo` model instance initialized with a `description` string under 1000 chars, when persisted or inspected, then `todo.description` matches the provided string.
- Given a `Todo` model instance initialized without `description`, when persisted or inspected, then `todo.description` is `None`.
- Given the Alembic migration history, when running `uv run alembic upgrade head`, then the `todos` table in SQLite successfully includes the nullable `description` column.

## Spec Change Log

## Design Notes

Column definition in `src/project_qwe/models/todo.py`:
```python
description: Mapped[str | None] = mapped_column(
    String(1000),
    nullable=True,
    default=None,
)
```

## Verification

**Commands:**
- `uv run alembic upgrade head` -- expected: Database schema upgraded to head successfully.
- `uv run pytest tests/models/test_todo_model.py` -- expected: Model tests pass.

## Suggested Review Order

**Database Model & Migration**

- Add optional 1000-character description column to Todo ORM entity
  [`todo.py:21`](../../../../src/project_qwe/models/todo.py#L21)

- Forward-only Alembic migration using batch_alter_table for SQLite compatibility
  [`2066bdd2fb23_add_description_to_todos.py:20`](../../../../migrations/versions/2066bdd2fb23_add_description_to_todos.py#L20)

**Unit Tests**

- Assert description persistence, nullable default, and update/clear behavior
  [`test_todo_model.py:7`](../../../../tests/models/test_todo_model.py#L7)

