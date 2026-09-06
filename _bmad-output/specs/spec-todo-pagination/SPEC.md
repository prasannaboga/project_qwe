---
id: SPEC-todo-pagination
companions: []
sources:
  - _bmad-output/planning-artifacts/prds/prd-project_qwe-2026-09-06/prd.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Todos API Performance & Bounded Pagination

## Why

The existing `GET /todos` endpoint executes an unconstrained database query returning all table rows into memory on every request. This causes unbounded memory growth, potential SQLite table locks, query drift across page boundaries during concurrent row additions, and performance degradation under load. This specification defines a bounded, zero-count pagination and deterministic sorting contract backed by database indexes.

## Capabilities

- **CAP-1**
  - **intent:** API consumer can request bounded pages of todos using `page` and `per_page` query parameters and receive a lightweight envelope with `has_next_page` evaluated via `limit + 1` query execution without executing `COUNT(*)`.
  - **success:** `GET /todos?page=1&per_page=20` returns at most 20 items in `{"items": [...], "page": 1, "per_page": 20, "has_next_page": bool}`, and queries with `page > 100` or `per_page > 100` return HTTP 422.

- **CAP-2**
  - **intent:** API consumer can sort todos via `sort=<field>:<direction>` across an explicit allowlist (`id`, `title`, `due_at`, `created_at`, `updated_at`), with the database applying secondary deterministic ordering on `id` to eliminate page drift.
  - **success:** Requests like `sort=due_at:asc` order by `due_at ASC, id ASC`, invalid sort fields or directions return HTTP 422, and consecutive page reads during concurrent inserts produce zero duplicate or skipped rows.

- **CAP-3**
  - **intent:** System maintains dedicated single-column B-Tree indexes on all filtered and sorted columns (`created_at`, `updated_at`, `due_at`, `title`, `status`) to ensure index-backed query execution.
  - **success:** A new Alembic migration applies cleanly via `uv run alembic upgrade head` without altering prior migrations, and all sorted query plans hit indexes.

## Constraints

- Route handlers in `src/project_qwe/api/todos.py` must remain thin delegates; all sorting, validation, limit+1 slicing, and database query logic must live in `src/project_qwe/services/todo_service.py`.
- No raw SQL string interpolation or arbitrary SQL expressions; all queries must use parameterized SQLAlchemy ORM constructs.
- Never modify an existing applied Alembic migration in `migrations/versions/`; all index additions must be in a new migration revision.
- Maximum page depth (`page`) is clamped at 100; maximum page size (`per_page`) is clamped at 100.
- Mandatory or automatic `COUNT(*)` queries are prohibited on listing endpoints.

## Non-goals

- Cursor/keyset-based pagination tokens (offset pagination with hard depth cap and secondary tie-breaker ID meets stability requirements).
- Mandatory total-count calculation or total-pages response field.
- Multi-column composite sort syntax or user-defined dynamic column sorting.
- Full-text search integrations.

## Success signal

Running automated integration tests with `uv run pytest` verifies that `GET /todos` returns paginated envelopes with accurate `has_next_page` flags, applies secondary tie-breaker ordering, rejects invalid sort parameters with 422, executes over SQLite indexes without full table scans, and preserves 100% test pass rate.
