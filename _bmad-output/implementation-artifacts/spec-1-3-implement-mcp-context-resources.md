---
title: 'Story 1.3: Implement MCP Context Resources'
type: 'feature'
created: '2026-10-18'
status: 'in-progress'
baseline_revision: '49c320be989fdc9012a66be1a1606846ee9fe458'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/implementation-artifacts/epic-1-context.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Autonomous AI clients lack direct, read-only contextual feeds to inspect active tasks, overdue items, and task priorities over the Model Context Protocol without invoking transactional tools or parsing ad-hoc formats.

**Approach:** Implement and register the four MCP context resources (`todo://items`, `todo://items/{id}`, `todo://summary`, `todo://priorities/{priority}`) in `src/project_qwe/mcp/todos/resources.py` backed by new query methods in `src/project_qwe/services/todo_service.py` using operation-scoped database sessions.

## Boundaries & Constraints

**Always:**
- Strictly delegate all database queries and aggregation logic to `src/project_qwe/services/todo_service.py` (AD-1, FR-5).
- Never import SQLAlchemy ORM models from `src/project_qwe/models/` into `src/project_qwe/mcp/`; import all schemas and enums from `src/project_qwe/schemas/todo.py` (AD-1).
- Acquire database sessions within operation-scoped context managers `with SessionLocal() as db:` closing the session immediately after reading the resource (FR-4, AD-3).
- Register resources with the official Python MCP SDK using `@mcp_server.resource(...)` decorators, using `ResourceNotFoundError` and `ResourceError` for error scenarios.
- Keep the SSE sub-application mounted at `/mcp/todos` in FastAPI and ensure `src/project_qwe/mcp/todos/server.py` imports `resources` so registrations take effect upon server load.

**Block If:**
- MCP SDK resource template URI syntax requires breaking changes to FastAPI or Starlette routing.
- Schema modifications require changes to existing applied database migrations.

**Never:**
- Import or query SQLAlchemy ORM models directly inside `src/project_qwe/mcp/` (AD-1).
- Keep open database sessions across SSE client connection lifetimes.
- Return raw exception tracebacks to MCP clients; handle missing or invalid resources gracefully with appropriate MCP resource exceptions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Active items feed | Read `todo://items` with active tasks in DB | JSON string of array of active items (`created`, `inprogress`) sorted by `due_at:asc` (nulls last) and `priority:desc` | Empty JSON array `[]` if no active items |
| Single item feed | Read `todo://items/42` with existing item | JSON string representing the `TodoResponse` for ID 42 | No error expected |
| Single item missing | Read `todo://items/999` with no matching record | Raises `ResourceNotFoundError` with message | Captured by MCP SDK and returned as resource read error |
| Summary feed | Read `todo://summary` with tasks in various states | Markdown string with status breakdown, priority breakdown, and list of overdue active tasks | Markdown with zero counts and empty overdue list if no tasks |
| Priority feed valid | Read `todo://priorities/urgent` | JSON string of active tasks with `priority="urgent"` | Empty JSON array `[]` if no matching tasks |
| Priority feed invalid | Read `todo://priorities/super-critical` | Raises `ResourceError` indicating invalid priority enum value | Captured by MCP SDK and returned as error |
| DB failure during resource read | OperationalError / DB failure | Catches exception, rolls back session, raises `ResourceError` | Clean session close without hanging connection |

</intent-contract>

## Code Map

- `src/project_qwe/services/todo_service.py` -- Add `get_active_todos(db, priority=None)` and `get_todo_summary(db)` / `get_todo_summary_markdown(db)` supporting active status filtering, overdue item calculation, and markdown summary generation.
- `src/project_qwe/mcp/todos/resources.py` -- Implement and decorate 4 MCP resources (`items`, `items_by_id`, `summary`, `priorities`) using `@mcp_server.resource(...)`.
- `src/project_qwe/mcp/todos/server.py` -- Import `resources` module alongside `tools` to trigger decorator registrations on startup.
- `tests/services/test_todo_service.py` -- Unit tests for `get_active_todos` and `get_todo_summary`.
- `tests/mcp/test_resources.py` -- Comprehensive unit and integration tests verifying `list_resources`, `list_resource_templates`, `read_resource`, error handling, and AD-1 compliance.
- `tests/mcp/test_scaffold.py` -- Update `test_resources_placeholders` to verify active resource calls instead of NotImplementedError.

