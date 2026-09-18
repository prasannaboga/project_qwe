# Research: Todo Priority Levels

**Feature**: 001-todo-priority | **Date**: 2026-09-18

All technical context was resolved directly from the existing codebase. No external research queries were required. This file documents the findings and decisions taken for each design question raised during the plan phase.

---

## Decision 1: Enum representation for priority values

**Decision**: Define `TodoPriority` as a `str`-subclassing `enum.Enum` in `src/project_qwe/models/todo.py`, stored as a constrained `VARCHAR` column (not a native DB enum type), following the identical pattern used by `TodoStatus`.

**Rationale**: The project already stores `TodoStatus` using `native_enum=False, create_constraint=True` with SQLAlchemy's `Enum` type. Reusing this pattern:
- Keeps the storage layer consistent and reviewable.
- Avoids a native PostgreSQL `ENUM` type, which requires a `DROP TYPE` and `CREATE TYPE` dance on downgrade — problematic under Constitution Principle IV.
- SQLAlchemy `CHECK CONSTRAINT` enforces the allowed values at the database level as a second safety net.

**Alternatives considered**:
- Native PostgreSQL `ENUM`: Rejected — harder to migrate, harder to downgrade.
- Plain `String` column with application-only validation: Rejected — Constitution Principle IV requires DB-level enforcement; `CHECK CONSTRAINT` provides this.

---

## Decision 2: Default priority level

**Decision**: `medium` is the server-side default for the `priority` column in both the ORM model and the Pydantic schema (`TodoBase`).

**Rationale**: Spec FR-004 mandates a default of `medium` when the field is omitted. `medium` is the semantically neutral mid-point, appropriate for work with no exceptional urgency. Both the SQLAlchemy `mapped_column(default=...)` and the Pydantic `Field(default=...)` are set to this value so that the default is enforced at every layer.

**Alternatives considered**:
- `low` as default: Rejected — implies new work is of low importance, which is not universally true.
- `None` / nullable: Rejected — spec FR-010 requires that no invalid or missing value is ever persisted.

---

## Decision 3: Priority filtering in the list endpoint

**Decision**: Add an optional `priority` query parameter to `GET /todos`. The parameter accepts exactly one value from the four valid levels. When omitted the full list is returned (existing behaviour preserved — FR-002 / backward compat).

**Rationale**: Spec FR-006 requires single-value priority filtering. Query parameters are the RESTful convention for list filters in this project (the existing `sort`, `page`, `per_page` params are all query params). Multi-value filtering (e.g. `urgent` OR `high`) is explicitly out of scope (Spec Assumptions).

**Alternatives considered**:
- Filter via request body: Rejected — GET requests with bodies are non-standard and violate REST conventions.
- Filter as path segment (`/todos/priority/urgent`): Rejected — this pattern implies a resource hierarchy that does not exist here; query parameters are idiomatic.

---

## Decision 4: Legacy row handling

**Decision**: The Alembic migration sets `server_default='medium'` on the new column so that all existing rows receive `medium` on migration. The ORM model column is `nullable=False` with `default=TodoPriority.MEDIUM`.

**Rationale**: Spec FR-009 requires legacy Todos to surface with `medium`. Setting the `server_default` in the migration means no UPDATE sweep is required — the database fills in the value for existing rows at migration time. This is the Alembic-idiomatic approach and satisfies the Alembic migration integrity requirement (Constitution Principle IV).

**Alternatives considered**:
- Migration UPDATE sweep: Possible but redundant when `server_default` achieves the same result more reliably.
- Nullable column with application-layer fallback: Rejected — leaks `None` values if any code path skips the fallback, violating FR-010.

---

## Decision 5: Pydantic validation for priority in update requests

**Decision**: `TodoUpdate.priority` is typed as `TodoPriority | None` with `default=None`. When `None`, the existing priority is preserved (patch semantics consistent with other optional update fields). When a value is supplied, it must be one of the four valid enum members — Pydantic enforces this automatically.

**Rationale**: Existing `TodoUpdate` uses the same `Optional[field]` pattern for `title`, `description`, `status`, and `due_at`. Consistency with established conventions (Constitution Principle VI). Pydantic's enum validation produces a clear 422 error with the list of valid values when an invalid string is supplied.

**Alternatives considered**:
- Separate PATCH endpoint for priority only: Rejected — over-engineering; the existing PUT semantics are sufficient.
- `str` with manual validation in the service: Rejected — Pydantic enum validation is more declarative, DRY, and consistent with how `TodoStatus` is validated.

---

## Summary Table

| Question | Decision | Principle Alignment |
|---|---|---|
| Enum storage | `str`-enum + `CHECK CONSTRAINT`, `native_enum=False` | IV (migration safety), II (consistency) |
| Default priority | `medium` at both ORM and schema layers | V (backward compat), FR-004 |
| Filtering mechanism | Optional query param on `GET /todos` | V (backward compat), FR-006 |
| Legacy rows | `server_default='medium'` in migration | IV (Alembic integrity), FR-009 |
| Update semantics | `TodoPriority \| None`, patch-style | VI (readability), FR-007 |
