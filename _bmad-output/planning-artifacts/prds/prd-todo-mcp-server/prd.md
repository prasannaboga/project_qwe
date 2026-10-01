---
title: "Todo Model Context Protocol (MCP) Server PRD"
status: final
created: 2026-09-25
updated: 2026-10-01
version: "1.1.0"
author: "Prasannaboga"
---

# PRD: Todo Model Context Protocol (MCP) Server

## 0. Document Purpose
This Product Requirements Document (PRD) establishes the comprehensive functional, technical, and architectural requirements for implementing a dedicated **Model Context Protocol (MCP) Server** for the Todo domain in `project_qwe`.

Targeted at software engineers, system architects, and LLM agent integrators, this PRD specifies how existing business logic in `src/project_qwe/services/todo_service.py` is exposed as standardized MCP **Tools**, **Resources**, and **Prompts** conforming to the Model Context Protocol specification. The server operates exclusively over **Server-Sent Events (SSE)** hosted directly within the application's FastAPI runtime, ready for containerized deployment and horizontal scaling in AWS.

---

## 1. Vision & Problem Statement

### 1.1 Problem Statement
Currently, `project_qwe` exposes todo management exclusively via a FastAPI REST API (`src/project_qwe/api/todos.py`). While suitable for traditional web and mobile clients, autonomous AI agents (e.g., Claude Desktop, VS Code with Copilot / Roo Code, Cursor, and cloud-hosted agent frameworks) require a standardized protocol interface to:
1. Discover and invoke todo actions using structured, validated JSON-RPC tool definitions.
2. Read live task summaries and lists directly as standardized context resources without writing ad-hoc HTTP scrapers.
3. Leverage pre-engineered domain prompts (e.g., daily prioritization, backlog triage) that guide agent reasoning.
4. Connect seamlessly over standard network HTTP endpoints without requiring local shell/process pipes (`stdio`).

### 1.2 Vision & Key Objectives
Deliver a high-performance, SSE-based Python MCP server mounted inside `project_qwe`'s FastAPI application:
* **Exclusively Network-Native (SSE Transport)**: Provide an HTTP Server-Sent Events transport endpoint (`/mcp/todos/sse`) compatible with VS Code, Claude Desktop, Cursor, and AWS-hosted agent infrastructure. Local process-pipe (`stdio`) transport is deprecated and not supported.
* **Tool Parity & Enhanced Discovery**: Expose full CRUD capabilities plus dedicated text search (`search_todos`), with pagination calibrated for LLM context limits (5 to 20 items) and sensible defaults (sorted by `due_at` and `priority`).
* **Standard Resources**: Provide read-only context feeds (`todo://...`) with MIME-type awareness for zero-overhead LLM grounding.
* **Domain Prompts**: Provide opinionated, parameterizable prompts for daily planning, triage, and task breakdown.
* **Modular Multi-Server Architecture**: Isolate the server under `src/project_qwe/mcp/todos/` to cleanly accommodate future domain MCP servers under `src/project_qwe/mcp/<domain>/`.
* **Clean Architecture Compliance**: Strictly invoke `todo_service` methods and use explicit database sessions from `project_qwe.config.database`, adhering to project architectural rules.

---

## 2. Target Users & Jobs To Be Done (JTBD)

### 2.1 Target Personas
1. **The AI Assistant (Direct Consumer)**: An LLM instance executing tasks on behalf of the user, querying context and performing actions via JSON-RPC over SSE.
2. **The Developer / Power User (End User)**: Developers using VS Code, Cursor, or Claude Desktop configured to connect to the remote or local HTTP MCP endpoint.
3. **The Multi-Agent Orchestrator / Cloud Consumer**: Cloud-based autonomous agents and task runners deployed in AWS communicating with `project_qwe` over HTTP/SSE.

### 2.2 Jobs To Be Done (JTBD)
* **JTBD-1 (Context Grounding)**: When starting a workday or coding session, I want my IDE/agent to automatically inspect active tasks and priorities via an SSE connection so it can guide work without manual copy-pasting.
* **JTBD-2 (Action Execution & Search)**: While conversing with an agent, I want it to create, inspect, update, or search existing tasks by title/description in real-time.
* **JTBD-3 (Task Triage & Organization)**: When tasks accumulate, I want to trigger a guided prompt workflow to re-prioritize and organize backlog tasks.

### 2.3 Key User Journeys

