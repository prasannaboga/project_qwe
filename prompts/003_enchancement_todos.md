# 003 - Enhance Todos

## Goal

Enhance the existing Todo application with environment-based configuration,
Todo status, due dates, and updated tests.

## Requirements

### 1. Configuration

Use `python-dotenv` and `pydantic-settings`.

Create:

```text
src/project_qwe/config/settings.py
```

Configure the application to load settings from `.env`.

Add the following to `.env`:

```env
DATABASE_URL=sqlite:///data/development.sqlite
```

Update:

```text
src/project_qwe/config/database.py
```

to use `DATABASE_URL` from the application settings.

Do not hardcode the database URL in `database.py`.

Also create/update `.env.example` with:

```env
DATABASE_URL=sqlite:///data/development.sqlite
```

Make sure `.env` is included in `.gitignore`.

### 2. Todo Model

Update the existing Todo model:

```text
src/project_qwe/models/todo.py
```

Add the following fields:

```text
status
due_at
```

#### status

Use an enum with these values:

```text
created
inprogress
completed
```

The default status should be:

```text
created
```

Do not allow invalid status values.

#### due_at

Add a nullable datetime field.

### 3. Database Migration

Create a new Alembic migration for the Todo changes.

Add:

```text
status
due_at
```

to the existing Todo table.

Do not modify the existing migration.

The migration should work with the existing database:

```text
data/development.sqlite
```

Verify with:

```bash
uv run alembic upgrade head
```

### 4. Todo Service

Update:

```text
src/project_qwe/services/todo_service.py
```

to support the new fields.

Create Todo should support:

- title
- status
- due_at

Update Todo should support:

- title
- status
- due_at

Keep all Todo business logic inside the service.

### 5. Todo API

Update:

```text
src/project_qwe/api/todos.py
```

to support the new fields.

Update the request and response schemas.

Todo response should include:

```json
{
  "id": 1,
  "title": "Learn FastAPI",
  "status": "created",
  "due_at": "2026-08-20T18:00:00",
  "created_at": "2026-08-15T10:00:00",
  "updated_at": "2026-08-15T10:00:00"
}
```

Support the following operations:

```text
POST   /todos
GET    /todos
GET    /todos/{todo_id}
PUT    /todos/{todo_id}
DELETE /todos/{todo_id}
```

Keep API endpoints thin and continue using:

```text
API → Todo Service → SQLAlchemy → SQLite
```

### 6. Tests

Update the existing tests for the Todo changes.

Add tests to verify:

- Todo defaults to `created` status.
- Valid statuses can be used.
- Invalid status is rejected.
- Todo can be created with `due_at`.
- Todo can be updated with a different status.
- Todo can be updated with a different `due_at`.
- Todo responses include `status` and `due_at`.
- Existing CRUD functionality continues to work.
- `DATABASE_URL` is loaded from settings.

Do not remove or weaken existing tests.

### 7. Dependencies

Use `uv` to add the required dependencies.

Do not manually edit dependency versions in `pyproject.toml`.

### 8. Verification

Run the migration:

```bash
uv run alembic upgrade head
```

Run the tests:

```bash
uv run pytest
```

and all Todo CRUD operations work with the new fields.

Do not make unrelated changes.
