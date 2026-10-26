---
title: 'Story 1.5: Implement Automated Test Suite and Protocol Compliance Verification'
type: 'feature'
created: '2026-10-26'
status: 'done'
baseline_revision: 'bf0163cf6a8a541ea2a70d26915e0939d5c36ed4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/implementation-artifacts/epic-1-context.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** While individual modules have local unit tests, the system lacks a unified protocol compliance and end-to-end SSE transport verification suite validating full JSON-RPC sessions, endpoint discovery, roundtrip latency (<100ms), and error boundaries over the mounted FastAPI ASGI app as specified in PRD NFR-1 through NFR-3.

**Approach:** Implement `tests/test_mcp_todos.py` providing a comprehensive, self-contained test suite that verifies unit validation on all 6 tools, resource/prompt parsing, database session isolation and rollback, and asynchronous SSE client integration over real transport sessions.

## Boundaries & Constraints

**Always:**
- Execute test assertions against the outermost interfaces: real SSE client connections, MCP protocol JSON-RPC messages, and public tool/resource/prompt endpoints (NFR-2).
- Verify roundtrip tool execution latency stays under 100ms for local database operations (NFR-1).
- Ensure error responses for invalid parameters format as standard MCP tool errors with `isError: true` rather than crashing the SSE stream or throwing HTTP 500s (NFR-3).
- Strictly verify AD-1 compliance: zero imports from `project_qwe.models` in `src/project_qwe/mcp/`.
- Ensure all tests run and pass cleanly via `uv run pytest tests/test_mcp_todos.py` and across the entire project test suite `uv run pytest`.

**Block If:**
- Testing SSE transport requires modifying production dependencies in ways that compromise security or runtime performance.
- Database migrations need to be altered (existing applied migrations are immutable).

**Never:**
- Leave background server threads or unclosed SSE connections running after test execution.
- Mock the internal MCP protocol transport when performing end-to-end compliance tests; test against actual SSE client/server handshakes.
- Import ORM models in MCP adapters (AD-1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SSE Client Connection & Discovery | Connect to `/mcp/todos/sse` via `sse_client` | Establishes session, receives endpoint, performs `initialize()`, introspects all 6 tools, 2 resources + 2 templates, 3 prompts | Clean disconnect on session exit |
| SSE Roundtrip Tool Invocation | `call_tool("create_todo", {"title": "SSE Task"})` over SSE | Returns success response with created todo JSON; roundtrip latency < 100ms | Validates NFR-1 (<100ms) |
| Tool Input Validation Bounds | `call_tool("list_todos", {"per_page": 25})` over SSE | Returns tool result with `isError: True` and validation message | Does not drop connection or return HTTP 500 (NFR-3) |
| Resource Reading over SSE | `read_resource("todo://items")` over SSE | Returns array of active todos with MIME `application/json` | Empty list if no active tasks |
| Prompt Rendering over SSE | `get_prompt("daily_planning", {})` over SSE | Returns prompt messages containing live markdown summary | Handles empty DB gracefully |
| DB Session Isolation & Rollback | Simulated DB operational failure during tool/resource call | Session rolled back, connection closed, returns MCP error | Zero connection leak, server stays responsive |
| Protocol Schema Compliance | Check `tools/list`, `resources/list`, `prompts/list` | All schemas conform to JSON-RPC 2.0 and Model Context Protocol spec | NFR-2 adherence |

</intent-contract>

## Code Map

- `tests/test_mcp_todos.py` -- Comprehensive automated test suite implementing unit validation, bounds checking, resource/prompt formatting, session isolation, latency benchmarks, and async SSE client transport tests.
- `src/project_qwe/mcp/todos/server.py` -- Optimized SSE mount endpoint (`message_path="/messages/"`) to prevent 307 redirects during client message posts.

## Tasks & Acceptance

**Execution:**
- `src/project_qwe/mcp/todos/server.py` -- Ensure `message_path="/messages/"` is configured -- Prevents 307 Temporary Redirects on client JSON-RPC message posts over SSE.
- `tests/test_mcp_todos.py` -- Implement unified test suite covering unit validations, session rollbacks, protocol compliance, latency benchmarks, and live SSE client-server integration -- Fulfills Story 1.5 acceptance criteria and NFR-1, NFR-2, NFR-3.

**Acceptance Criteria:**
- Given the completed MCP server, tools, resources, and prompts, when tests are run via `uv run pytest tests/test_mcp_todos.py`, then all tests pass with 100% success rate.
- Unit tests verify Pydantic input validation, bounds checking (`per_page` 5–20), and error formatting (`isError: true`) for all 6 tools.
- Unit tests verify resource generation formatting and prompt argument parsing.
- Integration tests verify database session isolation and rollback on simulated errors.
- An asynchronous SSE integration test verifies client connection to `/mcp/todos/sse`, endpoint discovery, and successful JSON-RPC message dispatch to `/mcp/todos/messages/`.
- Roundtrip tool latency over SSE is verified to stay under 100ms for local database operations (NFR-1).
- Full test suite passes via `uv run pytest`.

## Spec Change Log

## Review Triage Log

### 2026-10-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` Aligned SSE assertions with Python MCP SDK client types (`is_error` property and string-valued prompt arguments).

## Design Notes

Using an ephemeral localhost port (`127.0.0.1:0`) in a background Uvicorn daemon thread enables testing true end-to-end SSE protocol compliance using the official `mcp.client.sse.sse_client` and `ClientSession`. This tests the actual HTTP server, ASGI routing, SSE stream writer, JSON-RPC session establishment, and message dispatch pipeline without mocking network protocols.

## Verification

**Commands:**
- `uv run pytest tests/test_mcp_todos.py` -- expected: All unit, integration, and SSE end-to-end tests pass cleanly.
- `uv run pytest` -- expected: Full test suite passes across the entire project.

## Auto Run Result

### Summary of Implemented Change
Implemented the unified MCP test suite in `tests/test_mcp_todos.py` satisfying all acceptance criteria for Story 1.5 and NFR-1, NFR-2, and NFR-3. The suite provides unit parameter validation on all 6 tools, resource formatting and prompt parsing checks, database session isolation and rollback integration tests, and true asynchronous end-to-end SSE transport integration tests with latency benchmarking (<100ms) and error resilience verification. Configured `message_path="/messages/"` on `mcp_server.sse_app` to eliminate 307 temporary redirects on JSON-RPC message dispatches.

### Files Changed
- `tests/test_mcp_todos.py` -- Created comprehensive test suite containing 12 unit, integration, protocol introspectability, and async SSE transport tests.
- `src/project_qwe/mcp/todos/server.py` -- Updated SSE mount `message_path` to `"/messages/"` to prevent HTTP 307 redirects during client message posts.
- `_bmad-output/implementation-artifacts/spec-1-5-implement-automated-test-suite-and-protocol-compliance-verif.md` -- Finalized specification with triage log and auto run result.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- Updated story status and epic status to `done`.

### Review Findings Breakdown
- Patches applied: 1 (aligned client CallToolResult property `is_error` and string-valued prompt arguments)
- Items deferred: 0
- Items rejected: 0

### Follow-up Review Recommendation
- Recommendation: `false`
- Breakdown: 0 high, 1 medium, 0 low. Weighted score = 3 (threshold is 5).

### Verification Performed
- `uv run pytest tests/test_mcp_todos.py` (12 passed in 0.86s)
- `uv run pytest` (174 passed cleanly in 1.60s across all test modules)

### Residual Risks
- None. The MCP server is fully verified against the protocol specification, adheres to clean architecture boundaries (AD-1, AD-3), and passes all automated test suites.
