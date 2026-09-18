# API Contract: Todos — Priority Extension

**Feature**: 001-todo-priority | **Date**: 2026-09-18
**Base URL**: `/todos`

This document describes the changes to the Todo REST API introduced by the priority feature. All other endpoints and fields are unchanged.

---

## Shared Types

### TodoPriority (string enum)

Accepted string values (case-sensitive, lowercase):

| Value | Meaning |
|-------|---------|
| `urgent` | Requires immediate attention; blockers or time-critical tasks |
| `high` | Important; should be addressed in the current work period |
| `medium` | Standard work; no exceptional urgency *(default)* |
| `low` | Deferrable; nice-to-have or background work |

Any value outside this set causes a **422 Unprocessable Entity** response with a message naming the four valid options.

---

## Modified Endpoints

### POST /todos — Create a Todo

**Change**: `priority` is now an accepted optional field in the request body. When omitted, defaults to `medium`.

#### Request Body (additions highlighted)

```json
{
  "title": "string (required, min 1 char)",
  "description": "string | null (optional, max 1000 chars)",
  "status": "created | inprogress | completed (optional, default: created)",
  "due_at": "ISO 8601 datetime | null (optional)",
  "priority": "urgent | high | medium | low (optional, default: medium)"
}
```

#### Response — 201 Created (additions highlighted)

```json
{
  "id": 1,
  "title": "Buy milk",
  "description": null,
  "status": "created",
  "priority": "medium",
  "due_at": null,
  "created_at": "2026-09-18T15:20:00Z",
  "updated_at": "2026-09-18T15:20:00Z"
}
```

#### Error — 422 Unprocessable Entity (invalid priority)

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "priority"],
      "msg": "Input should be 'urgent', 'high', 'medium' or 'low'",
      "input": "critical"
    }
  ]
}
```

---

### PUT /todos/{todo_id} — Update a Todo

**Change**: `priority` is now an accepted optional field in the request body. When omitted, the existing priority is preserved unchanged.

#### Request Body (additions highlighted)

```json
{
  "title": "string | null (optional)",
  "description": "string | null (optional)",
  "status": "created | inprogress | completed | null (optional)",
  "due_at": "ISO 8601 datetime | null (optional)",
  "priority": "urgent | high | medium | low | null (optional)"
}
```

#### Response — 200 OK

Same shape as the `POST /todos` response. All fields returned; only the explicitly provided fields are changed.

#### Error — 422 Unprocessable Entity (invalid priority)

Same format as the create endpoint error.

---

### GET /todos — List Todos (with priority filter)

**Change**: A new optional `priority` query parameter filters results to only Todos with the specified priority level.

#### Query Parameters (additions highlighted)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | `1` | Page number (1–100) |
| `per_page` | integer | No | `20` | Items per page (1–100) |
| `sort` | string | No | `created_at:desc` | Sort format `<field>:<direction>` |
| `priority` | string | No | *(none — all returned)* | Filter by priority level: `urgent`, `high`, `medium`, or `low` |

#### Example Request

```
GET /todos?priority=urgent&page=1&per_page=20
```

#### Response — 200 OK

```json
{
  "items": [
    {
      "id": 5,
      "title": "Fix production outage",
      "description": null,
      "status": "inprogress",
      "priority": "urgent",
      "due_at": null,
      "created_at": "2026-09-18T10:00:00Z",
      "updated_at": "2026-09-18T12:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "has_next_page": false
}
```

#### Error — 422 Unprocessable Entity (invalid priority filter value)

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["query", "priority"],
      "msg": "Input should be 'urgent', 'high', 'medium' or 'low'",
      "input": "important"
    }
  ]
}
```

---

### GET /todos/{todo_id} — Get a Single Todo

**Change**: Response now includes the `priority` field. No request changes.

#### Response — 200 OK

Same shape as the POST response shown above. `priority` is always present.

---

## Unchanged Endpoints

- `DELETE /todos/{todo_id}` — No changes; response shape unchanged.

---

## Backward Compatibility Notes

- Adding `priority` to responses is a non-breaking additive change (Constitution Principle V).
- Existing clients that do not send `priority` on create continue to work — the field defaults to `medium`.
- Existing clients that do not use the `priority` filter parameter receive unchanged full-list behaviour.
- No endpoint paths, HTTP methods, or existing field semantics have changed.
