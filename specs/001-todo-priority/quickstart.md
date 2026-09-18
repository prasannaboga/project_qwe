# Quickstart Validation Guide: Todo Priority Levels

**Feature**: 001-todo-priority | **Date**: 2026-09-18

Use this guide to validate that the priority feature works end-to-end after implementation. All commands are run from the repository root.

---

## Prerequisites

- Python 3.14 and `uv` installed.
- `.env` file present with a valid `DATABASE_URL` (see `.env.example`).
- Dependencies installed: `uv sync`

---

## Setup

### 1. Apply the database migration

```bash
uv run alembic upgrade head
```

**Expected**: Migration output shows the `add_priority_to_todos` revision applied with no errors. Existing rows in the `todos` table are visible with `priority = medium`.

### 2. Start the development server

```bash
uv run uvicorn project_qwe.main:app --reload
```

**Expected**: Server starts on `http://127.0.0.1:8000` with no import or startup errors.

---

## Validation Scenarios

> For each scenario, the API contract is at [`contracts/todos-api.md`](contracts/todos-api.md).
> For field shapes, see [`data-model.md`](data-model.md).

---

### Scenario 1 — Create a Todo with an explicit priority

```bash
curl -s -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix outage", "priority": "urgent"}' | python3 -m json.tool
```

**Expected response** (HTTP 201):
- `priority` field is `"urgent"`
- All other fields present with correct defaults

---

### Scenario 2 — Create a Todo without a priority (default behaviour)

```bash
curl -s -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Write docs"}' | python3 -m json.tool
```

**Expected response** (HTTP 201):
- `priority` field is `"medium"` (default applied)

---

### Scenario 3 — Create a Todo with an invalid priority

```bash
curl -s -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Bad priority", "priority": "critical"}' | python3 -m json.tool
```

**Expected response** (HTTP 422):
- Error message names all four valid options (`urgent`, `high`, `medium`, `low`)
- No Todo is created

---

### Scenario 4 — Create a Todo with wrong casing

```bash
curl -s -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Bad casing", "priority": "URGENT"}' | python3 -m json.tool
```

**Expected response** (HTTP 422):
- Rejected; `"URGENT"` is not accepted

---

### Scenario 5 — Update a Todo's priority

First, note the `id` of the Todo created in Scenario 1 (e.g. `1`), then:

```bash
curl -s -X PUT http://127.0.0.1:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"priority": "low"}' | python3 -m json.tool
```

**Expected response** (HTTP 200):
- `priority` is now `"low"`
- All other fields (`title`, `status`, `description`, `due_at`) are unchanged from the original

---

### Scenario 6 — Update a Todo with an invalid priority

```bash
curl -s -X PUT http://127.0.0.1:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"priority": "important"}' | python3 -m json.tool
```

**Expected response** (HTTP 422):
- Rejected; original priority is preserved

---

### Scenario 7 — Filter the list by priority

Seed a few Todos with different priorities, then:

```bash
curl -s "http://127.0.0.1:8000/todos?priority=urgent" | python3 -m json.tool
```

**Expected response** (HTTP 200):
- Only Todos with `priority = "urgent"` appear in `items`
- `page`, `per_page`, `has_next_page` are present

---

### Scenario 8 — List all Todos (no filter — backward compat)

```bash
curl -s "http://127.0.0.1:8000/todos" | python3 -m json.tool
```

**Expected response** (HTTP 200):
- All Todos returned regardless of priority
- Every Todo object in `items` includes a `priority` field

---

### Scenario 9 — Retrieve a single Todo

```bash
curl -s http://127.0.0.1:8000/todos/1 | python3 -m json.tool
```

**Expected response** (HTTP 200):
- `priority` field is present with a valid value

---

### Scenario 10 — Legacy Todo handling (pre-migration row)

If there are rows that existed before this migration:

```bash
curl -s http://127.0.0.1:8000/todos | python3 -m json.tool
```

**Expected**: All pre-existing Todos are returned with `priority = "medium"`. No 500 errors or missing `priority` fields.

---

## Automated Test Suite

Run the full test suite to validate all scenarios and regressions:

```bash
uv run pytest
```

**Expected**: All tests pass (zero failures, zero errors). Coverage includes:
- Service-layer unit tests for `get_todos()` with and without the priority filter
- API integration tests for create, update, get, list with valid priorities, invalid priorities, and default priority
- At least one test asserting that legacy-style Todos (no priority supplied) default to `medium`

---

## Rollback Validation

To verify the downgrade path:

```bash
uv run alembic downgrade -1
```

**Expected**: The `priority` column is removed from `todos` without errors. The previous migration head is restored.
