# Project Development Instructions

## Project Overview

This is a Python 3.14 application managed with `uv`.

Use modern Python practices and keep the application modular, testable, and maintainable.

## Python

- Use Python 3.14.
- Use `uv` for project initialization, dependency management, and running commands.
- Prefer `uv run` for executing project commands.
- Use type hints for functions and public interfaces.
- Follow PEP 8.
- Prefer clear, explicit code over clever abstractions.
- Avoid unnecessary dependencies.

## Project Structure

Use the following structure:

```text
project_qwe/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── migrations/
│   └── versions/
├── src/
│   └── project_qwe/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       ├── models/
│       └── services/
└── tests/
```

### `src/project_qwe/services`

Contains application and business logic.

Rules:

- Keep business logic out of API endpoints.
- Services should be reusable and independently testable.
- Services can use models and database-related components.
- Avoid putting HTTP-specific logic in services.

Example:

```text
services/
├── __init__.py
└── user_service.py
```

### `src/project_qwe/models`

Contains SQLAlchemy ORM models.

Rules:

- Define database entities using SQLAlchemy.
- Keep ORM/database representation separate from business logic.
- Use appropriate relationships and constraints.
- Avoid putting business workflows inside ORM models.

Example:

```text
models/
├── __init__.py
├── user.py
└── todo.py
```

### `src/project_qwe/api`

Contains FastAPI endpoints and API-specific code.

Rules:

- API routes should be thin.
- Validate request data at the API boundary.
- Call services for business logic.
- Do not implement business logic directly inside route handlers.
- Return appropriate HTTP responses and status codes.

Example:

```text
api/
├── __init__.py
├── users.py
└── todos.py
```

## FastAPI

Use FastAPI for HTTP APIs.

Recommended flow:

```text
HTTP Request
     ↓
FastAPI Endpoint
     ↓
Validation
     ↓
Service
     ↓
SQLAlchemy Model / Database
     ↓
Response
```

Keep route handlers small.

Example:

```python
@router.post("/users")
def create_user(request: CreateUserRequest):
    return user_service.create_user(request)
```

## SQLAlchemy

Use SQLAlchemy as the ORM.

Rules:

- Use SQLAlchemy ORM models.
- Keep database configuration separate from models.
- Use explicit database sessions.
- Do not create database sessions inside individual ORM models.
- Avoid raw SQL unless there is a clear reason.
- Use transactions appropriately.

## Alembic

Use Alembic for database schema migrations.

Rules:

- Never modify an existing migration that has already been applied.
- Create a new migration for schema changes.
- Keep migrations small and focused.
- Review generated migrations before committing them.
- Ensure migrations are reversible where practical.

Typical commands:

```bash
uv run alembic revision --autogenerate -m "create users table"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Dependency Management

Use `uv`:

```bash
uv add fastapi
uv add sqlalchemy
uv add alembic
uv add uvicorn
```

Run the application with:

```bash
uv run uvicorn project_qwe.main:app --reload
```

Run tests with:

```bash
uv run pytest
```

Run migrations with:

```bash
uv run alembic upgrade head
```

## Testing

Use pytest.

Organize tests around behavior rather than implementation details.

```text
tests/
├── api/
├── services/
└── models/
```

Prioritize unit tests for service/business logic.

For API behavior, add focused integration tests.

## Code Quality

Before considering a change complete:

1. Verify the implementation.
2. Run relevant tests.
3. Check type hints and imports.
4. Check database migrations if models changed.
5. Avoid unrelated changes.
6. Keep the implementation as simple as possible.

## AI Development Guidelines

When implementing a feature:

1. Understand the existing code.
2. Identify affected files.
3. Explain the proposed approach when the change is non-trivial.
4. Make the smallest reasonable change.
5. Reuse existing patterns.
6. Add or update tests.
7. Verify the implementation.

Do not introduce new architecture or dependencies without a clear requirement.

## Architecture Principle

Follow:

```text
API
 ↓
Services
 ↓
Models / Database
```

Do not bypass the service layer for business operations.

Keep responsibilities clearly separated:

- `api/` → HTTP/API concerns
- `services/` → business logic
- `models/` → SQLAlchemy ORM/database entities
- `migrations/` → database schema evolution
- `tests/` → automated verification