## Tasks & Acceptance

**Execution:**
- `src/project_qwe/services/todo_service.py` -- Add `get_active_todos` and `get_todo_summary` with Markdown generation -- Provides SQL-level data aggregation and active item filtering without leaking ORM queries to MCP.
- `src/project_qwe/mcp/todos/resources.py` -- Implement `items`, `items_by_id`, `summary`, `priorities` using `@mcp_server.resource` and operation-scoped DB sessions -- Exposes the 4 MCP resources adhering to PRD FR-12 through FR-15 and AD-1.
- `src/project_qwe/mcp/todos/server.py` -- Import `project_qwe.mcp.todos.resources` -- Ensures resource templates and static resources are registered on MCP server startup.
- `tests/services/test_todo_service.py` -- Add tests for `get_active_todos` and `get_todo_summary` -- Validates overdue filtering, active status filtering, and markdown generation.
- `tests/mcp/test_resources.py` -- Create test suite covering all 4 resources, resource templates, edge cases, and AD-1 AST import verification -- Ensures end-to-end correctness of MCP resource handlers.
- `tests/mcp/test_scaffold.py` -- Update `test_resources_placeholders` to reflect implemented resources -- Maintains non-regression of test scaffold.

**Acceptance Criteria:**
- Given the MCP server running in `src/project_qwe/mcp/todos/`, when an MCP client queries resources via `resources/list` and `resources/templates/list`, then `todo://items` and `todo://summary` appear in static resources, and `todo://items/{id}` and `todo://priorities/{priority}` appear in resource templates (FR-12 to FR-15).
- Given active and completed todos in the database, when `todo://items` is read, then only active todos (`created`, `inprogress`) are returned, sorted by `due_at:asc` (nulls last) and `priority:desc`.
- Given an existing todo ID, when `todo://items/{id}` is read, then its JSON payload is returned; when a non-existent ID is read, a `ResourceNotFoundError` is returned (FR-13).
- Given tasks with past `due_at` timestamps, when `todo://summary` is read, then the returned markdown contains counts by status, counts by priority, and lists the overdue active tasks (FR-14).
- Given a valid priority level, when `todo://priorities/{priority}` is read, then only active tasks with that priority are returned; when an invalid priority is requested, a `ResourceError` is returned (FR-15).
- Given any resource read, when executed, database sessions are acquired via `with SessionLocal() as db:` and closed immediately upon completion with zero leaked connections (AD-3).
- Given `src/project_qwe/mcp/`, when scanned with AST, zero imports from `project_qwe.models` exist (AD-1).

## Spec Change Log

## Review Triage Log

## Design Notes

`mcp_server.resource(uri, mime_type)` registers static resources when `uri` contains no template parameters (e.g., `todo://items`, `todo://summary`) and dynamic resource templates when parameters are present (e.g., `todo://items/{id}`, `todo://priorities/{priority}`).
In `resources.py`:
- `items()`: maps to `todo://items` with `mime_type="application/json"`.
- `items_by_id(id: int)`: maps to `todo://items/{id}` with `mime_type="application/json"`.
- `summary()`: maps to `todo://summary` with `mime_type="text/markdown"`.
- `priorities(priority: str)`: maps to `todo://priorities/{priority}` with `mime_type="application/json"`.

For `todo://summary`, formatting into clean GFM Markdown:
```markdown
# Todo Summary

## Status
- Created: 3
- In Progress: 2
- Completed: 5
- Total: 10

## Priority
- Urgent: 1
- High: 2
- Medium: 4
- Low: 3

## Overdue Items
- #4: Prepare DB migration (due: 2026-10-10 12:00:00+00:00, priority: high)
```

## Verification

**Commands:**
- `uv run pytest tests/services/test_todo_service.py` -- expected: All service tests pass including new active todos and summary tests.
- `uv run pytest tests/mcp/test_resources.py` -- expected: All MCP resource tests pass including template resolution and AST checks.
- `uv run pytest` -- expected: Full test suite passes (all 128+ tests).
