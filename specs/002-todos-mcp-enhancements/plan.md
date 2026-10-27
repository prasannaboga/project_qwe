# Implementation Plan: Todos MCP API Enhancements

**Feature**: `002-todos-mcp-enhancements`
**Planning date**: 2026-10-27
**Current checkout branch**: `001-todo-priority` (create the feature branch before implementation)

## Technical Context

| Concern | Decision |
|---|---|
| Runtime and SDK | Python 3.14, `mcp==2.2.0`, high-level `mcp.server.mcpserver.MCPServer`, mounted through its legacy SSE app at `/mcp/todos` |
| Current boundaries | MCP adapters open operation-scoped `SessionLocal()` sessions and call `todo_service`; MCP code does not import ORM models (AD-1 test) |
| Input schemas | Use `typing.Annotated` plus Pydantic `Field` metadata on tool parameters, and `MCPServer.tool()` title/description/`ToolAnnotations` |
| Progress | Convert write tools to async handlers with injected `Context`; use `await asyncio.sleep()` only for a disabled-by-default demo delay and `asyncio.to_thread()` for synchronous SQLAlchemy service calls |
| Resource template | Retain and enrich the already registered `todo://items/{id}` JSON template; it already delegates to `todo_service.get_todo_by_id` and maps missing rows to `ResourceNotFoundError` |
| List pagination | Add an MCP-tool-level opaque, versioned keyset cursor to `list_todos`; retain current `page`/`per_page` offset mode for compatibility. MCP protocol `nextCursor` cannot page an arbitrary tool-call result. |
| Storage | No schema changes and no migration expected. Cursor traversal uses existing `created_at` plus `id` deterministic ordering and bounded SQL queries. |
| Testing | pytest unit tests for helpers/services and SSE integration tests with `ClientSession`, including progress callback capture and multi-page traversal |

## Architecture and Affected Modules

```text
MCP client
  └─ SSE MCPServer (/mcp/todos)
       ├─ tools.py: schema metadata, progress-aware write adapters, cursor inputs/results
       ├─ resources.py: existing todo://items/{id} template metadata and read adapter
       └─ server.py: registration remains the composition root
              └─ todo_service.py: reusable keyset query helper; synchronous DB transactions
                     └─ Todo model / existing indexes
```

Affected implementation files are `src/project_qwe/mcp/todos/tools.py`, `resources.py`, `server.py` only if shared wiring is needed, `src/project_qwe/services/todo_service.py`, `src/project_qwe/config/settings.py`, `.env.example`, `src/project_qwe/mcp/todos/README.md`, and `tests/test_mcp_todos.py` plus mirrored service tests. `main.py`, REST routes, ORM models, and Alembic migrations are not in scope.

## Constitution Check

| Principle | Status | Plan response |
|---|---|---|
| I. Python 3.14 / uv | Pass | No dependency is added; retain the locked SDK. |
| II. Layered architecture | Pass | MCP handlers remain transport adapters and call services; no ORM model imports or business logic duplication. |
| III. pytest coverage | Pass | Add service and SSE integration coverage for all requirements and failure paths. |
| IV. Migration integrity | Pass | No persisted model or schema change is planned. |
| V. API compatibility | Pass | REST behavior is unchanged. Existing MCP resource URI and list offset inputs remain supported; added metadata/cursor fields are additive. |
| VI. Maintainability | Pass | Delay limits and cursor version are named configuration/constants; public additions receive docstrings. |
| VII. Configuration/secret hygiene | Pass | Demo delay is loaded through `pydantic-settings`; no secret or production delay default is introduced. |

**Pre-design gate:** pass. The SDK limitation below is intentional and documented, rather than masked by a misleading protocol claim.

## Research Decisions

See [research.md](research.md) for the source-backed rationale.

1. Use SDK-supported `Annotated[..., Field(...)]`, decorator metadata, and tool annotations to expose descriptive JSON schemas.
2. Use `Context.report_progress()` from async write handlers; a value of zero disables the demo delay, while non-zero configuration must be 30–45 seconds.
3. Treat the registered `todo://items/{id}` as the requested ID resource template; refine and verify it instead of adding a duplicate URI.
4. Keep MCP discovery pagination separate from Todo-list pagination. The high-level server cannot attach protocol `nextCursor` to `tools/call`; use a domain cursor with a fixed keyset order for cursor mode.

## Detailed Design

### Rich tool schemas

For `create_todo`, `update_todo`, `delete_todo`, and `list_todos`, replace bare primitive annotations with explicit `Annotated`/`Field` contracts: human-readable titles, descriptions, defaults, enum values, date-time format, string limits, and numeric bounds. Use tool-level `title`, complete operation description, and `ToolAnnotations`:

- `list_todos`: read-only and idempotent.
- `create_todo`: non-read-only, non-idempotent, non-destructive.
- `update_todo`: non-read-only, non-idempotent, non-destructive.
- `delete_todo`: non-read-only, destructive, idempotent for a successfully deleted ID only if application semantics deliberately support repeated deletes; current not-found behavior means leave `idempotent_hint` unset/false.