#### UJ-1: Daily Planning in VS Code / Claude Desktop via HTTP SSE
* **Persona & Context**: Alex, a software engineer opening VS Code connected to the project's FastAPI server (`http://localhost:8000/mcp/todos/sse`).
* **Entry State**: The client initiates an SSE connection. Capabilities (Tools, Resources, Prompts) are negotiated over the event stream.
* **Path**:
  1. Alex invokes the prompt `daily_planning`.
  2. The client fetches the prompt template and auto-attaches resource `todo://summary` and `todo://active`.
  3. The agent analyzes tasks, spots 2 urgent items, and suggests tackling the nearest due item.
  4. Alex replies: "Mark task #4 as inprogress and change priority to high."
  5. The agent calls tool `update_todo(todo_id=4, status="inprogress", priority="high")`.
* **Climax**: Tool execution returns the updated `TodoResponse`. Agent confirms completion.
* **Resolution**: The PostgreSQL/SQLite database updates; daily plan is organized in under a minute.

#### UJ-2: Conversational Task Search and Creation
* **Persona & Context**: Cloud AI agent assisting in sprint planning.
* **Entry State**: Agent needs to check if a task already exists before creating a duplicate.
* **Path**:
  1. Agent invokes `search_todos(query="migration", limit=5)`.
  2. The server queries `todo_service` and returns matching todos.
  3. Finding no existing task for user table migrations, the agent calls `create_todo(title="Add DB migration for user table", priority="high", due_at="2026-10-15T18:00:00Z")`.
* **Climax**: Agent receives the newly created task with ID #12.

---

## 3. Glossary

* **MCP (Model Context Protocol)**: Open standard protocol allowing AI models to interact with tools, resources, and prompts over JSON-RPC 2.0.
* **SSE (Server-Sent Events)**: HTTP-based unidirectional streaming protocol where the client opens an event-stream connection (`GET /sse`) and submits client-to-server requests via HTTP POST (`/messages`).
* **MCP Server**: The server exposing capabilities over SSE.
* **Tool**: An executable function with a JSON Schema-defined signature callable by the LLM.
* **Resource**: Read-only contextual data identified by a URI (e.g. `todo://items`) that an MCP client attaches or reads into context.
* **Prompt**: Pre-defined conversational template with optional arguments exposed by the MCP server to guide LLM reasoning.
* **TodoStatus**: Lifecycle states: `created`, `inprogress`, `completed`.
* **TodoPriority**: Urgency levels: `urgent`, `high`, `medium`, `low`.

---

## 4. Features & Functional Requirements

### 4.1 MCP Server Core Runtime & Architecture (FR-CORE)
* **FR-1**: The MCP server MUST be built using the official Python MCP SDK (`mcp[cli]>=2.2.0,<2.3.0`), which is already declared and managed in `pyproject.toml`.
* **FR-2**: The server MUST use **Server-Sent Events (SSE)** as its sole transport mechanism. Local process-pipe (`stdio`) transport is explicitly out of scope.
* **FR-3**: The SSE transport MUST be mounted directly inside the primary FastAPI application (`src/project_qwe/main.py`) under the routing prefix `/mcp/todos/`:
  * `GET /mcp/todos/sse`: Establishes the persistent SSE stream to the client.
  * `POST /mcp/todos/messages`: Receives JSON-RPC client messages (tool calls, prompt requests, resource fetches).
* **FR-4**: The server MUST isolate database sessions per request/invocation using `project_qwe.config.database.SessionLocal()`, ensuring sessions are committed or rolled back and closed cleanly without leaking connections.
* **FR-5**: The server MUST NOT implement domain business logic or direct ORM queries inside tool or resource handlers; all domain operations MUST delegate to `src/project_qwe/services/todo_service.py`.

---

### 4.2 MCP Tools Specification (FR-TOOLS)
The MCP server MUST expose 6 dedicated tools matching and extending domain capabilities:

#### FR-6: `list_todos` Tool
* **Description**: Retrieve a paginated list of todo items with default sorting optimized for LLM planning.
* **Input Schema**:
  * `page` (integer, optional, default: 1, min: 1, max: 100): Page number.
  * `per_page` (integer, optional, default: 10, min: 5, max: 20): Number of items per page (bounded between 5 and 20 to fit LLM context windows).
  * `sort` (string, optional, default: "due_at:asc,priority:desc"): Sort order directive. Defaults to items nearest their due date first, then highest priority (`urgent` &rarr; `high` &rarr; `medium` &rarr; `low`).
  * `priority` (string, optional, enum: `["urgent", "high", "medium", "low"]`): Optional filter by priority.
