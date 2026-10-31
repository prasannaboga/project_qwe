# Tasks: Todos MCP API Enhancements

**Feature**: `002-todos-mcp-enhancements` | **Plan**: [plan.md](plan.md) | **Contract**: [contracts/todos-mcp.md](contracts/todos-mcp.md)

## Phase 1: Setup

- [ ] T001 Verify the `mcp==2.2.0` baseline, existing SSE endpoint, and tests in `pyproject.toml`, `uv.lock`, and `tests/test_mcp_todos.py`.

## Phase 2: Foundational

**Purpose**: Shared primitives required by progress and cursor work.

- [ ] T002 Add `MCP_TODOS_PROGRESS_DELAY_SECONDS` to `src/project_qwe/config/settings.py` and `.env.example`: default `0`; accept only `0` or integers 30–45 inclusive.
- [ ] T003 Add versioned strict cursor encode/decode helpers for `v`, `mode`, `priority`, `per_page`, `created_at`, and `id` in `src/project_qwe/mcp/todos/tools.py`.
- [ ] T004 Add delay-bound and malformed/unknown-version cursor tests in `tests/test_mcp_todos.py`.

## Phase 3: User Story 1 — Discoverable Todo Tools (P1) 🎯 MVP

**Goal**: An MCP client can inspect self-explanatory schemas for Todo list and mutation tools.

**Independent Test**: Over SSE, `list_tools()` reports titles, descriptions, field requiredness, defaults, enums, and bounds for all four affected tools.

- [ ] T005 [US1] Add `Annotated`/`Field` metadata to `list_todos` in `src/project_qwe/mcp/todos/tools.py`, preserving page 1–100 and per-page 5–20 constraints.
- [ ] T006 [US1] Add title, description, requiredness, nonblank title, description max 1000, enum, and ISO-8601 metadata to `create_todo` in `src/project_qwe/mcp/todos/tools.py`.
- [ ] T007 [US1] Add equivalent positive-ID and optional-update metadata to `update_todo` and `delete_todo` in `src/project_qwe/mcp/todos/tools.py`.
- [ ] T008 [US1] Add `MCPServer.tool()` titles/descriptions and correct `ToolAnnotations` in `src/project_qwe/mcp/todos/tools.py`; ensure injected `Context` is not client input.
- [ ] T009 [US1] Add tool-discovery schema and annotation assertions in `tests/test_mcp_todos.py`.

## Phase 4: User Story 2 — Individual Todo Resource (P1)

**Goal**: An MCP client can discover and read one Todo through the existing resource template.

**Independent Test**: Create a Todo, discover one `todo://items/{id}` template, read JSON, and verify invalid/missing IDs follow resource errors.

- [ ] T010 [US2] Enrich `todo://items/{id}` with name, title, description, and annotations in `src/project_qwe/mcp/todos/resources.py`, preserving URI and `application/json`.
- [ ] T011 [US2] Preserve positive-ID validation, `todo_service.get_todo_by_id`, `TodoResponse` serialization, and `ResourceNotFoundError` in `src/project_qwe/mcp/todos/resources.py`.
- [ ] T012 [US2] Add resource discovery/read SSE tests for uniqueness, JSON, invalid ID, and absent Todo in `tests/test_mcp_todos.py`.

## Phase 5: User Story 3 — Observable Todo Mutations (P2)

**Goal**: Progress-capable clients receive truthful, non-blocking mutation progress.

**Independent Test**: With delay zero, each write tool reports `1/3`, `2/3`, `3/3`; error paths never report `3/3`.

- [ ] T013 [US3] Convert create, update, and delete to async handlers with injected `Context` in `src/project_qwe/mcp/todos/tools.py`, preserving client contracts.
- [ ] T014 [US3] Implement `1/3` post-validation, optional awaited delay, `2/3` pre-persistence, and `3/3` only after success in `src/project_qwe/mcp/todos/tools.py`.
- [ ] T015 [US3] Use `asyncio.sleep` and `asyncio.to_thread` in `src/project_qwe/mcp/todos/tools.py` so no DB session crosses the delay and SQLAlchemy does not block the event loop.
- [ ] T016 [US3] Add validation, missing-ID, and forced-service-failure progress tests in `tests/test_mcp_todos.py`.
- [ ] T017 [US3] Add create/update/delete SSE progress-callback integration tests with delay forced to zero in `tests/test_mcp_todos.py`.

## Phase 6: User Story 4 — Bounded Todo-list Traversal (P2)

**Goal**: An MCP client follows opaque deterministic cursor pages without changing REST pagination.

**Independent Test**: Seed multi-page data, pass each returned cursor verbatim until `null`, and verify stable ordering, no duplicates, and invalid-token errors.

- [ ] T018 [US4] Add a `created_at DESC, id DESC` keyset helper with priority filter, `(created_at, id)` boundary, and `LIMIT per_page + 1` in `src/project_qwe/services/todo_service.py`; retain `get_todos()` offset behavior.
- [ ] T019 [US4] Add `cursor` input and additive `next_cursor` result to `list_todos` in `src/project_qwe/mcp/todos/tools.py`; preserve legacy offset mode absent a cursor.
- [ ] T020 [US4] Enforce cursor per-page 5–20, no `page` plus cursor, fixed sort, matching filter/page size, and clear invalid-token errors in `src/project_qwe/mcp/todos/tools.py`.
- [ ] T021 [US4] Add empty, boundary, multi-page, timestamp-tie, priority, and limit+1 service tests in `tests/services/test_todo_service.py`.
- [ ] T022 [US4] Add SSE traversal, final-null, no-duplicate, and invalid cursor/page/filter/sort tests in `tests/test_mcp_todos.py`.

## Phase 7: Polish and Cross-Cutting Concerns

- [ ] T023 Update schema, template, cursor, SDK-pagination distinction, and progress-demo guidance in `src/project_qwe/mcp/todos/README.md`.
- [ ] T024 Review docstrings and AD-1 layering compliance in `src/project_qwe/mcp/todos/tools.py`, `src/project_qwe/mcp/todos/resources.py`, and `src/project_qwe/services/todo_service.py`.
- [ ] T025 Run `specs/002-todos-mcp-enhancements/quickstart.md` and `uv run pytest`; verify no migration or REST-route change is required.

## Dependencies and Parallel Work

```text
T001 ─> US1 (T005–T009) ─> US2 (T010–T012) ─┐
T002 ─> US3 (T013–T017) ─────────────────────┼─> T023–T025
T003/T004 ─> US4 (T018–T022) ────────────────┘
```

US3 and US4 can run in parallel after their foundations. T021 service tests and T022 SSE tests can run in parallel after the cursor contract exists.

## Implementation Strategy

MVP is US1 after T001: schema discovery is independently valuable without persistence or transport changes. Then deliver US2, US3, and US4 incrementally; complete documentation and full regression testing last.

## Format Validation

All 25 tasks use the required checkbox, sequential ID, applicable `[US#]` label, and exact target path. Tests are included because the requested feature requires unit and integration coverage.
