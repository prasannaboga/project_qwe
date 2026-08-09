# 001 - Basic FastAPI Setup

## Goal

Add FastAPI to the existing Python project and create the initial API structure.

## Requirements

### 1. Add FastAPI

Use `uv` to add FastAPI:

```bash
uv add "fastapi[standard]"
```

Do not manually modify `pyproject.toml` for the dependency. Use `uv sync` and `uv lock`.

---

### 2. Basic Application

Create a FastAPI application using the existing project structure:

```text
src/project_qwe/
├── main.py
├── api/
│   └── ...
├── models/
├── services/
```

Keep API-related code under `api/`.

---

### 3. Home API

Create a basic home endpoint:

```http
GET /
```

Expected response:

```json
{
  "message": "Hello from Project QWE"
}
```

---

### 4. Health Check API

Create:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

Keep the health check implementation simple.

---

### 5. Todos API

Create a Todo API module under:

```text
src/project_qwe/api/todos.py
```

Add placeholders for all CRUD operations.

Endpoints:

```text
GET    /todos
GET    /todos/{todo_id}
POST   /todos
PUT    /todos/{todo_id}
DELETE /todos/{todo_id}
```

For this step:

- Do not implement database functionality.
- Do not create SQLAlchemy models.
- Do not add business logic.
- Use clear placeholder responses indicating that the operation is not implemented yet.
- Keep the endpoints ready for future implementation.

Example:

```json
{
  "message": "Todo creation is not implemented yet"
}
```

---

### 6. API Organization

Keep FastAPI routes separate from business logic.

Follow:

```text
API Endpoint
     ↓
Service
     ↓
Database / Model
```

For this initial setup, services are not required because Todo operations are only placeholders.

---

### 7. Application Startup

The application must be runnable with:

```bash
uv run fastapi dev src/project_qwe/main.py
```

or the equivalent FastAPI development command supported by the installed version.

---

### 8. Verification

Verify the following endpoints:

```text
GET /

GET /health

GET /todos
GET /todos/{todo_id}
POST /todos
PUT /todos/{todo_id}
DELETE /todos/{todo_id}
```

Ensure the application starts successfully and all endpoints return valid HTTP responses.

Do not implement database persistence or actual Todo CRUD logic in this step.
