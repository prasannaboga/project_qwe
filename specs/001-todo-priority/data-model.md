# Data Model: Todo Priority Levels

**Feature**: 001-todo-priority | **Date**: 2026-09-18

---

## Entity: Todo (modified)

The existing `Todo` entity gains one new attribute: `priority`.

### Attributes

| Attribute | Type | Nullable | Default | Constraints | Notes |
|-----------|------|----------|---------|-------------|-------|
| `id` | integer | No | auto | PRIMARY KEY | Existing — unchanged |
| `title` | string | No | — | min length 1 | Existing — unchanged |
| `description` | string (≤1000) | Yes | `null` | — | Existing — unchanged |
| `status` | TodoStatus enum | No | `created` | One of: created, inprogress, completed | Existing — unchanged |
| `priority` | **TodoPriority enum** | **No** | **`medium`** | **One of: urgent, high, medium, low** | **NEW** |
| `due_at` | datetime (tz-aware) | Yes | `null` | — | Existing — unchanged |
| `created_at` | datetime (tz-aware) | No | now() | server_default | Existing — unchanged |
| `updated_at` | datetime (tz-aware) | No | now() | onupdate | Existing — unchanged |

### New Value Type: TodoPriority

A constrained enumeration of exactly four lowercase string members, ordered from highest to lowest urgency:

| Value | Ordinal | Semantics |
|-------|---------|-----------|
| `urgent` | 1 (highest) | Requires immediate attention; blockers or time-critical tasks |
| `high` | 2 | Important work to be addressed in the current work period |
| `medium` | 3 (default) | Standard work with no exceptional urgency |
| `low` | 4 (lowest) | Nice-to-have or background work that can be deferred |

**Validation rules**:
- Values are case-sensitive; `"Urgent"`, `"URGENT"`, `"1"` are all invalid.
- The set is closed — no runtime additions or removals.
- Default value when omitted by consumer: `medium`.
- Invalid values produce a descriptive validation error naming all four valid options.

---

## Database Schema Change

### New column on `todos` table

```
todos
└── priority  VARCHAR  NOT NULL  DEFAULT 'medium'
              CHECK priority IN ('urgent', 'high', 'medium', 'low')
```

- Column type: `VARCHAR` (not a native DB enum) — consistent with `status` column pattern.
- `CHECK CONSTRAINT` enforces the four valid values at the database level.
- `DEFAULT 'medium'` at the database level ensures all pre-existing rows receive `medium` on migration without a separate UPDATE sweep.
- `NOT NULL` — the priority field is always present in every persisted row.

### Alembic migration (new revision)

- Adds the `priority` column with `server_default='medium'` and `nullable=False`.
- Includes a downgrade path that drops the column.
- Must be generated with: `uv run alembic revision --autogenerate -m "add priority to todos"`

---

## Validation Rules

| Rule | Source |
|------|--------|
| Priority value must be one of `urgent`, `high`, `medium`, `low` | FR-001, FR-003 |
| Priority comparison is case-sensitive (lowercase only) | FR-008 |
| Omitting priority on create defaults to `medium` | FR-004 |
| Omitting priority on update preserves existing value | FR-007 |
| Legacy rows (pre-feature) treated as `medium` | FR-009 |

---

## State Transitions

Priority is not a stateful field with transitions; it is a freely settable attribute. Any of the four values may be set to any other value via an update request. No ordering or lifecycle rules constrain which value may follow another.

---

## Relationships

Priority is a scalar attribute of Todo only. It is not a standalone entity and has no relationships to other entities. The `TodoPriority` type is reused across the ORM model, Pydantic schemas, and service filter logic.
