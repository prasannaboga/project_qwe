---
title: 'Todos API Performance and Bounded Pagination'
type: 'feature'
created: '2026-09-06'
status: 'done'
baseline_revision: '60e37dd69317faa0f57e47fa10c280cb86b67783'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The current `GET /todos` endpoint executes an unbounded database query (`select(Todo).order_by(Todo.id)`), loading all rows into memory and causing memory spikes, table scans on unindexed fields, and phantom duplicate/skipped records (drift) across pages.

**Approach:** Implement bounded offset pagination (`page`, `per_page`) with hard server-side limits, deterministic secondary tie-breaking on `id`, zero-count `limit + 1` next-page detection returning `TodoPaginationResponse`, and dedicated single-column database indexes applied via Alembic.

## Boundaries & Constraints

**Always:**
- Route handlers in `src/project_qwe/api/todos.py` remain thin delegates; all sorting parsing, allowlist validation, query construction, and limit+1 logic must reside in `src/project_qwe/services/todo_service.py`.
- Add single-column indexes on `todos` (`created_at`, `updated_at`, `due_at`, `title`, `status`) in `src/project_qwe/models/todo.py` and create a new Alembic migration revision without modifying any existing migrations.
- Validate `page` ($1 \le \text{page} \le 100$) and `per_page` ($1 \le \text{per_page} \le 100$). Reject out-of-bounds values with HTTP 422.
- Validate `sort` parameter matching format `field:direction` against allowlist fields `['id', 'title', 'due_at', 'created_at', 'updated_at']` and directions `['asc', 'desc']`. Reject invalid fields or formats with HTTP 422.
- Enforce secondary tie-breaker ordering on `id` matching primary sort direction (`ORDER BY {field} ASC, id ASC` / `ORDER BY {field} DESC, id DESC`) when primary sort is not `id`.
- Execute `limit + 1` fetch strategy to determine `has_next_page` without running `COUNT(*)`.

**Block If:**
- Upstream requirements require full-table `COUNT(*)` or total pages metadata.
- Upstream requirements mandate cursor/keyset opaque token pagination.

**Never:**
- Never execute business logic directly inside route handlers.
- Never modify existing applied migrations in `migrations/versions/`.
- Never execute raw SQL string formatting; always use parameterized SQLAlchemy expressions.
- Never load unbounded query result sets into application memory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default Pagination | `GET /todos` | HTTP 200 with `{"items": [...], "page": 1, "per_page": 20, "has_next_page": bool}`, ordered by `created_at DESC, id DESC` | No error expected |
| Custom Page & Limit | `GET /todos?page=2&per_page=5` | HTTP 200 with at most 5 items starting at offset 5 | No error expected |
| Valid Custom Sort | `GET /todos?sort=due_at:asc` | HTTP 200 with items ordered by `due_at ASC, id ASC` | No error expected |
| Case-Insensitive Sort Direction | `GET /todos?sort=TITLE:DESC` | HTTP 200 with items ordered by `title DESC, id DESC` | No error expected |
| Next Page Exists | 21 todos exist, query `page=1&per_page=20` | Returns 20 items and `has_next_page = true` | No error expected |
| Last Page Reached | 20 todos exist, query `page=1&per_page=20` | Returns 20 items and `has_next_page = false` | No error expected |
| Invalid Sort Field | `GET /todos?sort=secret_column:asc` | HTTP 422 Unprocessable Entity | Returns validation error detailing invalid sort field |
| Invalid Sort Direction | `GET /todos?sort=due_at:sideways` | HTTP 422 Unprocessable Entity | Returns validation error detailing invalid sort direction |
| Page Below Minimum | `GET /todos?page=0` | HTTP 422 Unprocessable Entity | Returns validation error `page >= 1` |
| Page Exceeds Max Depth | `GET /todos?page=101` | HTTP 422 Unprocessable Entity | Returns validation error `page <= 100` |
| Per Page Exceeds Max Limit | `GET /todos?per_page=101` | HTTP 422 Unprocessable Entity | Returns validation error `per_page <= 100` |

</intent-contract>

## Code Map

- `src/project_qwe/models/todo.py` -- Define `index=True` on `created_at`, `updated_at`, `due_at`, `title`, and `status` columns on `Todo` model.
- `migrations/versions/` -- New Alembic migration revision adding B-tree indexes for all sortable columns.
- `src/project_qwe/schemas/todo.py` -- Define `TodoPaginationResponse` schema containing `items`, `page`, `per_page`, and `has_next_page`.
- `src/project_qwe/services/todo_service.py` -- Update `get_todos` signature and implementation to handle `page`, `per_page`, `sort`, sort allowlist validation, secondary `id` tie-breaking, and `limit + 1` slicing.
- `src/project_qwe/api/todos.py` -- Update `GET /todos` route handler to accept `page`, `per_page`, `sort` query parameters, invoke service, and return `TodoPaginationResponse`.
- `tests/services/test_todo_service.py` -- Unit tests for service pagination, sort parsing, tie-breaking, limit+1 next page detection, and invalid sort validation.
- `tests/api/test_todos.py` -- Integration tests for `GET /todos` pagination parameters, response envelope, 422 validations, and ordering.