* **Output**: JSON string containing `items` array (`id`, `title`, `description`, `status`, `priority`, `due_at`, `created_at`, `updated_at`), `page`, `per_page`, and `has_next_page`.

#### FR-7: `get_todo_by_id` Tool
* **Description**: Fetch complete details of a specific todo item by its unique integer identifier.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo item to retrieve.
* **Output**: JSON representation of the todo item, or an MCP error result if not found.

#### FR-8: `search_todos` Tool
* **Description**: Search for todo items matching text in their title or description. Extensible for additional filter parameters in future iterations.
* **Input Schema**:
  * `query` (string, required, min_length: 1): Search keywords to match against title and description (case-insensitive substring match).
  * `limit` (integer, optional, default: 5, min: 1, max: 20): Maximum number of matching items to return.
* **Output**: JSON string containing an array of matching todo items, ordered by relevance or update timestamp.

#### FR-9: `create_todo` Tool
* **Description**: Create a new todo item in the database.
* **Input Schema**:
  * `title` (string, required, min_length: 1): Title of the task.
  * `description` (string, optional, max_length: 1000): Detailed task notes.
  * `status` (string, optional, default: "created", enum: `["created", "inprogress", "completed"]`): Initial status.
  * `priority` (string, optional, default: "medium", enum: `["urgent", "high", "medium", "low"]`): Priority level.
  * `due_at` (string ISO-8601 datetime, optional): Target completion timestamp.
* **Output**: JSON representation of the newly created todo item with generated `id` and timestamps.

#### FR-10: `update_todo` Tool
* **Description**: Update fields of an existing todo item.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo to modify.
  * `title` (string, optional, min_length: 1): Updated title.
  * `description` (string, optional, max_length: 1000): Updated description.
  * `status` (string, optional, enum: `["created", "inprogress", "completed"]`): New status.
  * `priority` (string, optional, enum: `["urgent", "high", "medium", "low"]`): New priority.
  * `due_at` (string ISO-8601 datetime, optional): New due date.
* **Output**: JSON representation of the updated todo item.

#### FR-11: `delete_todo` Tool
* **Description**: Permanently delete a todo item by ID.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo item to delete.
* **Output**: Confirmation object (`{"success": true, "message": "Todo deleted successfully"}`) or error if not found.

---

### 4.3 MCP Resources Specification (FR-RES)
The server MUST expose read-only contextual resources providing real-time data to LLMs:

* **FR-12: `todo://items`**:
  * **MIME Type**: `application/json`
  * **Content**: The list of all active (`created`, `inprogress`) todo items sorted by due date and priority.
* **FR-13: `todo://items/{id}`**:
  * **MIME Type**: `application/json`
  * **Content**: Specific todo item payload identified by URI template parameter `{id}`.
* **FR-14: `todo://summary`**:
  * **MIME Type**: `text/markdown`
  * **Content**: Aggregated markdown summary detailing total counts by status, counts by priority, and list of items past their `due_at` timestamp.
* **FR-15: `todo://priorities/{priority}`**:
  * **MIME Type**: `application/json`
  * **Content**: Filtered list of todo items matching `{priority}` (`urgent`, `high`, `medium`, `low`).

---

### 4.4 MCP Prompts Specification (FR-PROMPT)
The server MUST expose structured prompt templates that guide LLM interactions:

* **FR-16: `daily_planning` Prompt**:
  * **Arguments**:
    * `focus_area` (string, optional): Specific project area or topic to prioritize.
  * **Behavior**: Injects `todo://summary` and guides the model to act as an executive assistant, highlighting urgent/overdue items and proposing an optimal 3-5 item daily schedule.
* **FR-17: `triage_backlog` Prompt**:
  * **Arguments**:
    * `limit` (integer, optional, default: 20): Number of backlog items to evaluate.
  * **Behavior**: Loads backlog tasks (`status="created"`) and guides the agent to identify vague descriptions, suggest priority adjustments based on due dates, and flag duplicates.
* **FR-18: `task_breakdown` Prompt**:
  * **Arguments**:
    * `todo_id` (integer, required): ID of a high-level task.
  * **Behavior**: Fetches the task description via `todo://items/{todo_id}` and prompts the model to break it down into actionable sub-tasks formatted as ready-to-execute `create_todo` tool calls.

---

## 5. Non-Functional Requirements (NFR)