Keep the current JSON response shapes and validation messages where practical. `Context` is dependency-injected and must not appear in a client-facing input schema.

### Resource template

Keep `@mcp_server.resource("todo://items/{id}", ...)` to avoid breaking existing MCP clients. Add explicit name/title/description/annotations and verify `resources/templates/list` exposes it. The handler parses a positive integer ID, opens one session, delegates to `get_todo_by_id`, serializes through `TodoResponse`, returns `application/json`, and raises the established `ResourceNotFoundError` for an absent Todo. Do not add a second equivalent URI.

### Write progress and demo delay

Add `MCP_TODOS_PROGRESS_DELAY_SECONDS` to settings with default `0`. Valid configured values are `0` (off) or inclusive `30..45`; invalid values fail settings validation with a clear operator-facing message. Write handlers follow this order:

1. Validate and construct request data; report `1/3` (validated).
2. If enabled, report that the demonstration wait started, await `asyncio.sleep(delay)`, then report `2/3` (ready to persist). No DB session is open during this wait.
3. Invoke the existing synchronous service in `asyncio.to_thread` with a fresh operation-scoped session; only after it returns successfully report `3/3` (completed) and serialize the result.

On validation, persistence, or not-found failure, raise the existing MCP error and do not emit a success progress event. Keep transaction ownership and rollback behavior inside the existing service/session boundary. The README must state clients request/capture progress through their SDK callback and that the delay is demo-only.

### Cursor pagination for `list_todos`

The SDK’s protocol pagination applies to `tools/list`, `resources/list`, `resources/templates/list`, and `prompts/list`; it does not define a continuation result for `tools/call`. Do not replace the current high-level server with a low-level server merely to page discovery lists.

Add a **tool-contract** `cursor: str | None` and additive `next_cursor: str | null` in the `list_todos` JSON result. Preserve existing `page`, `per_page`, `sort`, and `priority` behavior when `cursor` is absent. Cursor mode:

- accepts `per_page` only in its existing 5–20 bound and rejects `page` combined with a cursor;
- uses a fixed, documented order `created_at DESC, id DESC`, independent of legacy `sort`, and rejects an incompatible explicit sort;
- encodes a version, cursor-mode marker, priority filter, page size, and last `(created_at, id)` boundary as URL-safe base64 JSON; the token contains no sensitive data;
- decodes strictly, rejects malformed/unknown-version/mismatched filter, page-size, or sort tokens as `ToolError`, and never treats a client-invented cursor as a REST page number;
- calls a new service keyset helper with `WHERE (created_at < boundary_created_at) OR (created_at = boundary_created_at AND id < boundary_id)`, `LIMIT per_page + 1`, and returns `next_cursor=None` only on the final page.

This provides deterministic order and avoids whole-collection loads and offset scans. As with any non-snapshot traversal, inserts/updates that move rows across the boundary during a traversal are not globally snapshot-consistent; document that trade-off. REST pagination stays unchanged.

## Security, Errors, Performance, Compatibility

- Inputs remain Pydantic-validated before database use. Cursor decoding has strict size/type/version checks; errors omit internal stack traces.
- Cursor tokens are opaque continuation values, not authorization credentials; no customer data or database connection data is encoded.
- The delay is opt-in configuration and async. Thread offloading prevents synchronous SQLAlchemy calls from blocking the ASGI event loop; no session is retained while awaiting.
- Resource missing IDs retain their current MCP resource-not-found semantics; tool missing IDs retain `ToolError` behavior.
- Additive MCP metadata and results preserve old clients. Legacy `list_todos` offset output stays intact. Existing REST API and migrations are untouched.

## Post-Design Constitution Check

Pass. The design introduces neither a dependency nor a database change, preserves all existing layer boundaries, keeps production delay disabled, and makes compatibility behavior explicit. Implementation must add the specified unit and integration tests before merge.

## Task Ordering and Parallelism

See [tasks.md](tasks.md). Foundational settings/helper work precedes write tool changes and cursor wiring. Once the shared metadata convention is established, resource-template verification and progress work can proceed independently of keyset pagination tests. Documentation and final regression verification follow all behavior changes.

## Delivery Stories

1. **US1 (P1) — Discoverable Todo tools**: An MCP client can inspect create, update, delete, and list tools and understand every required/optional field, constraint, and operation behavior without external documentation.
2. **US2 (P1) — Individual Todo resource**: An MCP client can discover and read the existing individual-Todo resource template with consistent JSON and not-found behavior.
3. **US3 (P2) — Observable Todo mutations**: A progress-capable MCP client receives truthful, non-blocking create/update/delete progress while demonstration delay remains disabled in normal operation.
4. **US4 (P2) — Bounded Todo-list traversal**: An MCP client can follow opaque `list_todos` cursor continuations through deterministic, bounded pages, while legacy MCP offset mode and REST pagination remain unchanged.
