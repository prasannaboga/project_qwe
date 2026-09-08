---
date: 2026-09-08
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Retrospective: Todos API Performance & Bounded Pagination (`spec-todo-pagination`)

## Epic summary

- **Epic / Spec**: `spec-todo-pagination` (Todos API Performance & Bounded Pagination)
- **Spec Location**: `_bmad-output/specs/spec-todo-pagination/SPEC.md`
- **Implementation Artifact**: `_bmad-output/implementation-artifacts/spec-todo-pagination.md`
- **Diff Range**: `60e37dd..c3be037` (PR #6, commit `c3be037d3f302bb4f951f8c07a482b4a4eb2ad8c`)
- **Stories / Tasks Completed**:
  - Story 1: Add database indexes for pagination and sorting (`migrations/versions/b1976b3395b4_add_indexes_for_todos_pagination_and_.py`, `src/project_qwe/models/todo.py`)
  - Story 2: Define pagination schemas and query validation models (`src/project_qwe/schemas/todo.py`)
  - Story 3: Implement limit+1 pagination and deterministic sorting in service layer (`src/project_qwe/services/todo_service.py`)
  - Story 4: Wire API route and write comprehensive automated test suite (`src/project_qwe/api/todos.py`, `tests/api/test_todos.py`, `tests/services/test_todo_service.py`)
- **Pending / Unfinished Stories**: None (`pending_stories: []`). All declared capabilities and implementation tasks verified `done`.
- **Evidence Inventory**:
  - Spec contract: Present at `_bmad-output/specs/spec-todo-pagination/SPEC.md` (derived from PRD `prd-project_qwe-2026-09-06`).
  - Implementation artifact: Present at `_bmad-output/implementation-artifacts/spec-todo-pagination.md`.
  - Git commits & churn: Verified via `git_evidence.py` across range `60e37dd..c3be037` (8 files changed, +392 / -29 lines).
  - Sprint status: Absent (stories mode; no `sprint-status.yaml` used).
  - Previous retrospective: None found (this is the repository's first retrospective).
  - Session logs: Not preserved in workspace; recorded as missing evidence (process lesson noted).

## Findings

### Aggregate Views

1. **Architecture Delta & Layering**
   - **Source**: `src/project_qwe/api/todos.py:16-39`, `src/project_qwe/services/todo_service.py:28-79`
   - **Observation**: Architectural separation is cleanly preserved. The route handler `get_todos` in `api/todos.py` acts strictly as a thin delegate, forwarding parameters (`page`, `per_page`, `sort`) and catching service-layer `ValueError` exceptions to convert to HTTP 422. Query construction, sort parameter parsing, allowlist validation, offset calculation, and `limit + 1` slicing are encapsulated entirely within `services/todo_service.py`. No session creation exists in models.
   - **Disposition**: Accept as-is.

2. **Duplication Map**
   - **Source**: `src/project_qwe/services/todo_service.py:28-79`
   - **Observation**: Pagination and sorting logic are centralized exclusively in `todo_service.get_todos`. No duplicated sort parsing or pagination slicing exists elsewhere in the codebase.
   - **Disposition**: Accept as-is.

3. **God-Class & Churn Analysis**
   - **Source**: `git_evidence.py` on range `60e37dd..c3be037`
   - **Observation**: Net line churn was modest and healthy across non-merge commits:
     - `src/project_qwe/services/todo_service.py`: +53 / -4 (net +49, total file length 126 lines)
     - `src/project_qwe/api/todos.py`: +31 / -8 (net +23, total file length 93 lines)
     - `tests/api/test_todos.py`: +80 / -9 (net +71, total file length 189 lines)
     - `tests/services/test_todo_service.py`: +53 / -7 (net +46, total file length 129 lines)
     No file exceeded maintainability boundaries or exhibited runaway growth.
   - **Disposition**: Accept as-is.

4. **Spec-to-Implementation Reconciliation**
   - **Source**: `_bmad-output/specs/spec-todo-pagination/SPEC.md` vs `src/project_qwe/services/todo_service.py:28-30`
   - **Observation**: `SPEC.md` CAP-3 specified single-column B-tree indexes for `created_at`, `updated_at`, `due_at`, `title`, and `status`. Migration `b1976b3395b4` created all 5 indexes. In `todo_service.py`, `ALLOWED_SORT_FIELDS` includes `{"id", "title", "due_at", "created_at", "updated_at"}` matching CAP-2's sorting allowlist, while excluding `status`. This is an acceptable distinction (status was indexed anticipating status filtering).
   - **Disposition**: Accept as-is.

### Diff-Scope Review Lenses

1. **Pattern Divergence: Starlette Deprecation Warning**
   - **Source**: `src/project_qwe/api/todos.py:31`, `tests/api/test_todos.py:141,146`
   - **Observation**: In `src/project_qwe/api/todos.py`, HTTP 422 is referenced via `status.HTTP_422_UNPROCESSABLE_ENTITY`. During pytest execution, Starlette emits:
     `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`
   - **Disposition**: Fix now / Track as open action item.
   - **Upstream Lesson**: Use up-to-date HTTP status constants or standard HTTP status codes in route exception mappings.

2. **Verification Gap: API Integration Test for Missing Sort Delimiter**
   - **Source**: `tests/api/test_todos.py`, `src/project_qwe/services/todo_service.py:47-48`
   - **Observation**: `tests/services/test_todo_service.py` tests `sort="invalid_format"` (missing `:`), but `tests/api/test_todos.py` only tests invalid field (`secret_column:asc`) and invalid direction (`due_at:sideways`). An end-to-end integration test asserting HTTP 422 on `GET /todos?sort=malformed` is missing from `test_todos.py`.
   - **Disposition**: Fix now / Track as open action item.
   - **Upstream Lesson**: Derive API integration tests directly from the full service-level validation failure matrix.

## Behavior verification

- **Automated Test Suite**:
  - Ran `uv run pytest`. All 45 tests passed in 0.69s (100% pass rate).
- **Alembic Database Migration**:
  - Ran `uv run alembic current`. Verified migration head `b1976b3395b4` (`add_indexes_for_todos_pagination_and_sorting`) applied cleanly.
- **SQLite Index & Query Plan Verification**:
  - Verified index existence in `sqlite_master`:
    `ix_todos_created_at`, `ix_todos_due_at`, `ix_todos_status`, `ix_todos_title`, `ix_todos_updated_at`.
  - Executed `EXPLAIN QUERY PLAN SELECT * FROM todos ORDER BY {field} DESC, id DESC LIMIT 21` across SQLite database:
    - `created_at`: `SCAN todos USING INDEX ix_todos_created_at`
    - `due_at`: `SCAN todos USING INDEX ix_todos_due_at`
    - `title`: `SCAN todos USING INDEX ix_todos_title`
    - `updated_at`: `SCAN todos USING INDEX ix_todos_updated_at`
    All sorted queries utilize the dedicated B-Tree index scan without full table scans.
- **End-to-End API Runtime Verification**:
  - Exercised live FastAPI application via `TestClient`:
    - Malformed sort (`/todos?sort=malformed`) -> HTTP 422 `{"detail": "Invalid sort format. Expected '<field>:<direction>'"}`.
    - Invalid sort field (`/todos?sort=foo:asc`) -> HTTP 422 `{"detail": "Invalid sort field 'foo'. Allowed fields: [...]"}`.
    - Invalid sort direction (`/todos?sort=title:sideways`) -> HTTP 422 `{"detail": "Invalid sort direction 'sideways'. Allowed directions: 'asc', 'desc'"}`.
    - Page bounds (`/todos?page=0`, `/todos?page=101`, `/todos?per_page=0`, `/todos?per_page=101`) -> HTTP 422.
    - Default pagination (`/todos`) -> HTTP 200 with envelope `{"items": [...], "page": 1, "per_page": 20, "has_next_page": false}`.

## Previous-retro follow-through

No prior retrospective document existed in the repository (`_bmad-output/**/epic-*-retro-*.md` / `_bmad-output/**/RETROSPECTIVE.md`). This is the initial retrospective; there are no prior action items to track.

## Action items

1. **Update deprecated HTTP status constant in API route**
   - **Action**: Replace `status.HTTP_422_UNPROCESSABLE_ENTITY` with `status.HTTP_422_UNPROCESSABLE_CONTENT` (or standard constant) in `src/project_qwe/api/todos.py` to clear `StarletteDeprecationWarning`.
   - **Owner**: Developer
   - **Type**: Remediation (Maintenance)

2. **Add API integration test for missing sort delimiter**
   - **Action**: Add `test_get_todos_malformed_sort_format_422` in `tests/api/test_todos.py` to test query `sort=malformed` at the HTTP route boundary.
   - **Owner**: Developer / QA
   - **Type**: Test Coverage

## Acceptance verdict

- **Verdict**: **accepted-with-open-items**
- **Criteria**: declared (`SPEC.md` CAP-1, CAP-2, CAP-3, Constraints, Success Signal)
- **Evidence**:
  - **CAP-1**: Bounded offset pagination with `limit + 1` next-page detection and `{items, page, per_page, has_next_page}` response envelope verified via tests and live execution. Page and per-page limits (1-100) enforced with HTTP 422.
  - **CAP-2**: Structured sorting against allowlist (`id`, `title`, `due_at`, `created_at`, `updated_at`) with case-insensitivity and deterministic secondary `id` tie-breaking verified in service and API layers.
  - **CAP-3**: Single-column B-tree indexes added via forward-only Alembic migration `b1976b3395b4`. SQLite query plans confirm index-backed execution (`SCAN todos USING INDEX ix_todos_<field>`).
  - **Code invariants**: 4-tier layered architecture preserved without leaks. Route handlers remain thin delegates.
  - **Pending stories**: None (`pending_stories: []`). All tasks complete.
  - Open items tracked are non-blocking maintenance updates (deprecation warning and test case addition).

## Open questions

None. The implementation strictly adheres to the architecture, guidelines, and declared capabilities.
