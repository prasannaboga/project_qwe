<!-- bmad:context -->
<!-- Verified 2026-08-19 against 14526a7. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## project_qwe

FastAPI REST service with SQLAlchemy ORM and Alembic migrations. Python 3.14 managed with `uv`. Planning and design artifacts live in `_bmad-output/` and `docs/`.

## Policy

- Follow `.gitignore`; never read, commit, or track ignored files.
- Never read or reference `mynotes.md` — excluded from project context.

## Where things are

- Application entry point: `src/project_qwe/main.py`
- HTTP endpoints & routes: `src/project_qwe/api/`
- Business logic: `src/project_qwe/services/`
- SQLAlchemy models: `src/project_qwe/models/`
- Pydantic schemas: `src/project_qwe/schemas/`
- Configuration & DB session management: `src/project_qwe/config/`
- Database migrations: `migrations/versions/`

## Running and verifying

- Run the development server with `uv run uvicorn project_qwe.main:app --reload`.
- Run automated tests with `uv run pytest`.
- Generate database migrations with `uv run alembic revision --autogenerate -m "<message>"`.
- Apply migrations with `uv run alembic upgrade head`.

## Conventions that differ from defaults

- Never execute business logic directly in route handlers; all domain operations must go through `src/project_qwe/services/`.
- Never modify an existing Alembic migration that has been applied; create a new migration revision for all schema changes.
- Never instantiate database sessions inside ORM models; inject sessions explicitly from `src/project_qwe/config/database.py`.

<!-- /bmad:context -->

## Repository guidance (agent working notes)

### Overview

Single FastAPI REST service (`project_qwe`) for todo management: SQLAlchemy 2.0 ORM + Alembic migrations + SQLite; Pydantic v2 schemas. Python 3.14 pinned via `uv` (`requires-python >=3.14,<3.15`).

### Commands

- Dev server: `uv run fastapi dev src/project_qwe/main.py` (README) or `uv run uvicorn project_qwe.main:app --reload`.
- Tests: `uv run pytest` (69 tests in ~0.6s against in-memory SQLite; no external services).
- Focused tests: `uv run pytest tests/api/test_todos.py::test_xxx` or `uv run pytest -k "xxx"`.
- Migrations: `uv run alembic revision --autogenerate -m "<message>"`, then `uv run alembic upgrade head`.
- No CI, lint, formatter, or typecheck config exists — `uv run pytest` is the only verification gate.

### Environment

- `DATABASE_URL` comes from root `.env` (see `.env.example`): `sqlite:///data/development.sqlite`; loaded via pydantic-settings; missing sqlite parent dirs are created automatically.
- `migrations/env.py` overrides `alembic.ini`'s `sqlalchemy.url` with `settings.DATABASE_URL` — editing the ini value has no effect.
- `uv run project-qwe` (console script from `pyproject.toml`) is a hello-world placeholder in `__init__.py`, not the API.

### Architecture notes

- Layered flow: `api/` router (thin handlers) → `schemas/` (Pydantic validation) → `services/` (business logic) → `models/` (ORM) → DB via `config/database.py`.
- All DB access via the `get_db` dependency; never create sessions in models or put business logic in route handlers.

### Testing notes

- `tests/conftest.py` has an autouse fixture creating/dropping all tables on in-memory SQLite (`StaticPool`, `check_same_thread=False`); `client` fixture overrides `get_db` on the app via FastAPI `TestClient`.
- E2E tests in `tests/e2e/` run through the same TestClient against the in-memory DB — no running server or external DB needed.

### Gotchas

- `sort` query param format: `<field>:<direction>`; allowed fields: `id`, `title`, `due_at`, `created_at`, `updated_at` (not `priority`); directions: `asc`/`desc`; non-`id` sorts get an `id` tiebreaker. Invalid values return `422` (`todo_service.get_todos`).
- Enums: `priority` = `urgent`/`high`/`medium`/`low` (default `medium`; a filter param on list, not creatable per-request sort); `status` = `created`/`inprogress`/`completed` (default `created`). `title` min length 1, `description` max 1000 chars.
- `PUT /todos/{id}` is partial-update: omitting a field preserves it, but an explicit `null` clears `description`/`due_at` while being ignored for `title`/`status`/`priority` (see `TodoUpdate` + `update_todo`, `model_fields_set`).

### MCP server: planned, not implemented

- `src/project_qwe/mcp/` and `tests/mcp/` are empty stubs — only stale `__pycache__`; no `.py` sources are committed. The `mcp[cli]` dependency is real but currently unused. Do not import or run `project_qwe.mcp.*`.
- The MCP server design lives in `_bmad-output/planning-artifacts/prds/prd-todo-mcp-server/prd.md` and `_bmad-output/planning-artifacts/architecture/architecture-todo-mcp-server/ARCHITECTURE-SPINE.md` (merged via PR #10 as docs only).

### Before changing code

Read, in order: `README.md`, `pyproject.toml`, `.env.example`, the relevant `api/`/`services/`/`models/`/`schemas/` files for your change, and `docs/todos-api-flow.md`. Executable sources of truth win over prose; verify docs against code before relying on them.