* **NFR-1 (Latency & Performance)**: SSE request/response roundtrip latency for tools MUST be under 100ms for local database operations (excluding external LLM inference time).
* **NFR-2 (MCP Protocol Compliance)**: Full adherence to the Anthropic Model Context Protocol specification over SSE transport. Tools, resources, and prompts must be introspectable via standard `tools/list`, `resources/list`, and `prompts/list`.
* **NFR-3 (Input Validation & Error Handling)**: All tool parameters must be validated via Pydantic schemas before reaching `todo_service`. Invalid parameters MUST return standard MCP `isError: true` tool results with clear error descriptions rather than terminating the connection or throwing 500 errors.
* **NFR-4 (Security & Networking)**: The SSE and message endpoints must support standard CORS headers, authentication middleware (if configured), and secure transmission (HTTPS) when behind an AWS Application Load Balancer (ALB).
* **NFR-5 (Resilience & Connection Keep-Alive)**: The SSE transport MUST implement regular ping/keepalive heartbeats (e.g. every 15-30 seconds) to prevent proxy, ALB, or client timeouts on idle connections. Database disconnections must return error responses without closing the SSE connection.

---

## 6. Architecture & Implementation Guidelines

### 6.1 Directory & Module Structure
To support multiple MCP domain servers (e.g. Todos, Users, Analytics) within `project_qwe`, the code is organized modularly under `src/project_qwe/mcp/`:

```
src/project_qwe/mcp/
├── __init__.py
└── todos/
    ├── __init__.py
    ├── server.py       # MCP Server instance, SSE transport setup & route integration
    ├── tools.py        # Tool definitions & input schema validation
    ├── resources.py    # Context resource URI handlers
    ├── prompts.py      # Guided prompt definitions
    └── __main__.py     # Optional standalone runner for local testing
```

### 6.2 FastAPI Mount & Integration
The MCP server is mounted directly into the FastAPI application in `src/project_qwe/main.py`:

```python
from fastapi import FastAPI
from project_qwe.mcp.todos.server import mcp_todos_app

app = FastAPI(...)
# Mount MCP SSE application under /mcp/todos
app.mount("/mcp/todos", mcp_todos_app)
```

Clients interact via:
* **Event Stream**: `GET /mcp/todos/sse`
* **Message Channel**: `POST /mcp/todos/messages?session_id=<id>`

### 6.3 Architectural Constraints (from AGENTS.md)
1. **No direct ORM queries in MCP handlers**: Handlers must call `todo_service` functions (`get_todos`, `get_todo_by_id`, `search_todos`, `create_todo`, `update_todo`, `delete_todo`).
2. **Explicit DB Sessions**: Wrap each tool/resource call in a context-managed session:
   ```python
   from project_qwe.config.database import SessionLocal

   def handle_tool(...):
       db = SessionLocal()
       try:
           return todo_service.some_method(db, ...)
       finally:
           db.close()
   ```
3. **No modification to existing applied migrations**: If `search_todos` or compound sorting requires indexing or schema enhancements, author a new Alembic migration.

### 6.4 AWS Deployment & Scaling Considerations
* **Horizontal Scaling**: Since todos state is stored in the database, the FastAPI container instances remain stateless.
* **ALB Configuration**: AWS Application Load Balancer idle timeout should be configured to at least 300 seconds, combined with the MCP SSE keepalive heartbeat.
* **Sticky Sessions**: In multi-instance deployments behind an ALB, enable cookie-based sticky sessions for the `/mcp/todos/` path so the client's POST messages route to the specific instance holding the active SSE stream session.

---

## 7. Assumptions & MCP Client Configurations

### 7.1 Resolved Assumptions & Decisions
* `[RESOLVED]` Transport is exclusively Server-Sent Events (SSE) over HTTP; stdio is dropped.
* `[RESOLVED]` Python `mcp[cli]>=2.2.0,<2.3.0` is already in `pyproject.toml`.
* `[RESOLVED]` Mounted directly in FastAPI at `/mcp/todos/` for unified AWS deployment and scaling.
* `[RESOLVED]` `get_todo` is split into `get_todo_by_id` and `search_todos(query, limit)`.
* `[RESOLVED]` `list_todos` page size is bounded between 5 and 20 (default: 10), defaulting to `due_at` and `priority` ordering.

### 7.2 Client Configuration Examples

#### VS Code (GitHub Copilot / Roo Code / Cline)
```json
{
  "mcpServers": {
    "todos": {
      "url": "http://127.0.0.1:8000/mcp/todos/sse",
      "transport": "sse"
    }
  }
}
```

#### Claude Desktop Configuration (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "todos": {
      "url": "http://127.0.0.1:8000/mcp/todos/sse"
    }
  }
}
```
