---
title: 'Story 1.2: Implement Service Extensions and MCP CRUD & Search Tools'
type: 'feature'
created: '2026-10-17'
status: 'done'
baseline_revision: '2aefe564177fe237d30b07c6e7ad0642223e9117'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Autonomous AI agents require structured MCP tool endpoints to search, list, retrieve, create, update, and delete tasks over SSE, but `todo_service` currently lacks text substring search and multi-field urgency sorting, and `src/project_qwe/mcp/todos/tools.py` contains only unimplemented placeholders.

**Approach:** Implement `search_todos` and compound sorting (including priority urgency ordering and nulls-last `due_at`) in `todo_service.py`, then implement and register the six MCP tools in `tools.py` using operation-scoped database sessions and Pydantic schema validation without importing ORM models into the MCP layer.

## Boundaries & Constraints

**Always:**
- Keep all business logic and query assembly in `src/project_qwe/services/todo_service.py`; MCP tool handlers in `src/project_qwe/mcp/todos/tools.py` must delegate all domain logic to the service layer (AD-1, FR-5).
- Acquire database sessions within tool functions using `with SessionLocal() as db:` from `project_qwe.config.database` so connections are scoped strictly to the execution of each tool call and never leaked into persistent SSE streams (FR-4).
- Validate all tool inputs with Pydantic schemas or type constraints, raising `ToolError` on invalid input or domain errors to yield standard MCP `isError: true` responses without crashing the SSE connection (NFR-3).
- Enforce `per_page` limits between 5 and 20 (default 10) in `list_todos` (FR-6).
- In `get_todos`, default sort to `due_at:asc,priority:desc` with `due_at` ascending sorting nulls last and priority descending ordered by urgency (`urgent` > `high` > `medium` > `low`) (FR-6).
- Preserve existing REST API endpoints, schemas, and test suite functionality without regression.

**Block If:**
- Schema changes requiring database migrations that would alter or conflict with existing applied Alembic revisions.

