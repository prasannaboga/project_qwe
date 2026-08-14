# 002 - Implement Todo CRUD

## Goal

Implement persistent Todo CRUD functionality using SQLAlchemy ORM and SQLite.

## Database

Use SQLite as the database.

Database file:

data/development.sqlite

Create the database connection setup in:

src/project_qwe/config/database.py

The database configuration should:

- Use SQLAlchemy.
- Create the SQLite engine.
- Configure the session factory.
- Provide a reusable database session for the application.
- Ensure the `data/` directory exists when required.
- Keep database configuration separate from business logic.

## Todo Model

Create a SQLAlchemy ORM model for Todo.

Location:

src/project_qwe/models/todo.py

Columns:

- `id`
- `title`
- `created_at`
- `updated_at`

Requirements:

- Use SQLAlchemy declarative ORM.
- `id` should be the primary key.
- `title` should be required.
- `created_at` should be populated when the record is created.
- `updated_at` should be populated when the record is created and updated whenever the Todo changes.
- Use appropriate SQLAlchemy types and constraints.
- Do not put business logic in the model.

## Alembic Migration

Configure Alembic for the SQLite database.

Create an Alembic migration for the Todo table.

The migration should create the Todo table with:

- `id`
- `title`
- `created_at`
- `updated_at`

Ensure the migration can be applied successfully with:

uv run alembic upgrade head

Do not manually modify the database schema outside Alembic.

## Todo Service

Create:

src/project_qwe/services/todo_service.py

Move all Todo business and database operations into this service.

Implement functions for:

- Create Todo
- Get all Todos
- Get Todo by ID
- Update Todo
- Delete Todo

The service should:

- Use SQLAlchemy sessions.
- Commit successful changes.
- Roll back failed transactions where appropriate.
- Refresh created/updated records when necessary.
- Handle a Todo that does not exist appropriately.
- Keep FastAPI-specific concerns out of the service.

## Todo API

Update:

src/project_qwe/api/todos.py

Replace the existing placeholder implementations with real CRUD operations.

Implement:

- GET /todos
- GET /todos/{todo_id}
- POST /todos
- PUT /todos/{todo_id}
- DELETE /todos/{todo_id}

Requirements:

- Use FastAPI.
- Use appropriate request/response schemas.
- Validate incoming data.
- Call `todo_service.py` for business logic.
- Do not access SQLAlchemy directly from the API endpoint.
- Return appropriate HTTP status codes.
- Return a clear response when a Todo does not exist.

The API layer should remain thin:

API endpoint
↓
Todo Service
↓
SQLAlchemy ORM
↓
SQLite

## Request / Response

Create appropriate Pydantic schemas for Todo API requests and responses.

At minimum:

### Create

title is required.

### Update

Allow updating the Todo title.

### Response

Return:

- id
- title
- created_at
- updated_at

## Project Structure

Maintain this structure:

```text
src/project_qwe/
├── api/
│   └── todos.py
├── config/
│   └── database.py
├── models/
│   └── todo.py
├── services/
│   └── todo_service.py
└── main.py
```

Also configure:

alembic.ini
migrations/
data/

Do not introduce unnecessary additional layers.

## Verification

After implementation:

1. Run the migration:

```
uv run alembic upgrade head
```

` 2. Update tests:

- Verify all Todo operations:
  - POST /todos
  - GET /todos
  - GET /todos/{todo_id}
  - PUT /todos/{todo_id}
  - DELETE /todos/{todo_id}

3. Verify that data persists in:

```
data/development.sqlite
```

**Do not modify unrelated functionality.**
