# Intent: Todos API Performance & Pagination

## 1. Executive Intent & Problem Statement
The Todos list endpoint requires high-performance, predictable querying and pagination. Unconstrained offset pagination, unindexed sorts, and mandatory `COUNT(*)` queries cause severe CPU/IO table scanning, memory exhaustion, and record drift (phantom duplicates or skipped rows across pages during concurrent mutations).

This specification establishes a robust, lightweight pagination baseline: page-based offset pagination secured by hard depth caps, deterministic tie-breaker ordering, zero-cost next-page detection via `limit + 1` fetching without `COUNT(*)`, and strict sort allowlisting backed by dedicated database indexes.

---

## 2. Scope Boundaries

### In-Scope
- Page-based offset pagination with enforced `page` and `per_page` limits and a maximum page depth ceiling.
- Strict sort parameter parsing (`sort=field:direction`) against an explicit allowlist of indexed columns.
- Deterministic secondary tie-breaker ordering on `id` (ascending or descending matching primary direction).
- Lightweight response envelope containing `items` and `has_next_page` evaluated via `limit + 1` query fetch strategy.
- SQLAlchemy query builder updates in domain service layer (`src/project_qwe/services/`).
- Database indexes for sort/filter columns managed via an Alembic migration (`migrations/versions/`).
- Pydantic request validation and standard 422 error handling for invalid sort fields, directions, and pagination parameters.

### Out-of-Scope (Excluded)
- Mandatory or optional `COUNT(*)` / total record count calculations.
- Full cursor-based / keyset pagination (deferred; tie-breaker offset + depth cap fulfills stability requirements without added client complexity).
- Arbitrary SQL sorting expressions or user-defined dynamic column ordering.
- Full-text search integrations.

---

## 3. Core Technical Requirements & Contract

### 3.1 Query Parameters
| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `page` | integer | `1` | `ge=1`, `le=100` (Max depth cap) | Current page number. |
| `per_page` | integer | `20` | `ge=1`, `le=100` (Max limit cap) | Number of items per page. |
| `sort` | string | `created_at:desc` | Format `field:direction` | Sort field and order. |

### 3.2 Sort Syntax & Allowlist
- **Format**: `<field>:<direction>` (e.g., `due_at:asc`, `created_at:desc`, `title:asc`).
- **Allowed Fields**: `id`, `title`, `due_at`, `created_at`, `updated_at`.
- **Allowed Directions**: `asc`, `desc` (case-insensitive in validation, normalized to lowercase).
- **Default Sort**: `created_at:desc`.

### 3.3 Deterministic Tie-Breaking
To prevent record drift across page boundaries during concurrent insertions or updates:
- Every query must apply a primary sort on the requested field followed by a secondary tie-breaker sort on `id`.
- Tie-breaker direction matches the primary sort direction:
  - `ORDER BY {field} ASC, id ASC`
  - `ORDER BY {field} DESC, id DESC`
- When the primary sort field is `id`, no secondary sort is appended.

### 3.4 Limit + 1 Pagination Logic
- The service fetches `per_page + 1` records from the database using `.offset((page - 1) * per_page).limit(per_page + 1)`.
- If `len(results) > per_page`:
  - `has_next_page = True`
  - Slice items to `results[:per_page]`.
- Else:
  - `has_next_page = False`
  - Return all `results`.
- Total count is never queried.

### 3.5 Response Envelope Schema
```json
{
  "items": [
    {
      "id": "integer",
      "title": "string",
      "description": "string | null",
      "completed": "boolean",
      "due_at": "string | null (ISO 8601)",
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)"
    }
  ],
  "page": 1,
  "per_page": 20,
  "has_next_page": false
}
```

---

## 4. Database & Indexing Requirements

### 4.1 Required Indexes
Ensure single-column B-tree indexes exist on the `todos` table to support efficient ordering and indexed lookups:
- `ix_todos_created_at` on `todos(created_at)`
- `ix_todos_updated_at` on `todos(updated_at)`
- `ix_todos_due_at` on `todos(due_at)`
- `ix_todos_title` on `todos(title)`
- Primary key index on `todos(id)` (default)

### 4.2 Alembic Migration
- Generate a new migration revision via `uv run alembic revision --autogenerate -m "add_indexes_for_todos_pagination_and_sorting"`.
- Never modify previous applied migrations.

---

## 5. Error Handling & Validation Rules

- **Invalid Sort Field**: If `field` is not in `['id', 'title', 'due_at', 'created_at', 'updated_at']`, return `422 Unprocessable Entity` with a clear validation error message.
- **Invalid Sort Direction**: If `direction` is not in `['asc', 'desc']`, return `422 Unprocessable Entity`.
- **Malformed Sort Format**: If `sort` does not match `^[a-zA-Z0-9_]+:(asc|desc)$` (case-insensitive), return `422 Unprocessable Entity`.
- **Pagination Boundary Violations**:
  - `page < 1` or `page > 100` -> `422 Unprocessable Entity`.
  - `per_page < 1` or `per_page > 100` -> `422 Unprocessable Entity`.

---

## 6. Acceptance Criteria

- [ ] **AC-1: Valid Pagination & Default Ordering**: `GET /api/v1/todos` returns 200 with default `page=1`, `per_page=20`, sorted by `created_at DESC, id DESC`, with `has_next_page` correctly computed.
- [ ] **AC-2: Limit+1 Execution**: Database queries fetch at most `per_page + 1` rows with no `COUNT(*)` query executed.
- [ ] **AC-3: Allowlist Enforcement**: Requests with `sort=invalid_column:asc` or `sort=created_at:invalid` fail with 422.
- [ ] **AC-4: Max Depth & Limit Guardrails**: Requests with `page=101` or `per_page=101` fail with 422.
- [ ] **AC-5: Deterministic Pagination**: Paginating through records with duplicate sort values (e.g., matching timestamps) produces no duplicate or missing rows across page boundaries due to the secondary `id` tie-breaker.
- [ ] **AC-6: Index Migration**: A new Alembic migration adds required B-tree indexes for all sortable columns and applies cleanly via `uv run alembic upgrade head`.
- [ ] **AC-7: Architectural Compliance**: Endpoint handles request/response mapping only; all pagination logic, sort parsing, and query construction reside in `src/project_qwe/services/`.
