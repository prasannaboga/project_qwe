---
title: "Todo Model Context Protocol (MCP) Server PRD"
status: draft
created: 2026-09-25
updated: 2026-09-25
version: "1.0.0"
author: "Prasannaboga"
---

# PRD: Todo Model Context Protocol (MCP) Server

## 0. Document Purpose
This Product Requirements Document (PRD) establishes the comprehensive functional, technical, and architectural requirements for implementing a dedicated **Model Context Protocol (MCP) Server** for the Todo domain in `project_qwe`. 

Targeted at software engineers, system architects, and LLM agent integrators, this PRD specifies how existing business logic in `src/project_qwe/services/todo_service.py` is exposed as standardized MCP **Tools**, **Resources**, and **Prompts** conforming to the Anthropic Model Context Protocol specification (2024-11-05).

---

## 1. Vision & Problem Statement

### 1.1 Problem Statement
Currently, `project_qwe` exposes todo management exclusively via a FastAPI REST API (`src/project_qwe/api/todos.py`). While suitable for traditional web and mobile clients, autonomous AI agents (e.g. Claude Desktop, Cursor, Antigravity, local LLM CLI tools) lack a native, standard protocol interface to:
1. Discover and invoke todo actions with structured, validated tool definitions.
2. Read live task lists and status summaries directly as standardized context resources without making ad-hoc HTTP calls.
3. Leverage pre-engineered domain prompts (e.g., daily prioritization, backlog triage) that guide agent reasoning.

### 1.2 Vision & Key Objectives
Deliver a high-performance, compliant Python MCP server that unlocks programmatic AI interaction with the Todo ecosystem:
* **Tool Parity**: Expose full CRUD capabilities with strict parameter validation matching `src/project_qwe/schemas/todo.py`.
* **Standard Resources**: Provide read-only context feeds (`todo://...`) with mime-type awareness for zero-overhead LLM grounding.
* **Domain Prompts**: Provide opinionated, parameterizable prompts for daily planning, triage, and task synthesis.
* **Clean Architecture Compliance**: Strictly invoke `todo_service` methods and use explicit database sessions from `project_qwe.config.database`, adhering to project architectural rules.

---

## 2. Target Users & Jobs To Be Done (JTBD)

### 2.1 Target Personas
1. **The AI Assistant (Direct Consumer)**: An LLM instance executing tasks on behalf of the user, querying context and performing actions via JSON-RPC.
2. **The Developer / Power User (End User)**: Developers using tools like Claude Desktop, Cursor, or CLI agents who want their agent to manage their daily todo list directly in their active project database.
3. **The System Integrator**: An engineer configuring multi-agent workflows connecting external task pipelines to `project_qwe`.

### 2.2 Jobs To Be Done (JTBD)
* **JTBD-1 (Context Grounding)**: When I am starting my workday in an LLM agent, I want the agent to automatically inspect my current tasks and priorities so it can suggest what to work on without me manually pasting todo lists.
* **JTBD-2 (Action Execution)**: When discussing a project with an agent, I want the agent to create, update, or resolve todos in real-time as action items emerge from the conversation.
* **JTBD-3 (Task Triage & Organization)**: When tasks accumulate, I want to trigger a guided agent workflow to re-prioritize and categorize overdue or in-progress tasks.

### 2.3 Key User Journeys

#### UJ-1: Daily Planning with AI Assistant
* **Persona & Context**: Alex, a software engineer opening Claude Desktop at 9:00 AM connected to the `project_qwe` Todo MCP server.
* **Entry State**: MCP client connects via stdio. Server capabilities (Tools, Prompts, Resources) are negotiated.
* **Path**:
  1. Alex invokes the prompt `daily_planning`.
  2. The client fetches the prompt template and auto-attaches resource `todo://summary` and `todo://active`.
  3. The agent analyzes the tasks, highlights 2 urgent items, and suggests tackling the oldest in-progress item first.
  4. Alex replies: "Mark item #4 as inprogress and change priority to high."
  5. The agent calls tool `update_todo(todo_id=4, status="inprogress", priority="high")`.
* **Climax**: Tool returns the updated `TodoResponse`. Agent confirms the change.
* **Resolution**: Alex's database is updated; the day's roadmap is clear in 60 seconds.

#### UJ-2: Autonomous Meeting Action Item Extraction
* **Persona & Context**: Agent reading meeting notes in Cursor/IDE.
* **Entry State**: Agent identifies 3 distinct action items from markdown text.
* **Path**:
  1. Agent calls tool `create_todo` with `title="Add DB migration for user table"`, `priority="high"`, `due_at="2026-09-30T18:00:00Z"`.
  2. Server validates input schema, writes to database via `todo_service.create_todo`, and returns created todo details with assigned ID.
