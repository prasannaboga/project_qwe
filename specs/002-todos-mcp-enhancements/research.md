# Research: Todos MCP API Enhancements

**Feature**: `002-todos-mcp-enhancements` | **Date**: 2026-10-27

## SDK capability and schema metadata

**Decision**: Retain `MCPServer` and use `Annotated` Pydantic `Field` metadata, `@mcp_server.tool(title=..., description=..., annotations=...)`, and async injected `Context`.

**Rationale**: Installed `mcp==2.2.0` exposes these high-level APIs. They produce descriptive tool schemas without manually maintaining JSON Schema or introducing a new framework.

**Alternatives considered**:

- Hand-written JSON Schema: rejected because it duplicates parameter validation and drifts from Pydantic.
- Replacing high-level MCPServer: rejected because the requested schema and progress capabilities already exist.

Sources: [MCP Python SDK tools](https://py.sdk.modelcontextprotocol.io/servers/tools/), [progress handlers](https://py.sdk.modelcontextprotocol.io/handlers/progress/).

## Existing ID resource template

**Decision**: Preserve `todo://items/{id}` and improve its metadata/tests rather than creating another individual-Todo template.

**Rationale**: `resources.py` already registers a typed template, delegates to `todo_service.get_todo_by_id`, serializes with `TodoResponse`, returns JSON, and raises `ResourceNotFoundError`. The SDK discovers curly-brace templates through `resources/templates/list`.

**Alternatives considered**:

- Add `todo://todos/{todo_id}`: rejected as a duplicate, client-confusing URI and an avoidable compatibility surface.
- Move fetching logic into the resource: rejected because it violates the service boundary.

Sources: [MCP Python SDK resources](https://py.sdk.modelcontextprotocol.io/servers/resources/), [URI templates](https://py.sdk.modelcontextprotocol.io/servers/uri-templates/).

## Progress notifications and delay

**Decision**: Use async handlers, `Context.report_progress`, `asyncio.sleep`, and settings value `0` or `30..45` seconds.

**Rationale**: The context method is the SDK-supported notification path. Awaited sleep does not block the event loop. Disabling the delay by default keeps it a demonstration aid and allows fast automated tests; opening the session only after the delay avoids holding a transaction during a wait.

**Alternatives considered**:

- `time.sleep`: rejected because it blocks the event loop.
- Always delay 30 seconds: rejected as unconditional production behavior and harmful to tests.
- Report completion before commit: rejected because it can falsely claim success after a failed transaction.

Sources: [MCP Python SDK progress](https://py.sdk.modelcontextprotocol.io/handlers/progress/), [Python asyncio sleep](https://docs.python.org/3/library/asyncio-task.html#sleeping).

## Pagination

**Decision**: Implement opaque application-level keyset cursors for `list_todos`; do not call that MCP protocol-level pagination.

**Rationale**: Official SDK guidance states that protocol cursor pagination is for discovery list requests. A high-level `MCPServer` emits a complete discovery list; the low-level `Server` can supply `next_cursor` only for handlers such as `on_list_resources`. It cannot make a domain-specific `tools/call` response protocol-paginated. A `(created_at, id)` keyset boundary provides deterministic, bounded SQL pages and avoids `OFFSET` work.

**Alternatives considered**:

- Reuse REST `page`/offset only: rejected because that is not protocol pagination and degrades for deep pages.
- Rebuild the server with low-level `Server`: rejected as disproportionate, potentially disruptive to current decorators/SSE integration, and still unable to protocol-page `list_todos` results.
- Support cursor mode across every arbitrary existing sort: deferred; safe lexicographic predicates, null ordering, semantic priority ordering, and cursor encoding would add substantial complexity. Fixed cursor order is explicit and independently verifiable.

**Trade-off**: Keyset traversal is deterministic for stable rows but is not a database snapshot; concurrent updates/inserts may alter what a long traversal observes. Cursor payloads are validated opaque continuations, not security credentials.

Source: [MCP Python SDK pagination](https://py.sdk.modelcontextprotocol.io/advanced/pagination/).
