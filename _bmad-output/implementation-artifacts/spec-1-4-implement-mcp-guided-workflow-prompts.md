---
title: 'Story 1.4: Implement MCP Guided Workflow Prompts'
type: 'feature'
created: '2026-10-26'
status: 'done'
baseline_revision: 'b39c5e9cbfb7532bd584a8cccbd5c7f8be7a747a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/implementation-artifacts/epic-1-context.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** AI agent users lack structured guidance and standard interaction templates to conduct daily task planning, triage unrefined backlog items, and systematically decompose complex tasks into executable sub-tasks.

**Approach:** Implement and register the three MCP prompt templates (`daily_planning`, `triage_backlog`, `task_breakdown`) in `src/project_qwe/mcp/todos/prompts.py` using `@mcp_server.prompt(...)` backed by service methods in `src/project_qwe/services/todo_service.py` with operation-scoped DB sessions.

## Boundaries & Constraints

**Always:**
- Strictly delegate all database queries to `src/project_qwe/services/todo_service.py` (AD-1, FR-5).
- Never import SQLAlchemy ORM models from `src/project_qwe/models/` into `src/project_qwe/mcp/`; import all schemas and enums from `src/project_qwe/schemas/todo.py` (AD-1).
- Acquire database sessions within operation-scoped context managers `with SessionLocal() as db:` closing the session immediately after rendering the prompt (FR-4, AD-3).
- Register prompts with the official Python MCP SDK using `@mcp_server.prompt(...)` decorators.
- Ensure `src/project_qwe/mcp/todos/server.py` imports `prompts` so prompt registrations take effect upon server load.
- `daily_planning` embeds `todo://summary` context and accepts an optional `focus_area: str | None = None` argument (FR-16).
- `triage_backlog` accepts an optional `limit: int = 20` argument, loads unstarted backlog items (`status="created"`), and outputs clarity/prioritization review instructions (FR-17).
- `task_breakdown` accepts a required `todo_id: int` argument, fetches the parent task context, and outputs instructions formatting sub-tasks as executable `create_todo` tool calls (FR-18).

**Block If:**
- MCP prompt schema or arguments require breaking changes to Starlette/FastAPI sub-app routing.
- Schema modifications require changes to existing applied database migrations.

**Never:**
- Import or query SQLAlchemy ORM models directly inside `src/project_qwe/mcp/` (AD-1).
- Hold open database connections across client prompt inspection requests.
- Silently ignore missing parent tasks in `task_breakdown`; raise an explicit `ValueError` when a requested todo is not found.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Daily planning default | `daily_planning()` | Prompt text embedding markdown summary from `todo://summary` and instructing 3-5 item daily task agenda selection | Fallback summary if empty DB |
| Daily planning with focus area | `daily_planning(focus_area="Backend Architecture")` | Prompt text embedding summary and highlighting "Backend Architecture" focus area | No error expected |
| Triage backlog default | `triage_backlog(limit=20)` with backlog tasks in DB | Prompt text listing backlog tasks (`status="created"`) and auditing clarity, due dates, priority, duplication | Friendly notice if backlog is empty |
| Triage backlog custom limit | `triage_backlog(limit=5)` with >5 backlog tasks | Prompt text listing at most 5 backlog tasks | Clamps/validates limit (1-50) |
| Task breakdown existing ID | `task_breakdown(todo_id=1)` with existing task | Prompt text displaying parent task title, description, priority, due date, and instructing sub-task creation via `create_todo` calls | No error expected |
| Task breakdown missing ID | `task_breakdown(todo_id=999999)` with no matching task | Raises `ValueError` indicating task not found | Raised as ValueError for MCP rendering error |
| Task breakdown invalid ID type | `task_breakdown(todo_id="abc")` | Rejects non-integer ID | MCP / Pydantic validation error |
| DB failure during prompt rendering | OperationalError / DB failure | Catches exception, rolls back session, raises `ValueError` | Clean session close without hanging connection |

</intent-contract>

## Code Map

- `src/project_qwe/services/todo_service.py` -- Add `get_backlog_todos(db, limit=20)` to retrieve unstarted backlog items (`status="created"`) ordered by semantic priority urgency and creation date.
- `src/project_qwe/mcp/todos/prompts.py` -- Implement and decorate 3 MCP prompts (`daily_planning`, `triage_backlog`, `task_breakdown`) using `@mcp_server.prompt(...)` and operation-scoped sessions.
- `src/project_qwe/mcp/todos/server.py` -- Import `prompts` module alongside `tools` and `resources` to trigger decorator registrations on startup.
- `tests/services/test_todo_service.py` -- Unit tests for `get_backlog_todos`.
- `tests/mcp/test_prompts.py` -- Comprehensive unit and integration tests verifying `list_prompts`, `get_prompt`, argument handling, edge cases, and AD-1 compliance.
- `tests/mcp/test_scaffold.py` -- Update `test_prompts_placeholders` to verify active prompt calls.

## Tasks & Acceptance

**Execution:**
- `src/project_qwe/services/todo_service.py` -- Add `get_backlog_todos` -- Retrieves `status="created"` items ordered by priority urgency and creation date.
- `src/project_qwe/mcp/todos/prompts.py` -- Implement `daily_planning`, `triage_backlog`, `task_breakdown` using `@mcp_server.prompt(...)` and operation-scoped DB sessions -- Exposes the 3 MCP prompts adhering to PRD FR-16 through FR-18 and AD-1.
- `src/project_qwe/mcp/todos/server.py` -- Import `project_qwe.mcp.todos.prompts` -- Ensures prompts are registered on MCP server startup.
- `tests/services/test_todo_service.py` -- Add tests for `get_backlog_todos` -- Validates backlog status filtering and limit.
- `tests/mcp/test_prompts.py` -- Create test suite covering all 3 prompts, arguments, edge cases, and AD-1 AST import verification -- Ensures end-to-end correctness of MCP prompt handlers.
- `tests/mcp/test_scaffold.py` -- Update `test_prompts_placeholders` to reflect implemented prompts -- Maintains non-regression of test scaffold.

