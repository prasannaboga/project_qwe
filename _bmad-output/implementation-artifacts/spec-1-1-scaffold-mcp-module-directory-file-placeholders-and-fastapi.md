---
title: 'Scaffold MCP Module Directory, File Placeholders, and FastAPI SSE Mount'
type: 'feature'
created: '2026-10-07'
status: 'in-review'
baseline_commit: 'd4f8b495d92d5b7f359b438b5deca211324fecb9'
review_loop_iteration: 0
context:
  - _bmad-output/planning-artifacts/architecture/architecture-todo-mcp-server/ARCHITECTURE-SPINE.md
  - _bmad-output/implementation-artifacts/epic-1-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project lacks the architectural foundation and ASGI mount required to expose Model Context Protocol (MCP) capabilities to AI clients over Server-Sent Events (SSE).

**Approach:** Create the `src/project_qwe/mcp/todos/` module hierarchy with typed placeholder files (`__init__.py`, `server.py`, `tools.py`, `resources.py`, `prompts.py`, `__main__.py`) and mount the MCP sub-application into the main FastAPI application at `/mcp/todos`.

## Boundaries & Constraints

**Always:**
- Mount the MCP server as a dedicated ASGI sub-application using `app.mount("/mcp/todos", mcp_todos_app)` without wrapping it inside a FastAPI `APIRouter` (AD-2).
- Keep all domain business logic and ORM operations out of the MCP layer; handlers must only interact with `todo_service` and `schemas/todo.py` (AD-1, FR-5).
- Structure the module under `src/project_qwe/mcp/todos/` with placeholder files containing proper typing and empty signatures/placeholders (FR-1).
- Ensure existing FastAPI REST endpoints (`/`, `/health`, `/todos/`) and existing test suite continue to operate without regression.

**Ask First:**
- Changing the route prefix from `/mcp/todos`.
- Modifying project dependencies in `pyproject.toml` beyond what is already pinned.

