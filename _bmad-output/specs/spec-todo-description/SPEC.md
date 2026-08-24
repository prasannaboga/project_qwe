---
id: SPEC-todo-description
companions: []
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Todo API Description Field

## Why

Todo items currently only capture a concise title and due date, leaving users unable to store detailed context, instructions, or multi-line notes for a task. Adding an optional `description` field eliminates this limitation, enabling richer task management while preserving full backward compatibility for existing records and API consumers.

## Capabilities

- **CAP-1**
  - **intent:** A client can supply an optional `description` text (up to 1,000 characters) when creating a new Todo item.
  - **success:** `POST /todos` accepts a payload with `description`, persists it, and returns it in the response (HTTP 201). Omitting `description` defaults to `null`. Payloads with `description` exceeding 1,000 characters receive HTTP 422.

- **CAP-2**
  - **intent:** A client can view the `description` field when reading individual or listed Todo items.
  - **success:** `GET /todos` and `GET /todos/{todo_id}` include `description` in the response payload (returning the stored string or `null`).

- **CAP-3**
  - **intent:** A client can update a Todo's description to a new text value, or explicitly clear an existing description to `null`.
  - **success:** Updating a Todo with a new description updates the value; passing `null` clears the stored description. Omitting the field during partial updates preserves the existing description.

## Constraints

- Database schema modification must be executed via a new forward-only Alembic migration revision without modifying prior migration files.
- All database operations and domain logic must be implemented in `src/project_qwe/services/todo_service.py`; route handlers in `src/project_qwe/api/todos.py` remain thin controllers.
- The `description` field is an optional, nullable string capped at 1,000 characters (`max_length=1000`), returning HTTP 422 when exceeded.
- Full backward compatibility: all existing database rows default to `NULL` for `description`, and existing API requests omitting `description` continue without error.

## Non-goals

- No full-text search index, fuzzy search, or indexing on `description`.
- No server-side markdown parsing, HTML rendering, or sanitization; stored and returned as raw plain text.
- No pagination or query parameter filtering on `description`.
- No file attachments or binary media association.

## Success signal

- A client can create, retrieve, update, and clear a description up to 1,000 characters across all CRUD endpoints, backed by an applied Alembic migration and a passing automated test suite (`pytest`) verifying valid text, null/omitted fields, and validation boundaries.
