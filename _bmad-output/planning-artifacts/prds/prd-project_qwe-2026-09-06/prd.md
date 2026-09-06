---
title: "Todos API Performance & Pagination PRD"
status: final
created: 2026-09-06
updated: 2026-09-06
version: "1.0.0"
author: "Prasannaboga"
---

# Product Requirements Document (PRD)
## Todos API Performance & Pagination

---

## 1. Executive Summary & Vision

### 1.1 Problem Statement
The current `GET /todos` endpoint in `project_qwe` executes an unbounded query (`select(Todo).order_by(Todo.id)`), loading all table records directly into memory. As the volume of todos grows, this unconstrained approach leads to:
* High memory allocation and CPU spikes during high-concurrency read operations.
* Unindexed full table scans when filtering or sorting on dynamic criteria.
* Page drift (phantom duplicate records or skipped items across page boundaries) when paginating using standard offset queries during concurrent writes.
* Database latency bottlenecks when mandatory `COUNT(*)` queries are executed on every listing request.

### 1.2 Vision & Key Objectives
Establish a high-performance, deterministic, and bounded pagination baseline for the Todos API that:
1. Bounds memory and execution time through enforced limit and page depth caps.
2. Eliminates query drift using deterministic secondary tie-breaker sorting.
3. Completely avoids count-query overhead using a zero-cost `limit + 1` next-page detection algorithm.
4. Guarantees indexed database execution by strictly allowlisting sortable fields.

### 1.3 Success Metrics & Counter-Metrics
* **Success Metric 1:** `GET /todos` p99 latency remains $< 30\text{ms}$ on SQLite under typical workloads.
* **Success Metric 2:** $100\%$ of permitted sort queries utilize dedicated B-Tree database indexes.
* **Success Metric 3:** Zero phantom duplicates or skipped items when traversing consecutive pages during concurrent row additions.
* **Counter-Metric:** Client error rate ($422\text{s}$) should occur only on genuinely malformed requests (e.g. `page > 100` or invalid sort keys), with zero false rejections for compliant clients.

---

## 2. Scope Boundaries

### 2.1 In-Scope
* Page-based offset pagination with enforced `page` and `per_page` limits and a maximum page depth ceiling ($100$).
* Strict sort parameter parsing (`sort=field:direction`) against an explicit allowlist of indexed columns.
* Deterministic secondary tie-breaker ordering on `id` matching the primary direction.
* Lightweight response envelope containing `items`, `page`, `per_page`, and `has_next_page` evaluated via `limit + 1` query fetch strategy.
* SQLAlchemy query builder updates in domain service layer (`src/project_qwe/services/todo_service.py`).
* Database indexes for sort/filter columns managed via an Alembic migration (`migrations/versions/`).
* Pydantic request validation and standard 422 error handling for invalid sort fields, directions, and pagination parameters.

### 2.2 Out-of-Scope (Excluded)
* Mandatory or optional `COUNT(*)` / total record count calculations.
* Full cursor-based / keyset pagination (deferred; tie-breaker offset + depth cap fulfills stability requirements without added client complexity).
* Arbitrary SQL sorting expressions or user-defined dynamic column ordering.
* Full-text search integrations or multi-column composite sorting syntax.

---

## 3. Functional Requirements (FRs)

* **`FR-1: Bounded Offset Pagination Parameters`**
  * The `GET /todos` endpoint MUST accept `page` (default `1`, integer, $1 \le \text{page} \le 100$) and `per_page` (default `20`, integer, $1 \le \text{per_page} \le 100$).
  * The system MUST enforce a server-side maximum depth ceiling ($\text{page} \le 100$) and max page size ($\text{per_page} \le 100$) to prevent deep-offset resource exhaustion.

* **`FR-2: Structured Sorting Syntax`**
  * The endpoint MUST support a single query parameter `sort` with format `<field>:<direction>` (case-insensitive for direction, e.g., `due_at:asc`, `created_at:desc`).
  * If `sort` is omitted, the system MUST apply default sorting `created_at:desc`.

* **`FR-3: Strict Sort Allowlist Enforcement`**
  * Allowed sort fields MUST be strictly restricted to: `['id', 'title', 'due_at', 'created_at', 'updated_at']`.
  * Allowed sort directions MUST be strictly restricted to: `['asc', 'desc']`.
  * Any request requesting sorting on unlisted fields or malformed syntax MUST be rejected with HTTP 422.

* **`FR-4: Deterministic Secondary Tie-Breaker Sorting`**
  * When sorting on any non-primary key column (`title`, `due_at`, `created_at`, `updated_at`), the query MUST append a secondary deterministic sort on `id` matching the primary direction:
    * Ascending: `ORDER BY {field} ASC, id ASC`
    * Descending: `ORDER BY {field} DESC, id DESC`
  * When sorting explicitly on `id`, no secondary sort clause is appended.