**Never:**
- Implement actual tool, resource, or prompt domain logic in this scaffolding story (reserved for Stories 1.2–1.4).
- Import SQLAlchemy ORM models from `src/project_qwe/models/` into `src/project_qwe/mcp/` (AD-1).
- Use local process-pipe (`stdio`) transport; SSE is the sole transport mechanism (FR-2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Application startup | `uvicorn project_qwe.main:app` | FastAPI boots cleanly with `/mcp/todos` mounted | Import or syntax errors abort startup |
| Health check regression | `GET /health` | Status 200, `{"status": "ok"}` | 500 if app mount corrupted core routing |
| Root endpoint regression | `GET /` | Status 200, `{"message": "Hello from Project QWE"}` | 500 if app mount corrupted core routing |
| MCP sub-app import | `from project_qwe.mcp.todos.server import mcp_todos_app` | Returns valid ASGI Starlette application instance | ModuleNotFoundError if structure incorrect |
| Submodule placeholder import | Import `tools`, `resources`, `prompts` from `project_qwe.mcp.todos` | Imports succeed cleanly with exported placeholder symbols | Syntax or import error |

</frozen-after-approval>

## Code Map

- `src/project_qwe/main.py` -- Main FastAPI application entry point; line 5 creates `app`, line 7 includes `todos_router`. Needs `app.mount("/mcp/todos", mcp_todos_app)`.
- `src/project_qwe/mcp/__init__.py` -- Top-level MCP namespace package initializer.
- `src/project_qwe/mcp/todos/__init__.py` -- Domain MCP package initializer exporting `mcp_server` and `mcp_todos_app`.
- `src/project_qwe/mcp/todos/server.py` -- MCP server instance definition and SSE ASGI sub-application (`mcp_server`, `mcp_todos_app`).
- `src/project_qwe/mcp/todos/tools.py` -- Placeholder definitions for the 6 MCP tools (`list_todos`, `get_todo_by_id`, `search_todos`, `create_todo`, `update_todo`, `delete_todo`).
- `src/project_qwe/mcp/todos/resources.py` -- Placeholder definitions for MCP context resources (`items`, `items_by_id`, `summary`, `priorities`).
- `src/project_qwe/mcp/todos/prompts.py` -- Placeholder definitions for guided prompts (`daily_planning`, `triage_backlog`, `task_breakdown`).
- `src/project_qwe/mcp/todos/__main__.py` -- Standalone runner entry point for local development execution.
- `tests/mcp/test_scaffold.py` -- Unit tests validating imports, placeholder signatures, ASGI mount, and non-regression of core routes.

## Tasks & Acceptance

**Execution:**
- [x] `src/project_qwe/mcp/__init__.py` -- Create MCP namespace package file -- Establishes Python package boundary for MCP protocols.
- [x] `src/project_qwe/mcp/todos/__init__.py` -- Create domain package file exporting `mcp_server` and `mcp_todos_app` -- Provides clean import interface for the application.
- [x] `src/project_qwe/mcp/todos/server.py` -- Instantiate `MCPServer("project-qwe-todos")` and export `mcp_todos_app = mcp_server.sse_app(sse_path="/sse", message_path="/messages")` -- Provides ASGI sub-application with SSE transport.
- [x] `src/project_qwe/mcp/todos/tools.py` -- Define typed placeholder functions for the 6 tools without domain logic -- Scaffolds tool signatures for Story 1.2.
- [x] `src/project_qwe/mcp/todos/resources.py` -- Define typed placeholder functions for context resources without domain logic -- Scaffolds resource signatures for Story 1.3.
- [x] `src/project_qwe/mcp/todos/prompts.py` -- Define typed placeholder functions for workflow prompts without domain logic -- Scaffolds prompt signatures for Story 1.4.
- [x] `src/project_qwe/mcp/todos/__main__.py` -- Implement entry point running `uvicorn.run(...)` or standalone server execution -- Provides CLI execution runner for development testing.
- [x] `src/project_qwe/main.py` -- Mount `mcp_todos_app` at `/mcp/todos` using `app.mount("/mcp/todos", mcp_todos_app)` -- Connects MCP sub-application into primary FastAPI application.
- [x] `tests/mcp/test_scaffold.py` -- Add automated test suite verifying module imports, placeholder functions, sub-app mount, and existing routes -- Ensures zero regressions and compliance with ACs.

**Acceptance Criteria:**
- Given the project repository at `src/project_qwe/`, when the MCP module layout is created under `src/project_qwe/mcp/todos/`, then the directory structure contains `__init__.py`, `server.py`, `tools.py`, `resources.py`, `prompts.py`, and `__main__.py`.
- Given the created MCP placeholder files, when inspected, then each file contains empty type annotations and placeholder functions/classes without implementing domain logic or importing ORM models.
- Given the main FastAPI application in `src/project_qwe/main.py`, when loaded, then it mounts the MCP sub-application at `/mcp/todos` using `app.mount("/mcp/todos", mcp_todos_app)` and boots without import errors or router conflicts.
- Given the automated test suite, when executed with `uv run pytest`, then all tests pass and verify that `/mcp/todos` is registered on the FastAPI app without regressing `/` or `/health`.

## Spec Change Log

## Design Notes

In `src/project_qwe/mcp/todos/server.py`:
```python
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette

mcp_server = MCPServer(
    name="project-qwe-todos",
    instructions="Todo management and workflow automation protocol server.",
)
mcp_todos_app: Starlette = mcp_server.sse_app(
    sse_path="/sse",
    message_path="/messages",
)
```

In `src/project_qwe/main.py`:
```python
from project_qwe.mcp.todos.server import mcp_todos_app
# ...
app.mount("/mcp/todos", mcp_todos_app)
```

## Verification

**Commands:**
- `uv run pytest` -- expected: all unit and integration tests pass cleanly including new scaffold tests.
- `uv run python -c "from project_qwe.main import app; print(app)"` -- expected: FastAPI application loads without error.