## Tasks & Acceptance

**Execution:**
- `src/project_qwe/models/todo.py` -- Add `index=True` to `title`, `status`, `due_at`, `created_at`, and `updated_at` mapped columns.
- `migrations/versions/` -- Generate new Alembic migration revision `uv run alembic revision --autogenerate -m "add_indexes_for_todos_pagination_and_sorting"` and apply via `uv run alembic upgrade head`.
- `src/project_qwe/schemas/todo.py` -- Create `TodoPaginationResponse` Pydantic model with `items: list[TodoResponse]`, `page: int`, `per_page: int`, and `has_next_page: bool`.
- `src/project_qwe/services/todo_service.py` -- Refactor `get_todos(db: Session, page: int = 1, per_page: int = 20, sort: str = "created_at:desc")` to parse/validate sort parameters, apply secondary tie-breaker, execute limit+1 query, and return `tuple[Sequence[Todo], bool]`.
- `src/project_qwe/api/todos.py` -- Update `GET /todos` route handler to accept `page: int = Query(1, ge=1, le=100)`, `per_page: int = Query(20, ge=1, le=100)`, and `sort: str = Query("created_at:desc")`, pass parameters to `todo_service.get_todos`, and construct `TodoPaginationResponse`.
- `tests/services/test_todo_service.py` -- Add unit tests covering all pagination parameters, limit+1 behavior, sort directions, and invalid sort errors.
- `tests/api/test_todos.py` -- Update existing `GET /todos` tests and add integration tests for `TodoPaginationResponse` envelope, default values, query limits, and 422 responses.

**Acceptance Criteria:**
- Given a database with multiple todos, when `GET /todos` is called with default parameters, then HTTP 200 is returned with `page=1`, `per_page=20`, `items` sorted by `created_at DESC, id DESC`, and `has_next_page` correctly computed.
- Given a request with `page=2&per_page=5`, when `GET /todos` is queried, then exactly at most 5 items starting at offset 5 are returned in the response envelope.
- Given a request with `sort=invalid_col:asc` or `sort=due_at:invalid_dir`, when `GET /todos` is called, then HTTP 422 is returned with a descriptive error message.
- Given a request with `page=101` or `per_page=101`, when `GET /todos` is called, then HTTP 422 is returned.
- Given multiple todos sharing the exact same timestamp, when sorted by that timestamp, then results maintain deterministic pagination across page boundaries without duplicates or skips due to secondary `id` sorting.
- Given a clean database, when `uv run alembic upgrade head` is executed, then the new migration cleanly applies all five B-tree indexes.
- Given the complete test suite, when `uv run pytest` is executed, then all tests pass with 100% success rate.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Verification

**Commands:**
- `uv run alembic upgrade head` -- expected: All migrations applied cleanly including the new index migration.
- `uv run pytest` -- expected: 100% passed tests across unit and integration test suites.

## Auto Run Result

- **Status:** done
- **Summary:** Implemented bounded offset pagination, strict sort allowlisting, secondary tie-breaker sorting on ID, zero-count limit+1 next-page detection, and Alembic migration for single-column B-tree indexes.
- **Files Changed:**
  - `src/project_qwe/models/todo.py` -- Added `index=True` to `title`, `status`, `due_at`, `created_at`, `updated_at`.
  - `migrations/versions/b1976b3395b4_add_indexes_for_todos_pagination_and_.py` -- Created and applied index migration.
  - `src/project_qwe/schemas/todo.py` -- Added `TodoPaginationResponse` model.
  - `src/project_qwe/services/todo_service.py` -- Updated `get_todos` with pagination, sort parsing, allowlist validation, tie-breakers, and limit+1.
  - `src/project_qwe/api/todos.py` -- Updated `GET /todos` endpoint with query parameters and `TodoPaginationResponse`.
  - `tests/services/test_todo_service.py` -- Added unit tests for pagination, sorting, limit+1, tie-breakers, and validation errors.
  - `tests/api/test_todos.py` -- Added integration tests for pagination envelope, sorting, limits, next-page boundary, and 422 validations.
- **Review Findings Breakdown:** 0 patches applied, 0 items deferred, 0 items rejected.
- **Follow-up Review Recommendation:** false (0 patched findings, score 0).
- **Verification:** All 45 tests passed (`uv run pytest`), Alembic migrations applied (`uv run alembic upgrade head`).
- **Residual Risks:** None.
