# MCP Contract: Todos Enhancements

**Feature**: `002-todos-mcp-enhancements` | **Transport**: existing SSE server mounted at `/mcp/todos`

## Tool metadata

All affected tools expose a title, a descriptive operation summary, field-level title/description/default/constraints, and annotations. Required parameters remain required; optional values are explicitly represented with defaults or nullable types.

| Tool | Required fields | Additive metadata/behavior |
|---|---|---|
| `create_todo` | `title` (nonblank) | Field constraints for title, description ≤1000, enum values, and ISO-8601 due date; progress notifications; structured JSON response unchanged. |
| `update_todo` | `todo_id` (positive) | Optional change fields documented; progress notifications; missing Todo remains an MCP tool error. |
| `delete_todo` | `todo_id` (positive) | Destructive annotation; progress notifications; success JSON unchanged. |
| `list_todos` | none | Read-only/idempotent annotation, documented offset mode and additive cursor mode. |

## `list_todos` pagination modes

### Existing offset mode (preserved)

Inputs remain `page` (1–100), `per_page` (5–20), `sort`, and optional `priority`. The response continues to include `items`, `page`, `per_page`, and `has_next_page`.

### Additive cursor mode

| Input/output | Contract |
|---|---|
| `cursor` | Optional opaque continuation returned by a prior cursor-mode response. Never synthesize or edit it. |
| `per_page` | 5–20. Must equal the value encoded by `cursor` after page one. |
| `priority` | Optional valid priority. Must equal the value encoded by `cursor` after page one. |
| `sort` | Cursor mode uses only `created_at:desc,id:desc`; incompatible explicit sort is an MCP tool error. |
| `page` | Not accepted together with `cursor`. |
| `next_cursor` | `null` on final page; otherwise pass verbatim as `cursor` in the next call. |

`next_cursor` is an application result field, not MCP protocol `nextCursor`. This distinction is deliberate: MCP protocol pagination does not page `tools/call` results.

Example first page:

```json
{"per_page": 10, "priority": "high"}
```

Example continuation:

```json
{"cursor": "<previous next_cursor>", "per_page": 10, "priority": "high"}
```

## Individual Todo resource template

| Property | Contract |
|---|---|
| Template | `todo://items/{id}` (existing, preserved) |
| Discovery | Returned by `resources/templates/list` |
| Parameter | `id`: positive integer Todo identifier |
| Result | Exactly one `application/json` content item representing `TodoResponse` |
| Not found | Existing `ResourceNotFoundError` convention |
| Data access | `todo_service.get_todo_by_id` through operation-scoped `SessionLocal()` |

## Progress notifications

`create_todo`, `update_todo`, and `delete_todo` may emit progress only when the client provides a progress callback/token and the server reports progress. Notification values are monotonic, with total `3`:

1. `1/3`: validation complete.
2. `2/3`: optional demo delay complete; persistence begins.
3. `3/3`: committed/deleted successfully.

No terminal success notification is emitted if persistence fails. The configured demo delay is off by default and, if enabled, must be 30–45 seconds.
