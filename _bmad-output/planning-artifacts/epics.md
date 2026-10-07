---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-todo-mcp-server/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-todo-mcp-server/ARCHITECTURE-SPINE.md
---

# project_qwe - Epic Breakdown: Todo MCP Server

## Overview

This document provides the complete epic and story breakdown for the Todo Model Context Protocol (MCP) Server in project_qwe, decomposing requirements from the PRD and Architecture Spine into implementable, value-driven stories.

## Requirements Inventory

### Functional Requirements

- **FR-1**: The MCP server MUST be built using the official Python MCP SDK (`mcp[cli]>=2.2.0,<2.3.0`) within the Python 3.14 virtual environment.
- **FR-2**: The server MUST use Server-Sent Events (SSE) as its sole transport mechanism. Local process-pipe (`stdio`) transport is explicitly out of scope.
- **FR-3**: The SSE transport MUST be mounted directly inside the primary FastAPI application (`src/project_qwe/main.py`) under the routing prefix `/mcp/todos/`:
  - `GET /mcp/todos/sse`: Establishes the persistent SSE stream to the client.
  - `POST /mcp/todos/messages`: Receives JSON-RPC client messages (tool calls, prompt requests, resource fetches).
- **FR-4**: The server MUST isolate database sessions per request/invocation using `project_qwe.config.database.SessionLocal()`, ensuring sessions are committed or rolled back and closed cleanly without leaking connections.
- **FR-5**: The server MUST NOT implement domain business logic or direct ORM queries inside tool or resource handlers; all domain operations MUST delegate to `src/project_qwe/services/todo_service.py`.
- **FR-6**: `list_todos` Tool: Retrieve a paginated list of todo items with default sorting (`due_at:asc`, `priority:desc`), pagination bounded between 5 and 20 items (`per_page`, default: 10, min: 5, max: 20; `page`, default: 1, min: 1, max: 100), and optional priority filter.
- **FR-7**: `get_todo_by_id` Tool: Fetch complete details of a specific todo item by its unique integer identifier (`todo_id: int`).
- **FR-8**: `search_todos` Tool: Search for todo items matching text in their title or description (case-insensitive substring match) with `query` (string, required) and `limit` (integer, default: 5, min: 1, max: 20).
- **FR-9**: `create_todo` Tool: Create a new todo item with `title` (required), optional `description`, `status` (default: "created"), `priority` (default: "medium"), and optional `due_at`.
- **FR-10**: `update_todo` Tool: Partially update fields of an existing todo item by ID (`todo_id`, `title`, `description`, `status`, `priority`, `due_at`).
- **FR-11**: `delete_todo` Tool: Permanently delete a todo item by ID (`todo_id: int`).
- **FR-12**: `todo://items` Resource: Read-only context feed (`application/json`) returning all active (`created`, `inprogress`) todo items sorted by due date and priority.
- **FR-13**: `todo://items/{id}` Resource: Read-only context feed (`application/json`) for a specific todo item payload identified by ID.
- **FR-14**: `todo://summary` Resource: Read-only Markdown context overview (`text/markdown`) detailing total counts by status, counts by priority, and list of overdue items.
- **FR-15**: `todo://priorities/{priority}` Resource: Read-only context feed (`application/json`) filtering todo items matching `{priority}`.
- **FR-16**: `daily_planning` Prompt: Structured prompt template injecting `todo://summary` to guide LLM daily scheduling and highlight urgent/overdue items.
- **FR-17**: `triage_backlog` Prompt: Structured prompt template evaluating backlog tasks for vague descriptions, priority adjustments, and duplicates.
- **FR-18**: `task_breakdown` Prompt: Structured prompt template fetching `todo://items/{todo_id}` and guiding decomposition into actionable sub-tasks formatted as `create_todo` tool calls.

### NonFunctional Requirements

- **NFR-1**: Latency & Performance: SSE request/response roundtrip latency for tools MUST be under 100ms for local database operations (excluding external LLM inference time).
- **NFR-2**: MCP Protocol Compliance: Full adherence to the Model Context Protocol specification over SSE transport, introspectable via standard `tools/list`, `resources/list`, and `prompts/list`.
- **NFR-3**: Input Validation & Error Handling: All tool parameters validated via Pydantic schemas; invalid parameters return standard MCP `isError: true` tool results with human-readable error descriptions rather than crashing the server.
- **NFR-4**: Security & Networking: Support standard CORS headers, authentication middleware pass-through, and HTTPS termination behind an AWS Application Load Balancer (ALB).
- **NFR-5**: Resilience & Connection Keep-Alive: Regular ping/heartbeats (every 15 to 30 seconds) to prevent proxy, ALB, or client timeouts on idle connections; database disconnections captured cleanly without dropping SSE connection.

### Additional Requirements