* **`FR-5: Limit + 1 Next-Page Detection`**
  * The database query MUST fetch `per_page + 1` rows using offset `(page - 1) * per_page` and limit `per_page + 1`.
  * If the result set count equals `per_page + 1`, the system MUST set `has_next_page = true` and return the first `per_page` items.
  * If the count is $\le \text{per_page}$, `has_next_page = false` and all items are returned.
  * The system MUST NOT execute `COUNT(*)` or total-page queries on standard listing.

* **`FR-6: Pagination Response Envelope`**
  * The endpoint MUST return a top-level JSON response with the schema:
    ```json
    {
      "items": [
        {
          "id": 1,
          "title": "Task title",
          "description": "Optional description",
          "status": "created",
          "due_at": "2026-09-10T12:00:00Z",
          "created_at": "2026-09-06T18:00:00Z",
          "updated_at": "2026-09-06T18:00:00Z"
        }
      ],
      "page": 1,
      "per_page": 20,
      "has_next_page": false
    }
    ```

* **`FR-7: Declarative Error Handling`**
  * Input violations (invalid sort column, unknown direction, `page > 100`, `per_page > 100`, negative values) MUST return HTTP 422 with a structured error payload detailing the invalid field.

---

## 4. Non-Functional Requirements (NFRs)

* **`NFR-1: Memory & Compute Guardrails`**: Memory allocation during `GET /todos` MUST remain bounded to at most 101 records per query. Full-table memory streaming is prohibited.
* **`NFR-2: SQL Injection & Expression Safety`**: Sort expressions MUST never be concatenated into raw SQL strings. All queries MUST be constructed using parameterized SQLAlchemy column attributes.
* **`NFR-3: Zero Lock Contention`**: Read queries MUST use standard non-locking select statements compatible with SQLite WAL mode.
* **`NFR-4: Backward Compatibility`**: Existing endpoints (`GET /todos/{id}`, `POST /todos`, `PUT /todos/{id}`, `DELETE /todos/{id}`) MUST continue operating unchanged.

---

## 5. Database & Migration Specification

### 5.1 Indexes Required on `todos` Table
* `ix_todos_created_at` on column `created_at`
* `ix_todos_updated_at` on column `updated_at`
* `ix_todos_due_at` on column `due_at`
* `ix_todos_title` on column `title`
* `ix_todos_status` on column `status`
* Primary key index on `id` (existing)

### 5.2 Migration Policy
* A new revision MUST be generated via `uv run alembic revision --autogenerate -m "add_indexes_for_todos_pagination_and_sorting"`.
* Existing migration files in `migrations/versions/` MUST NOT be altered.

---

## 6. Architectural Compliance & Layer Boundaries

* **Routing Layer (`src/project_qwe/api/todos.py`)**: Responsible only for dependency injection (`db: Session`), query parameter declarations (`page: int = Query(...)`), invoking the service layer, and returning `TodoPaginationResponse`.
* **Business Logic Layer (`src/project_qwe/services/todo_service.py`)**: Houses all domain operations, sort parsing, allowlist validation, query construction, deterministic tie-breaking, `limit + 1` execution, and `has_next_page` calculation.
* **Schema Layer (`src/project_qwe/schemas/todo.py`)**: Defines `TodoPaginationResponse` and validation models.
* **Model Layer (`src/project_qwe/models/todo.py`)**: Defines ORM columns and index declarations.

---

## 7. Acceptance Criteria (ACs)

* [ ] **AC-1**: `GET /todos` with no parameters returns HTTP 200 with default `page=1`, `per_page=20`, sorted by `created_at DESC, id DESC`, with items wrapped in the envelope.
* [ ] **AC-2**: Querying with `page=2&per_page=10` fetches exact offsets without executing a `COUNT(*)` query.
* [ ] **AC-3**: Requesting unlisted sort fields (`sort=unknown_field:asc`) or invalid directions (`sort=due_at:sideways`) returns HTTP 422 with a validation error description.
* [ ] **AC-4**: Requesting `page=101` or `per_page=101` returns HTTP 422.
* [ ] **AC-5**: Paginating through records sharing identical timestamps produces zero duplicate or missing records across page boundaries due to secondary `id` ordering.
* [ ] **AC-6**: A new Alembic migration adds all specified single-column indexes and applies cleanly via `uv run alembic upgrade head`.
* [ ] **AC-7**: All automated tests pass with `uv run pytest`.