**Never:**
- Import SQLAlchemy ORM models from `src/project_qwe/models/` into `src/project_qwe/mcp/` (AD-1).
- Perform in-memory post-filtering or sorting for pagination or search inside MCP handlers; all filtering, searching, and sorting must occur at the SQL query level in `todo_service` (FR-5).
- Use local process-pipe (`stdio`) transport; tools must be exposed via the existing mounted ASGI SSE server (FR-2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List todos default | `list_todos()` with tasks in DB | Returns JSON with items sorted by `due_at:asc` (nulls last) then priority urgency (`urgent` > `high` > `medium` > `low`), `page: 1`, `per_page: 10`, `has_next_page` | No error |
| List todos invalid per_page | `list_todos(per_page=4)` or `list_todos(per_page=25)` | Rejection with clear error message | Raises `ToolError("per_page must be between 5 and 20")` |
| List todos priority filter | `list_todos(priority="urgent")` | Returns only urgent tasks matching the filter | Raises `ToolError` if invalid priority string |
| Get todo by ID found | `get_todo_by_id(todo_id=1)` (task exists) | Returns JSON representation of task 1 | No error |
| Get todo by ID missing | `get_todo_by_id(todo_id=999)` (non-existent) | Error result indicating task not found | Raises `ToolError("Todo with id 999 not found")` |
| Search todos match | `search_todos(query="meeting", limit=5)` | Returns up to 5 matching tasks ordered by `updated_at:desc` | No error |
| Search todos empty query | `search_todos(query="   ")` | Rejection for empty search query | Raises `ToolError("query must not be empty")` |
| Search todos out of bounds limit | `search_todos(query="test", limit=50)` | Rejection for limit > 20 | Raises `ToolError("limit must be between 1 and 20")` |
| Create todo success | `create_todo(title="Buy milk", priority="high")` | Creates task, commits DB, returns created task JSON | Raises `ToolError` on invalid inputs |
| Update todo partial | `update_todo(todo_id=1, status="inprogress")` | Updates status of task 1, leaves other fields intact | Raises `ToolError("Todo with id 1 not found")` if missing |
| Delete todo success | `delete_todo(todo_id=1)` (task exists) | Deletes task 1, returns `{"success": true, "message": "..."}` | Raises `ToolError("Todo with id 1 not found")` if missing |

</intent-contract>

## Code Map

- `src/project_qwe/services/todo_service.py` -- Add `search_todos(db, query, limit)` and extend `get_todos` for comma-separated sort strings, priority urgency mapping, and `due_at.asc().nulls_last()`.
- `src/project_qwe/mcp/todos/tools.py` -- Register the 6 tools with `@mcp_server.tool()`, manage `SessionLocal()` lifecycle, validate inputs, call `todo_service`, serialize via `schemas/todo.py`.
- `src/project_qwe/mcp/todos/server.py` -- Import `project_qwe.mcp.todos.tools` to ensure tool registration when the server app is instantiated.
- `tests/services/test_todo_service.py` -- Add unit tests for `search_todos`, compound sorting, priority urgency sorting, and `nulls_last`.
- `tests/mcp/test_tools.py` -- Unit tests verifying direct invocation and error handling of all 6 tools, session scoping, and AD-1 import restrictions.
- `tests/mcp/test_scaffold.py` -- Update `test_tools_placeholders` to reflect that tools are now implemented functions rather than `NotImplementedError` stubs.

## Tasks & Acceptance

**Execution:**
- `src/project_qwe/services/todo_service.py` -- Implement `search_todos` and update `get_todos` to support compound sorting, custom priority ordering via SQL `case`, and `nulls_last()` -- Enables database-level search and sorting for MCP and REST consumers.
- `tests/services/test_todo_service.py` -- Add unit tests covering `search_todos` matching, empty queries, limits, multi-field sorting, and urgency order -- Validates service extensions at the SQL query layer.
- `src/project_qwe/mcp/todos/tools.py` -- Replace `NotImplementedError` stubs with registered `@mcp_server.tool()` implementations wrapping `SessionLocal()` and calling `todo_service` -- Exposes the 6 MCP tools to agent clients.
- `src/project_qwe/mcp/todos/server.py` -- Import `project_qwe.mcp.todos.tools` to trigger tool registration upon server load -- Ensures tools are registered with `mcp_server`.
- `tests/mcp/test_tools.py` -- Create comprehensive test suite for all 6 tools, verifying happy path, boundary validation, error formatting (`ToolError`), session closing, and AD-1 compliance -- Ensures full test coverage for MCP tools.
- `tests/mcp/test_scaffold.py` -- Update `test_tools_placeholders` to assert tools are callable and return valid responses instead of raising `NotImplementedError` -- Maintains consistency across test suites.

**Acceptance Criteria:**
- Given a database containing tasks, when `search_todos(query="keyword", limit=5)` is called, then tasks with matching title or description are returned ordered by `updated_at:desc`.
- Given `get_todos` is called with `sort="due_at:asc,priority:desc"`, then items are ordered with earliest `due_at` first, items with null `due_at` last, and secondary sorting ordered by `urgent` > `high` > `medium` > `low`.
- Given an agent client calls `list_todos(per_page=4)`, then a `ToolError` is raised with a descriptive error message.
- Given an agent client calls `get_todo_by_id(todo_id=99999)` for a non-existent task, then a `ToolError` is raised indicating the task was not found.
- Given any tool invocation in `src/project_qwe/mcp/todos/tools.py`, then a database session is acquired from `SessionLocal()` and closed upon exit, and no modules from `project_qwe.models` are imported.

## Spec Change Log

_None._

## Review Triage Log

### 2026-10-18 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 0, low 3)
- defer: 0
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[high]` `[patch]` In `update_todo`, only populate `update_kwargs` with explicitly provided non-None arguments to prevent unintentional deletion of existing description and due date fields in `todo_service.update_todo`.
  - `[low]` `[patch]` In `todo_service.search_todos`, escape SQL LIKE wildcards (`\`, `%`, `_`) so literal search queries do not inadvertently trigger pattern matching.
  - `[low]` `[patch]` In `src/project_qwe/mcp/todos/tools.py`, clean up unused imports (`TodoPaginationResponse`), use top-level enum imports (`TodoPriority`, `TodoStatus`), and wrap database operations in `try...except` translating unexpected errors to `ToolError`.
  - `[low]` `[patch]` In `tests/mcp/test_tools.py` and `tests/services/test_todo_service.py`, add explicit test assertions for partial update field preservation and literal SQL wildcard escaping.

## Design Notes

- **Priority Urgency Mapping:** SQL enum types or string columns do not sort by semantic urgency. We use `sqlalchemy.case`:
  ```python
  priority_order = case(
      {
          TodoPriority.URGENT: 4,
          TodoPriority.HIGH: 3,
          TodoPriority.MEDIUM: 2,
          TodoPriority.LOW: 1,
      },
      value=Todo.priority,
  )
  ```
  `priority:desc` orders `urgent` (4) before `low` (1).
- **Nulls Last:** `Todo.due_at.asc().nulls_last()` ensures tasks with explicit deadlines appear ahead of unscheduled tasks.
- **MCP Tool Error Handling:** Raising `mcp.server.mcpserver.exceptions.ToolError` causes the MCP SDK to format the response as `CallToolResult(content=[TextContent(type="text", text=str(exc))], is_error=True)`, perfectly satisfying NFR-3.

## Verification

**Commands:**
- `uv run pytest tests/services/test_todo_service.py` -- expected: all service tests pass.
- `uv run pytest tests/mcp/` -- expected: all MCP scaffold and tool tests pass.
- `uv run pytest` -- expected: entire project test suite passes cleanly with zero failures.

## Auto Run Result

### Summary of implemented change
Implemented service extensions in `src/project_qwe/services/todo_service.py` (`search_todos` with case-insensitive substring search and SQL wildcard escaping, plus compound sorting support in `get_todos` including priority urgency ordering via `case` and nulls-last `due_at`), and registered/implemented all six MCP tools in `src/project_qwe/mcp/todos/tools.py` (`list_todos`, `get_todo_by_id`, `search_todos`, `create_todo`, `update_todo`, `delete_todo`) using operation-scoped database sessions (`with SessionLocal() as db:`), Pydantic schema validation, and zero direct ORM model imports (strictly adhering to AD-1).

### Files changed
- `src/project_qwe/services/todo_service.py`: Added `search_todos`, compound sorting parser `_build_sort_clauses`, and semantic priority urgency ordering with nulls-last due dates.
- `src/project_qwe/mcp/todos/tools.py`: Implemented and registered all 6 MCP tools with `@mcp_server.tool()`, context-managed sessions, schema validation, and safe partial updating.
- `src/project_qwe/mcp/todos/server.py`: Imported `tools` module upon load to trigger `@mcp_server.tool()` decorators.
- `tests/services/test_todo_service.py`: Added unit test coverage for `search_todos`, limit boundaries, empty queries, compound sorting, and wildcard escaping.
- `tests/mcp/test_tools.py`: Added comprehensive test suite for all 6 tools covering happy paths, bounds, error handling, session scoping, and AD-1 compliance.
- `tests/mcp/test_scaffold.py`: Updated `test_tools_placeholders` to verify implemented tool functions return JSON output.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: Marked Story 1.2 as done.

### Review findings breakdown
- Patches applied: 4 (1 high: partial update field erasure, 3 low: wildcard escaping, error wrapping / import cleanups, test assertions)
- Items deferred: 0
- Items rejected: 4 (out-of-scope `search_todos` pagination, `status` filter on `list_todos`, timezone normalization, and retaining `created_at:desc` default on `get_todos` for REST preservation)

### Follow-up review recommendation
- Recommended: `true`
- Patched counts by severity: high: 1, medium: 0, low: 3. Score: high >= 1 triggers follow-up review recommendation.

### Verification performed
- `uv run pytest tests/services/test_todo_service.py` -> 29 passed
- `uv run pytest tests/mcp/` -> 45 passed
- `uv run pytest` -> 128 passed cleanly in 0.84s with zero failures

### Residual risks
None identified. Invariant AD-1 verified via AST analysis; all 6 MCP tools execute cleanly in-memory and register with `mcp_server`.