* **Climax**: Agent receives ID #12 and outputs a confirmed checklist to the user.

---

## 3. Glossary

* **MCP (Model Context Protocol)**: Open standard protocol created by Anthropic allowing AI models to interact with local or remote external tools, resources, and prompts over JSON-RPC 2.0.
* **MCP Server**: The server process exposing endpoints/capabilities over a communication transport (`stdio` or `SSE`).
* **Tool**: An executable function with a JSON Schema-defined signature that the LLM model can choose to call.
* **Resource**: Read-only contextual data identified by a URI (e.g. `todo://items`) that an MCP client can attach or read into context.
* **Prompt**: Pre-defined conversational template with optional arguments exposed by the MCP server to guide LLM workflows.
* **TodoStatus**: Enumeration of task lifecycle states: `created`, `inprogress`, `completed`.
* **TodoPriority**: Enumeration of task urgency: `urgent`, `high`, `medium`, `low`.

---

## 4. Features & Functional Requirements

### 4.1 MCP Server Core Runtime & Architecture (FR-CORE)
* **FR-1**: The MCP server MUST be implemented using the official Python MCP SDK (`mcp` package) and run within the project's Python 3.14 virtual environment.
* **FR-2**: The server MUST support `stdio` transport as the default primary transport for local agent execution (CLI, Claude Desktop, Cursor).
* **FR-3**: The server MAY optionally provide a Server-Sent Events (`SSE`) transport over HTTP for remote or networked agent access.
* **FR-4**: The server MUST isolate database sessions per request/invocation using `project_qwe.config.database.SessionLocal()`, ensuring sessions are properly committed and closed without leaking connections.
* **FR-5**: The server MUST NOT implement business logic or direct database queries in tool handlers; all domain operations MUST call `src/project_qwe/services/todo_service.py`.

---

### 4.2 MCP Tools Specification (FR-TOOLS)
The MCP server MUST expose the following 5 tools, matching the capabilities of the REST API:

#### FR-6: `list_todos` Tool
* **Description**: Retrieve a paginated list of todo items with optional sorting and priority filtering.
* **Input Schema**:
  * `page` (integer, optional, default: 1, min: 1, max: 100): Page number.
  * `per_page` (integer, optional, default: 20, min: 1, max: 100): Number of items per page.
  * `sort` (string, optional, default: "created_at:desc"): Sort order in `<field>:<dir>` format (allowed fields: `id`, `title`, `status`, `priority`, `created_at`, `updated_at`, `due_at`; directions: `asc`, `desc`).
  * `priority` (string, optional, enum: `["urgent", "high", "medium", "low"]`): Filter by priority.
* **Output**: JSON string containing items array (`id`, `title`, `description`, `status`, `priority`, `due_at`, `created_at`, `updated_at`), `page`, `per_page`, `has_next_page`.

#### FR-7: `get_todo` Tool
* **Description**: Fetch full details of a specific todo item by its unique integer identifier.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo item to retrieve.
* **Output**: JSON representation of the todo item, or an MCP error message if not found.

#### FR-8: `create_todo` Tool
* **Description**: Create a new todo item in the system.
* **Input Schema**:
  * `title` (string, required, min_length: 1): Title of the task.
  * `description` (string, optional, max_length: 1000): Detailed task notes.
  * `status` (string, optional, default: "created", enum: `["created", "inprogress", "completed"]`): Initial status.
  * `priority` (string, optional, default: "medium", enum: `["urgent", "high", "medium", "low"]`): Priority level.
  * `due_at` (string ISO-8601 datetime, optional): Target completion timestamp.
* **Output**: JSON representation of the newly created todo item with generated `id` and timestamps.

#### FR-9: `update_todo` Tool
* **Description**: Update fields of an existing todo item.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo to modify.
  * `title` (string, optional, min_length: 1): Updated title.
  * `description` (string, optional, max_length: 1000): Updated description.
  * `status` (string, optional, enum: `["created", "inprogress", "completed"]`): New status.
  * `priority` (string, optional, enum: `["urgent", "high", "medium", "low"]`): New priority.
  * `due_at` (string ISO-8601 datetime, optional): New due date.
* **Output**: JSON representation of the updated todo item.

#### FR-10: `delete_todo` Tool
* **Description**: Permanently delete a todo item by ID.
* **Input Schema**:
  * `todo_id` (integer, required): ID of the todo item to delete.
