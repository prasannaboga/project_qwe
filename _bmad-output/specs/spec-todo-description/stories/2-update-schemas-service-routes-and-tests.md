---
title: 'Update schemas, service layer, API routes, and automated test suite'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_commit: 'e6a5f644a72ae10a24e2845705bb44e15b57acc9'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Pydantic schemas, service layer, and API endpoints do not accept, validate, process, or return the new `description` field, leaving the database capability inaccessible to clients.

**Approach:** Update `schemas/todo.py` with 1000-char validation, update `services/todo_service.py` to handle creation, updating, and clearing of description, and add full test coverage across service and API layers.

## Boundaries & Constraints

**Always:**
- Strictly maintain the 4-tier layered architecture: route handlers in `api/todos.py` remain thin delegates; all CRUD and business logic resides in `services/todo_service.py`.
- Enforce `max_length=1000` on `description` in Pydantic schemas, returning HTTP 422 Unprocessable Entity when exceeded.
- Preserve backward compatibility: requests omitting `description` must succeed with `description: null`.
- Passing explicit `null` for `description` on update must clear the existing description in the database.

**Ask First:**
- Any change to existing endpoint URLs or core HTTP status codes.

**Never:**
- Never execute database queries or mutations directly inside route handlers.
- Never hardcode or alter existing non-description validation rules.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| POST /todos with valid description | `{"title": "Task", "description": "Details"}` | HTTP 201 with `description == "Details"` | N/A |
| POST /todos omitting description | `{"title": "Task"}` | HTTP 201 with `description == null` | N/A |
| POST /todos with description > 1000 chars | `{"title": "Task", "description": "a" * 1001}` | HTTP 422 Unprocessable Entity | Pydantic validation error |
| GET /todos & GET /todos/{id} | Record with description | HTTP 200 with `description` populated | N/A |
| PUT /todos/{id} update description | `{"description": "New text"}` | HTTP 200 with `description == "New text"` | 404 if not found |
| PUT /todos/{id} clear description | `{"description": null}` | HTTP 200 with `description == null` | 404 if not found |

</frozen-after-approval>

## Code Map

- `src/project_qwe/schemas/todo.py` -- Update `TodoBase`, `TodoCreate`, `TodoUpdate`, and `TodoResponse` with optional `description` field (`max_length=1000`).
- `src/project_qwe/services/todo_service.py` -- Pass `description` in `create_todo` and handle updates/clearing in `update_todo`.
- `src/project_qwe/api/todos.py` -- Confirm route handlers serialize `TodoResponse` with `description`.
- `tests/services/test_todo_service.py` -- Unit tests for service layer description create, update, and clear.
- `tests/api/test_todos.py` -- Integration tests for API endpoints with description, nulls, and boundary validation.

## Tasks & Acceptance

**Execution:**
- [x] `src/project_qwe/schemas/todo.py` -- Add `description: str | None = Field(default=None, max_length=1000, ...)` to `TodoBase`, `TodoUpdate`, and `TodoResponse`.
- [x] `src/project_qwe/services/todo_service.py` -- Update `create_todo` and `update_todo` to persist and update/clear `description`.
- [x] `tests/services/test_todo_service.py` -- Add unit tests for description CRUD and fix any legacy status references to `TodoStatus.INPROGRESS`.
- [x] `tests/api/test_todos.py` -- Add endpoint tests for description (valid, omitted, null update, and >1000 char validation) and fix legacy status references.

**Acceptance Criteria:**
- Given a `TodoCreate` payload with `description`, when calling `POST /todos`, then the response is HTTP 201 containing the description.
- Given a `TodoCreate` payload with `description` exceeding 1000 chars, when calling `POST /todos`, then HTTP 422 is returned.
- Given an existing todo with a description, when sending `PUT /todos/{id}` with `{"description": null}`, then the description is cleared to `null`.
- Given the full test suite, when running `uv run pytest`, then 100% of tests pass.

## Spec Change Log

## Design Notes

Pydantic schema updates in `src/project_qwe/schemas/todo.py`:
```python
class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the todo item")
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed description for the todo item",
    )
    status: TodoStatus = Field(default=TodoStatus.CREATED, ...)
    due_at: datetime | None = Field(default=None, ...)
```

In `src/project_qwe/services/todo_service.py`:
```python
if todo_data.description is not None or "description" in todo_data.model_fields_set:
    todo.description = todo_data.description
```

## Verification

**Commands:**
- `uv run pytest` -- expected: All unit and API tests pass.

## Suggested Review Order

**Schemas & Data Validation**

- Add optional 1000-character description field across TodoBase, TodoUpdate, and TodoResponse
  [`todo.py:10`](../../../../src/project_qwe/schemas/todo.py#L10)

**Service Layer Business Logic**

- Persist description on creation and support partial update and explicit clearing to null
  [`todo_service.py:14`](../../../../src/project_qwe/services/todo_service.py#L14)

**Automated Tests**

- Service unit tests for create, update, and clear description
  [`test_todo_service.py:20`](../../../../tests/services/test_todo_service.py#L20)

- API route integration tests for description payloads, nulls, and 1000-char boundary validation
  [`test_todos.py:18`](../../../../tests/api/test_todos.py#L18)