**Acceptance Criteria:**
- Given an MCP client connected to `/mcp/todos/sse`, when the client lists prompts via `prompts/list`, then `daily_planning` (FR-16), `triage_backlog` (FR-17), and `task_breakdown` (FR-18) are exposed with expected argument schemas.
- Given `daily_planning`, when rendered without arguments, it embeds the live markdown summary and instructions for selecting a 3–5 item daily agenda; when rendered with `focus_area`, it incorporates that focus area into the guidance.
- Given `triage_backlog`, when rendered, it lists created/backlog tasks up to `limit` (default 20) and instructs the agent to audit clarity, missing due dates, priority alignment, and duplication.
- Given `task_breakdown`, when rendered with a valid `todo_id`, it embeds the parent task context and instructs the agent to decompose it into sub-tasks formatted as actionable `create_todo` tool calls; when rendered with a non-existent ID, it raises a `ValueError`.
- Given any prompt invocation, database sessions are acquired via `with SessionLocal() as db:` and closed immediately upon completion (AD-3).
- Given `src/project_qwe/mcp/`, when scanned with AST, zero imports from `project_qwe.models` exist (AD-1).

## Spec Change Log

## Review Triage Log

### 2026-10-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` Handled MCPServer exception wrapping in `tests/mcp/test_prompts.py` and implemented full prompt test suite.

## Design Notes

1. `daily_planning(focus_area: str | None = None) -> str`:
   - Fetches markdown summary via `todo_service.get_todo_summary_markdown(db)`.
   - Prompt instructions:
     - Review the status, priority distribution, and overdue items.
     - Select 3–5 realistic high-impact tasks for today.
     - If focus area is provided, prioritize tasks aligning with the focus area.
     - Detail the rationale and execution sequence for the selected tasks.

2. `triage_backlog(limit: int = 20) -> str`:
   - Fetches backlog tasks via `todo_service.get_backlog_todos(db, limit=limit)`.
   - Formats backlog list with IDs, titles, priorities, and creation dates.
   - Prompt instructions:
     - Check titles and descriptions for clarity and completeness.
     - Identify tasks missing deadlines or having misaligned priorities.
     - Flag redundant tasks or suggest merging/deleting them.
     - Recommend tasks ready for execution vs tasks needing breakdown.

3. `task_breakdown(todo_id: int) -> str`:
   - Fetches parent task via `todo_service.get_todo_by_id(db, todo_id)`.
   - If not found, raises `ValueError(f"Todo with ID {todo_id} not found")`.
   - Formats parent task metadata.
   - Prompt instructions:
     - Decompose the parent task into discrete sub-tasks.
     - Format each sub-task as an executable `create_todo` tool call with title, description, priority, and due_at.

## Verification

**Commands:**
- `uv run pytest tests/services/test_todo_service.py` -- expected: All service tests pass including backlog tests.
- `uv run pytest tests/mcp/test_prompts.py` -- expected: All MCP prompt tests pass including registration, execution, and AST checks.
- `uv run pytest` -- expected: Full test suite passes (all 148+ tests).

## Auto Run Result

### Summary of Implemented Change
Implemented the three guided MCP prompts (`daily_planning`, `triage_backlog`, and `task_breakdown`) registered via `@mcp_server.prompt(...)` in `src/project_qwe/mcp/todos/prompts.py`. Added supporting service method `get_backlog_todos` in `src/project_qwe/services/todo_service.py` to retrieve unstarted tasks ordered by semantic priority urgency and creation date. Implemented operation-scoped database sessions with `with SessionLocal() as db:` and verified strict compliance with AD-1 (zero imports from `project_qwe.models` in MCP module).

### Files Changed
- `src/project_qwe/services/todo_service.py` -- Added `get_backlog_todos` with priority urgency ordering and limit validation.
- `src/project_qwe/mcp/todos/prompts.py` -- Implemented and registered 3 MCP prompts (`daily_planning`, `triage_backlog`, `task_breakdown`) with schema annotations and error handling.
- `src/project_qwe/mcp/todos/server.py` -- Imported `prompts` module to trigger decorator registrations on application startup.
- `tests/mcp/test_scaffold.py` -- Updated placeholder checks to verify functional MCP prompts.
- `tests/mcp/test_prompts.py` -- Created comprehensive test suite with 13 tests covering prompt discovery, argument schemas, execution, error handling, and AD-1 compliance.
- `tests/services/test_todo_service.py` -- Added unit tests for `get_backlog_todos` filtering and ordering.
- `_bmad-output/implementation-artifacts/spec-1-4-implement-mcp-guided-workflow-prompts.md` -- Finalized specification with triage log and auto run result.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- Updated story status to `done`.

### Review Findings Breakdown
- Patches applied: 1 (handled nested exception inspection in test_prompts.py)
- Items deferred: 0
- Items rejected: 0

### Follow-up Review Recommendation
- Recommendation: `false`
- Breakdown: 0 high, 1 medium, 0 low. Weighted score = 3 (threshold is 5).

### Verification Performed
- `uv run pytest tests/services/test_todo_service.py` (34 passed)
- `uv run pytest tests/mcp/test_prompts.py` (13 passed)
- `uv run pytest tests/mcp/test_scaffold.py` (10 passed)
- `uv run pytest` (162 passed cleanly)

### Residual Risks
- None. Prompts execute safely within operation-scoped sessions and conform strictly to MCP specification and PRD FR-16 through FR-18.