* **Output**: Success confirmation message (`{"success": true, "message": "Todo deleted successfully"}`) or error if not found.

---

### 4.3 MCP Resources Specification (FR-RES)
The server MUST expose read-only contextual resources providing real-time data to LLMs:

* **FR-11: `todo://items`**:
  * **MIME Type**: `application/json`
  * **Content**: The list of all active (non-completed) todo items sorted by priority and due date.
* **FR-12: `todo://items/{id}`**:
  * **MIME Type**: `application/json`
  * **Content**: Specific todo item payload identified by URI template parameter `{id}`.
* **FR-13: `todo://summary`**:
  * **MIME Type**: `text/markdown`
  * **Content**: Aggregated high-level overview detailing total counts by status (`created`, `inprogress`, `completed`), counts by priority, and list of items past their `due_at` timestamp.
* **FR-14: `todo://priorities/{priority}`**:
  * **MIME Type**: `application/json`
  * **Content**: Filtered list of todo items matching `{priority}` (`urgent`, `high`, `medium`, `low`).

---

### 4.4 MCP Prompts Specification (FR-PROMPT)
The server MUST expose structured prompt templates that guide LLM interactions:

* **FR-15: `daily_planning` Prompt**:
  * **Arguments**:
    * `focus_area` (string, optional): Specific project area or topic to prioritize.
  * **Behavior**: Injects the `todo://summary` resource and instructs the model to act as an executive assistant, reviewing overdue and high-priority items, and proposing an optimal 3-5 item schedule for today.
* **FR-16: `triage_backlog` Prompt**:
  * **Arguments**:
    * `limit` (integer, optional, default: 20): Number of backlog items to evaluate.
  * **Behavior**: Loads backlog tasks (`status="created"`) and guides the agent to identify vague titles, recommend priority adjustments based on due dates, and identify duplicates.
* **FR-17: `task_breakdown` Prompt**:
  * **Arguments**:
    * `todo_id` (integer, required): ID of a high-level task.
  * **Behavior**: Fetches the task description via `todo://items/{todo_id}` and prompts the model to break it down into actionable sub-tasks, formatting them as ready-to-execute `create_todo` tool calls.

---

## 5. Non-Functional Requirements (NFR)

* **NFR-1 (Latency)**: Stdio tool execution latency MUST be under 50ms for local database operations (excluding LLM generation time).
* **NFR-2 (Standard Compliance)**: Full adherence to MCP 2024-11-05 JSON-RPC specification. Tools, resources, and prompts must be introspectable via standard `tools/list`, `resources/list`, and `prompts/list` methods.
* **NFR-3 (Input Validation & Error Handling)**: All tool parameters must be validated via Pydantic schemas before reaching `todo_service`. Invalid parameters MUST return standard MCP `isError: true` tool results with human-readable error descriptions rather than crashing the server.
* **NFR-4 (Security)**: The server runs with the database privileges of the active user. When operating via `stdio`, communication is confined to local process pipes without network exposure.
* **NFR-5 (Resilience)**: Database connection failures must be captured cleanly and reported as protocol errors without dropping the `stdio` connection.

---

## 6. Architecture & Implementation Guidelines

### 6.1 Directory & Module Structure
The implementation will reside in:
* Server Entrypoint: `src/project_qwe/mcp/server.py`
* Tool Handlers: `src/project_qwe/mcp/tools.py`
* Resource Handlers: `src/project_qwe/mcp/resources.py`
* Prompt Definitions: `src/project_qwe/mcp/prompts.py`
* CLI Launcher: `src/project_qwe/mcp/__main__.py` (executable via `uv run python -m project_qwe.mcp`)

### 6.2 Architectural Constraints (from AGENTS.md)
1. **No direct ORM queries in MCP handlers**: Handlers must call `todo_service` methods (`get_todos`, `get_todo_by_id`, `create_todo`, `update_todo`, `delete_todo`).
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
3. **No modification to existing applied migrations**.

---

## 7. Assumptions & Open Decisions

* `[ASSUMPTION]` The Python `mcp` library (`mcp>=1.2.0`) will be added to `pyproject.toml` dependencies via `uv add mcp`.
* `[ASSUMPTION]` Stdio transport will be the default CLI entrypoint, compatible with Claude Desktop configuration:
  ```json
  {
    "mcpServers": {
      "todos": {
        "command": "uv",
        "args": ["run", "python", "-m", "project_qwe.mcp"]
      }
    }
  }
  ```
* `[DECISION NEEDED]` Confirm if SSE transport should be bundled in the same CLI via a `--transport sse --port 8001` flag or if stdio satisfies current needs.
