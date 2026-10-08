# Epic 1 Context: Todo MCP Server Integration

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Enable AI agent clients (such as Claude Desktop, VS Code Copilot / Roo Code, and Cursor) to manage, search, inspect, and prioritize tasks over a high-performance Server-Sent Events (SSE) transport mounted into FastAPI, adhering to clean architecture invariants and delegating all domain operations to the existing service layer.

## Stories

- Story 1.1: Scaffold MCP Module Directory, File Placeholders, and FastAPI SSE Mount
- Story 1.2: Implement Service Extensions and MCP CRUD & Search Tools
- Story 1.3: Implement MCP Context Resources
- Story 1.4: Implement MCP Guided Workflow Prompts
- Story 1.5: Implement Automated Test Suite and Protocol Compliance Verification

## Requirements & Constraints

- **Transport & Endpoints:** The MCP server must communicate exclusively over Server-Sent Events (SSE) mounted under `/mcp/todos/` in FastAPI. `GET /mcp/todos/sse` provides the persistent event stream and session establishment, while `POST /mcp/todos/messages` receives client JSON-RPC messages. Process-pipe (`stdio`) transport is not supported.
- **Connection Keep-Alive:** The SSE transport must emit periodic ping or comment heartbeats (every 15 to 30 seconds) to maintain persistent connections across proxies and load balancers.
- **Tools Capability:** Expose six validated JSON-RPC tools:
  - `list_todos`: Paginated retrieval bounded between 5 and 20 items per page, defaulting to sorting by due date ascending (nulls last) and priority descending (`urgent` > `high` > `medium` > `low`), with optional priority filtering.
  - `get_todo_by_id`: Complete task lookup by integer ID.
  - `search_todos`: Case-insensitive text substring search across title and description with configurable limit (1–20, default 5).
  - `create_todo`: Task creation with required title and optional description, status, priority, and due date.
  - `update_todo`: Partial task updates by ID.
  - `delete_todo`: Task deletion by ID with confirmation response.
- **Resources Capability:** Expose read-only contextual feeds:
  - `todo://items` (`application/json`): Active items (`created`, `inprogress`) sorted by due date and priority.
  - `todo://items/{id}` (`application/json`): Details for a single task by ID.
  - `todo://summary` (`text/markdown`): Aggregated overview with status counts, priority counts, and overdue items.
  - `todo://priorities/{priority}` (`application/json`): Active items filtered by priority level.
- **Prompts Capability:** Expose three guided prompt templates:
  - `daily_planning`: Injects `todo://summary` with optional focus area to guide daily scheduling of 3–5 items.
  - `triage_backlog`: Evaluates backlog items (`status="created"`) for clarity, priority alignment, and duplication.
  - `task_breakdown`: Takes a required `todo_id`, retrieves task context via `todo://items/{todo_id}`, and formats sub-tasks as executable `create_todo` tool calls.
- **Validation & Error Handling:** Validate all tool inputs with Pydantic schemas. Invalid arguments or domain errors must return standard MCP error results (`isError: true` with descriptive text) rather than unhandled 500 exceptions or dropping the SSE stream.
- **Performance & Protocol Compliance:** Roundtrip tool execution latency must stay under 100ms for local database operations. The server must comply with MCP specifications and support standard discovery endpoints (`tools/list`, `resources/list`, `prompts/list`).

## Technical Decisions

- **Ports & Adapters Isolation:** The MCP adapter under `src/project_qwe/mcp/todos/` acts as an inbound port parallel to the REST API. It must interact exclusively with `src/project_qwe/services/todo_service.py` and `src/project_qwe/schemas/todo.py`. Direct imports of SQLAlchemy ORM models from `src/project_qwe/models/` or direct database queries in MCP handlers are strictly prohibited.
- **FastAPI Sub-Application Mounting:** The MCP server is mounted directly as a dedicated ASGI sub-application using `app.mount("/mcp/todos", mcp_todos_app)` in `src/project_qwe/main.py` via `mcp.server.sse.SseServerTransport`. It must not use FastAPI `APIRouter` route definitions.
- **Operation-Scoped Database Sessions:** Persistent SSE connection loops must hold zero open database connections. Sessions must be acquired from `SessionLocal()` via context managers strictly for the execution span of individual tool calls or resource queries, and closed immediately upon completion.
- **Service-Owned Query Assembly:** Keyword search and multi-criteria sorting logic must be implemented inside `todo_service` at the SQL query level rather than performed in-memory inside MCP handlers. Any schema changes or new indexes require new Alembic revisions without modifying existing migrations.
- **Multi-Instance Session Stickiness:** Because the Python MCP SDK maintains SSE session stream writers in process memory, multi-instance production deployments require ALB cookie-based stickiness on `/mcp/*`.
- **Module Layout:** Components reside under `src/project_qwe/mcp/todos/` (`server.py`, `tools.py`, `resources.py`, `prompts.py`, `__main__.py`).

## Cross-Story Dependencies

- **Story 1.1** scaffolds the package structure and mounts the ASGI sub-application in `src/project_qwe/main.py`, establishing the base server instance.
- **Story 1.2** extends `todo_service` with SQL-level search and sorting, and implements the six MCP tools.
- **Story 1.3** registers context resources (`todo://items`, `todo://items/{id}`, `todo://summary`, `todo://priorities/{priority}`) relying on `todo_service` queries.
- **Story 1.4** implements prompts that reference the resources established in Story 1.3 and generate tool calls matching Story 1.2 schemas.
- **Story 1.5** requires Stories 1.1–1.4 to execute unit, integration, and end-to-end SSE transport test suites verifying compliance and performance.
