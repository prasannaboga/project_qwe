# Data Model: Todos MCP API Enhancements

No database tables, columns, migrations, or ORM entities change. The design adds transport/configuration value objects only.

## Existing Todo (read and written through services)

| Field relevant to this plan | Use |
|---|---|
| `id` | Existing unique ID for tools and `todo://items/{id}` resource template. Positive integer validation remains at the MCP boundary. |
| `created_at` | Primary cursor ordering key in new keyset mode. |
| `priority` | Optional `list_todos` filter; encoded into a cursor to prevent switching result sets mid-traversal. |
| serialized fields | `TodoResponse.model_dump(mode="json")` remains the single MCP JSON representation. |

## Configuration: `MCP_TODOS_PROGRESS_DELAY_SECONDS`

| Property | Value |
|---|---|
| Type | integer setting loaded by `pydantic-settings` |
| Default | `0` (disabled) |
| Valid values | `0` or integer 30 through 45 inclusive |
| Purpose | Demonstration-only wait between validation and persistence for progress-notification clients |
| Test value | `0` |
| Persistence | Environment only; never database-backed |

## Tool cursor payload (not persisted)

The cursor is URL-safe base64 encoded JSON and treated as opaque by clients.

| Field | Meaning | Validation |
|---|---|---|
| `v` | Cursor format version | Must equal supported version `1` |
| `mode` | Cursor contract marker | Must equal `created_at_desc_id_desc` |
| `priority` | Filter used for page one | `null` or valid TodoPriority value; must match request |
| `per_page` | Chosen tool page size | Integer 5–20; must match request |
| `created_at` | Last returned row timestamp | Strict ISO-8601 datetime |
| `id` | Last returned row identifier | Positive integer |

The next page predicate is `(created_at < cursor.created_at) OR (created_at = cursor.created_at AND id < cursor.id)`, with `LIMIT per_page + 1`. Absence of a cursor starts at the first page; absence of a next cursor is the final-page indicator.