- **AD-1 (Lightweight Ports & Adapters Isolation)**: Handlers in `src/project_qwe/mcp/todos/` must only interact with `src/project_qwe/services/todo_service.py` and `src/project_qwe/schemas/todo.py`. Direct imports of SQLAlchemy ORM models from `src/project_qwe/models/` or raw database queries inside MCP handlers are strictly prohibited.
- **AD-2 (FastAPI ASGI Sub-Application Mounting)**: The Todo MCP server must be mounted directly as a dedicated ASGI sub-application using `app.mount("/mcp/todos", mcp_todos_app)` in `src/project_qwe/main.py`. It must interface with `mcp.server.sse.SseServerTransport` directly and must not be wrapped inside standard FastAPI `APIRouter` route definitions.
- **AD-3 (Operation-Scoped Database Sessions)**: The persistent SSE connection loop must hold zero open database connections. Database sessions must be acquired from `SessionLocal()` strictly via context managers for the execution span of individual tool calls or dynamic resource resolutions, and closed immediately upon completion.
- **AD-4 (Multi-Instance In-Memory Session Stickiness)**: Because `SseServerTransport` maintains session stream writers in process memory, multi-instance deployments behind an AWS ALB must configure cookie-based target group stickiness on `/mcp/*`. Single-instance and local development environments require no stickiness configuration.
- **AD-5 (Service-Owned Search and Multi-Field Sorting)**: Keyword text search (`search_todos`) and multi-criteria sorting (`due_at` ascending with nulls last, followed by `priority` descending) must be implemented inside `src/project_qwe/services/todo_service.py` at the SQL query level, and consumed directly by `src/project_qwe/mcp/todos/tools.py`.
- **Directory Hierarchy**: Server implementation must live under `src/project_qwe/mcp/todos/` (`server.py`, `tools.py`, `resources.py`, `prompts.py`, `__main__.py`).

### UX Design Requirements

*(None — headless backend protocol service without a web UI layer).*

### FR Coverage Map

