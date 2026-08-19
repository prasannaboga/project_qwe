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
