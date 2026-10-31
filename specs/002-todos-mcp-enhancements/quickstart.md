# Quickstart Validation: Todos MCP API Enhancements

## Prerequisites

```bash
uv sync
uv run pytest
uv run uvicorn project_qwe.main:app --reload
```

No migration is required. Keep `MCP_TODOS_PROGRESS_DELAY_SECONDS` unset or set to `0` for normal validation. Set it to a value from `30` through `45` only for the live progress demonstration.

## Automated validation

Run the focused suite, then all tests:

```bash
uv run pytest tests/test_mcp_todos.py tests/services/test_todo_service.py
uv run pytest
```

Expected: schema discovery, resource-template discovery/read behavior, progress tests, invalid cursor tests, and multi-page cursor traversal all pass. The delay must remain disabled in automated tests.

## Schema and resource discovery

Connect an MCP SDK client to `http://127.0.0.1:8000/mcp/todos/sse`, initialize it, and call `list_tools()` and `list_resource_templates()`.

Expected:

- Affected tools expose titles/descriptions, parameter descriptions, defaults, enums, and bounds.
- `todo://items/{id}` appears exactly once in resource templates.
- Reading a created Todo at that URI produces one `application/json` response; an absent ID follows the established MCP not-found result.

## Cursor traversal

Create more than one page of Todos with distinguishable timestamps. Call `list_todos` without `cursor` in cursor mode, then repeatedly pass each returned `next_cursor` verbatim until it is `null`.

Expected:

- Each page has at most `per_page` items.
- IDs appear in `created_at DESC, id DESC` order without duplicates for an unchanged collection.
- The final page has `next_cursor: null`.
- Malformed cursor, a changed priority/per-page, `cursor` combined with `page`, or incompatible sort yields an MCP tool error.
- Existing offset-mode calls continue to return `page`, `per_page`, and `has_next_page`.

## Progress demonstration

Set `MCP_TODOS_PROGRESS_DELAY_SECONDS=30`, restart the server, and use an SDK client that passes a progress callback to `call_tool` for create, update, and delete.

Expected:

- The callback observes monotonically increasing notifications through `1/3`, `2/3`, and `3/3`.
- Other requests remain serviceable while the tool awaits the delay.
- The final tool result arrives only after the database operation succeeds.
- Force a persistence error or use an absent ID to verify no successful `3/3` notification is emitted.

See [contracts/todos-mcp.md](contracts/todos-mcp.md) and [data-model.md](data-model.md) for the detailed contracts.