- **FR-1**: Epic 1 (Core Python MCP SDK >=2.2.0 dependency and virtual environment configuration)
- **FR-2**: Epic 1 (Exclusive Server-Sent Events transport without stdio)
- **FR-3**: Epic 1 (FastAPI ASGI sub-application mounting under /mcp/todos/)
- **FR-4**: Epic 1 (Operation-scoped database sessions with SessionLocal)
- **FR-5**: Epic 1 (Clean architecture isolation delegating to todo_service)
- **FR-6**: Epic 1 (list_todos tool with 5-20 bounds and due_at/priority default sort)
- **FR-7**: Epic 1 (get_todo_by_id tool by integer ID)
- **FR-8**: Epic 1 (search_todos tool by title/description query)
- **FR-9**: Epic 1 (create_todo tool)
- **FR-10**: Epic 1 (update_todo tool)
- **FR-11**: Epic 1 (delete_todo tool)
- **FR-12**: Epic 1 (todo://items active tasks context feed)
- **FR-13**: Epic 1 (todo://items/{id} single task context feed)
- **FR-14**: Epic 1 (todo://summary markdown status overview)
- **FR-15**: Epic 1 (todo://priorities/{priority} filtered items feed)
- **FR-16**: Epic 1 (daily_planning guided prompt)
- **FR-17**: Epic 1 (triage_backlog guided prompt)
- **FR-18**: Epic 1 (task_breakdown guided prompt)

## Epic List

### Epic 1: Todo MCP Server Integration
Enable AI agent clients (Claude Desktop, VS Code with Copilot / Roo Code, Cursor) to manage, search, inspect, and prioritize tasks over a high-performance SSE transport mounted into FastAPI, adhering to clean architecture invariants.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18.
**NFRs covered:** NFR-1, NFR-2, NFR-3, NFR-4, NFR-5.

*Planned sequential stories within Epic 1:*
1. **Story 1.1**: Scaffold MCP module structure, files, and transport placeholders (`server.py`, `tools.py`, `resources.py`, `prompts.py`, `__main__.py`, FastAPI mount).
2. **Story 1.2**: Extend `todo_service` and implement the 6 MCP Tools (`list_todos`, `get_todo_by_id`, `search_todos`, `create_todo`, `update_todo`, `delete_todo`).
3. **Story 1.3**: Implement MCP Context Resources (`todo://items`, `todo://items/:id`, `todo://summary`, `todo://priorities/:priority`).
4. **Story 1.4**: Implement Guided Prompts (`daily_planning`, `triage_backlog`, `task_breakdown`).
5. **Story 1.5**: Implement automated tests (unit, integration & SSE end-to-end) and verify MCP compliance.

---

## Epic 1: Todo MCP Server Integration

Enable AI agent clients (Claude Desktop, VS Code with Copilot / Roo Code, Cursor) to manage, search, inspect, and prioritize tasks over a high-performance SSE transport mounted into FastAPI, adhering to clean architecture invariants.

### Story 1.1: Scaffold MCP Module Directory, File Placeholders, and FastAPI SSE Mount

As a Developer,
I want the foundational MCP module directory structure, file placeholders, and FastAPI ASGI mount configured without business logic,
So that subsequent stories can implement tools, resources, and prompts within a compliant architectural scaffold.

**Acceptance Criteria:**

- **Given** the project repository at `src/project_qwe/`
- **When** the MCP module layout is created under `src/project_qwe/mcp/todos/`
- **Then** the directory structure contains `__init__.py`, `server.py`, `tools.py`, `resources.py`, `prompts.py`, and `__main__.py`
- **And** each file contains empty type annotations and placeholder functions/classes without implementing actual business logic (FR-1, AD-1)
- **And** `src/project_qwe/main.py` mounts the MCP sub-application at `/mcp/todos` using `app.mount("/mcp/todos", mcp_todos_app)` (FR-3, AD-2)
- **And** starting the development server with `uv run uvicorn project_qwe.main:app` boots successfully without import errors or router registration conflicts

### Story 1.2: Implement Service Extensions and MCP CRUD & Search Tools

As an AI Agent / Developer,
I want to execute task CRUD operations and keyword searches via validated MCP tools,
So that I can inspect, create, update, and delete tasks directly from conversation and IDE workflows.

**Acceptance Criteria:**

- **Given** the `todo_service` in `src/project_qwe/services/todo_service.py`
- **When** `todo_service` is updated with `search_todos(db: Session, query: str, limit: int = 5)` and multi-field sorting support in `get_todos` for `due_at` (asc, nulls last) and `priority` (desc)
- **Then** database queries execute at the SQL level and comply with clean architecture without importing models into the MCP layer (FR-5, AD-1, AD-5)
- **And** the MCP server registers 6 tools conforming to PRD schemas: `list_todos` with `per_page` bounded between 5 and 20 (FR-6), `get_todo_by_id` (FR-7), `search_todos` (FR-8), `create_todo` (FR-9), `update_todo` (FR-10), and `delete_todo` (FR-11)
- **And** all tool parameters are validated via Pydantic; invalid parameters return MCP tool results with `isError: true` and descriptive error text rather than unhandled 500 exceptions (NFR-3)
- **And** each tool invocation executes within an operation-scoped `with SessionLocal() as db:` context, closing the session immediately after completion (FR-4, AD-3)

### Story 1.3: Implement MCP Context Resources

As an AI Agent,
I want to read live todo context feeds via standardized URI endpoints (`todo://items`, `todo://items/:id`, `todo://summary`, `todo://priorities/:priority`),
So that I have zero-overhead real-time grounding in active tasks, overdue items, and task priorities.

**Acceptance Criteria:**

- **Given** the MCP server running in `src/project_qwe/mcp/todos/`
- **When** an MCP client queries resources via `resources/list` and `resources/read`
- **Then** `todo://items` returns an `application/json` array of all active (`created`, `inprogress`) todos ordered by due date and priority (FR-12)
- **And** `todo://items/{id}` returns the JSON representation of the specific todo item or returns an error if not found (FR-13)
- **And** `todo://summary` returns a formatted `text/markdown` document containing total counts by status, priority breakdown, and a bulleted list of overdue tasks (FR-14)
- **And** `todo://priorities/{priority}` returns a JSON array of active todos filtered by the specified priority (`urgent`, `high`, `medium`, `low`) (FR-15)
- **And** resource readers resolve data using operation-scoped database sessions without persisting connection handles (AD-3)

### Story 1.4: Implement MCP Guided Workflow Prompts

As an AI Agent User,
I want pre-engineered MCP prompt templates for daily planning, backlog triage, and task breakdown,
So that the agent can guide structured planning sessions and systematically decompose high-level tasks.

**Acceptance Criteria:**

- **Given** an MCP client connected to `/mcp/todos/sse`
- **When** the client lists prompts via `prompts/list`
- **Then** the server exposes `daily_planning` (FR-16), `triage_backlog` (FR-17), and `task_breakdown` (FR-18)
- **And** `daily_planning` accepts an optional `focus_area` argument, embeds `todo://summary`, and outputs instructions for a 3-5 item daily task agenda
- **And** `triage_backlog` accepts an optional `limit` argument (default 20), loads created/backlog tasks, and instructs the agent to audit clarity and due dates
- **And** `task_breakdown` accepts a required `todo_id` integer argument, fetches the parent task context, and instructs the model to generate sub-tasks formatted as actionable `create_todo` tool calls

### Story 1.5: Implement Automated Test Suite and Protocol Compliance Verification

As a Software Engineer,
I want comprehensive unit tests, service integration tests, and end-to-end SSE transport tests,
So that the Todo MCP Server is verified against MCP specification standards, schema validations, and performance latency targets.

**Acceptance Criteria:**

- **Given** the completed MCP server, tools, resources, and prompts
- **When** tests are run via `uv run pytest tests/test_mcp_todos.py`
- **Then** unit tests verify Pydantic input validation, bounds checking (`per_page` 5-20), and error formatting (`isError: true`) for all 6 tools
- **And** unit tests verify resource generation formatting and prompt argument parsing
- **And** integration tests verify database session isolation and rollback on simulated errors
- **And** an asynchronous SSE integration test verifies client connection to `/mcp/todos/sse`, endpoint discovery, and successful JSON-RPC message dispatch to `/mcp/todos/messages`
- **And** all tests pass 100% within CI test runners (NFR-1, NFR-2, NFR-3)


