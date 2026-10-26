# Todos MCP Server

The MCP server is mounted at `/mcp/todos` and speaks the [MCP SSE transport](https://spec.modelcontextprotocol.io/specification/basic/transports/#http-with-sse).

| Endpoint | Purpose |
|---|---|
| `GET /mcp/todos/sse` | SSE stream — connect here to start a session |
| `POST /mcp/todos/messages/` | JSON-RPC message dispatch |

## Connecting from an AI client

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "project_qwe_todos": {
      "url": "http://localhost:8000/mcp/todos/sse"
    }
  }
}
```

**VS Code (Copilot / Roo Code / Cursor)** — point the MCP server URL to:

```
http://localhost:8000/mcp/todos/sse
```

---

## Tools

Six tools are available for CRUD and search operations.

| Tool | Parameters | Description |
|---|---|---|
| `list_todos` | `page` (1–100, default 1), `per_page` (5–20, default 10), `sort` (default `"due_at:asc,priority:desc"`), `priority` (optional filter) | Paginated todo list, sorted for LLM planning |
| `get_todo_by_id` | `todo_id: int` | Fetch a single todo by ID |
| `search_todos` | `query: str`, `limit: int` (default 5) | Keyword search across todo fields |
| `create_todo` | `title`, `description`, `priority`, `due_at`, `status` | Create a new todo |
| `update_todo` | `todo_id: int`, plus any fields to change | Update one or more fields on an existing todo |
| `delete_todo` | `todo_id: int` | Delete a todo by ID |

All tools return structured JSON. Invalid parameters return an MCP error result (`isError: true`) with a descriptive message rather than an unhandled exception.

**Example — list urgent todos:**
```
list_todos(priority="urgent", per_page=5)
```

**Example — search for a keyword:**
```
search_todos(query="deploy", limit=10)
```

---

## Resources

Four read-only resource URIs provide live todo context.

| URI | MIME type | Description |
|---|---|---|
| `todo://items` | `application/json` | All active todos (`created`, `inprogress`), ordered by due date then priority |
| `todo://items/{id}` | `application/json` | A single todo item by ID |
| `todo://summary` | `text/markdown` | Counts by status and priority, plus a bulleted list of overdue tasks |
| `todo://priorities/{priority}` | `application/json` | Active todos filtered by priority (`urgent`, `high`, `medium`, `low`) |

**Example — read the summary in a prompt:**
```
Read todo://summary and give me my 3 most important tasks for today.
```

---

## Prompts

Three pre-engineered prompt templates guide structured planning sessions.

| Prompt | Arguments | Description |
|---|---|---|
| `daily_planning` | `focus_area` (optional) | Embeds `todo://summary` and guides a 3–5 item daily task agenda |
| `triage_backlog` | `limit` (optional, default 20) | Loads backlog items and instructs the agent to audit clarity and due dates |
| `task_breakdown` | `todo_id: int` (required) | Fetches the parent task and generates sub-tasks as `create_todo` calls |

**Example — run daily planning with a focus:**
```
Use the daily_planning prompt with focus_area="backend stability"
```

**Example — break down a task into sub-tasks:**
```
Use the task_breakdown prompt with todo_id=42
```
