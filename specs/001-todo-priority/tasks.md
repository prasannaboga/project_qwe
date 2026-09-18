# Tasks: Todo Priority Levels

**Feature**: 001-todo-priority | **Branch**: `001-todo-priority` | **Date**: 2026-09-18
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing project is in a runnable state and establish the development baseline for this feature.

- [X] T001 Verify existing test suite passes with `uv run pytest` before any changes are made
- [X] T002 Verify development server starts with `uv run uvicorn project_qwe.main:app --reload` before any changes are made

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Introduce the `TodoPriority` enum and the database migration — the two artefacts that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `TodoPriority` str-enum (`urgent`, `high`, `medium`, `low`) to `src/project_qwe/models/todo.py` using `native_enum=False, create_constraint=True` — identical pattern to existing `TodoStatus`; include module-level docstring on the enum
- [X] T004 Add `priority` mapped column to the `Todo` ORM class in `src/project_qwe/models/todo.py` — `NOT NULL`, `default=TodoPriority.MEDIUM`, same `Enum(...)` kwargs as `TodoStatus`, with a database-level `CHECK CONSTRAINT` restricting values to `('urgent', 'high', 'medium', 'low')`
- [X] T005 Generate Alembic migration with `uv run alembic revision --autogenerate -m "add priority to todos"` and review the generated file in `migrations/versions/`; verify: column is `VARCHAR NOT NULL`, `server_default='medium'`, `CHECK CONSTRAINT` present, and a downgrade path that drops the column is included
- [X] T006 Apply migration with `uv run alembic upgrade head` and confirm it runs without errors

**Checkpoint**: `TodoPriority` enum exists in the model, migration is applied, and `uv run pytest` still passes (existing tests should be unaffected).

---

## Phase 3: User Story 4 — Priority in Every Response (Priority: P1) 🎯 MVP

**Goal**: Every Todo response — single-item and list — includes the `priority` field so consumers can see priority without extra calls.

> US4 is listed P1 in the spec and is a prerequisite for all other stories that return Todo objects, so it is implemented first.

**Independent Test**: Retrieve any existing Todo via `GET /todos/{id}` and assert the response JSON contains `"priority": "medium"` (the default applied to legacy rows).

### Implementation for User Story 4

- [X] T007 [US4] Add `priority: TodoPriority` field with `default=TodoPriority.MEDIUM` to `TodoBase` in `src/project_qwe/schemas/todo.py`; import `TodoPriority` from `project_qwe.models.todo`
- [X] T008 [US4] Add `priority: TodoPriority` field to `TodoResponse` in `src/project_qwe/schemas/todo.py` so it is always serialised in responses; ensure `model_config = ConfigDict(from_attributes=True)` remains intact
- [X] T009 [US4] Add integration test asserting `GET /todos/{id}` response includes `"priority"` with a valid `TodoPriority` value in `tests/api/test_todos.py`
- [X] T010 [US4] Add integration test asserting every item in `GET /todos` list response includes the `"priority"` field in `tests/api/test_todos.py`
- [X] T011 [US4] Run `uv run pytest` — all tests must pass

**Checkpoint**: `priority` is visible in all Todo responses; `GET /todos` and `GET /todos/{id}` both return the field. US4 is independently verifiable.

---

## Phase 4: User Story 1 — Assign Priority on Create (Priority: P1)

**Goal**: Consumers can set any of the four valid priority levels when creating a Todo; omitting the field defaults to `medium`; invalid values are rejected with a descriptive error.

**Independent Test**: Send `POST /todos` with each of the four valid priorities and assert `201 Created` + correct `priority` in response. Send an invalid priority and assert `422` with a message naming all valid options.

### Implementation for User Story 1

- [X] T012 [US1] Confirm `TodoCreate` inherits `priority` from `TodoBase` (added in T007) in `src/project_qwe/schemas/todo.py` — no additional code needed; add a comment to `TodoCreate` confirming the inheritance
- [X] T013 [US1] Update `create_todo()` in `src/project_qwe/services/todo_service.py` to pass `todo_data.priority` (or `TodoPriority.MEDIUM` if falsy) to the `Todo(...)` constructor
- [X] T014 [P] [US1] Add integration test: `POST /todos` with `priority="urgent"` → `201`, response `priority == "urgent"` in `tests/api/test_todos.py`
- [X] T015 [P] [US1] Add integration test: `POST /todos` with `priority="high"` → `201`, response `priority == "high"` in `tests/api/test_todos.py`
- [X] T016 [P] [US1] Add integration test: `POST /todos` with `priority="medium"` → `201`, response `priority == "medium"` in `tests/api/test_todos.py`
- [X] T017 [P] [US1] Add integration test: `POST /todos` with `priority="low"` → `201`, response `priority == "low"` in `tests/api/test_todos.py`
- [X] T018 [US1] Add integration test: `POST /todos` with no `priority` field → `201`, response `priority == "medium"` (default) in `tests/api/test_todos.py`
- [X] T019 [US1] Add integration test: `POST /todos` with `priority="critical"` → `422`, error message contains all four valid values in `tests/api/test_todos.py`
- [X] T020 [US1] Add integration test: `POST /todos` with `priority="URGENT"` (wrong casing) → `422` in `tests/api/test_todos.py`
- [X] T021 [US1] Run `uv run pytest` — all tests must pass

**Checkpoint**: Creating Todos with explicit or omitted priority works correctly; invalid values are rejected. US1 is independently verifiable.

---

## Phase 5: User Story 2 — Update Priority on Existing Todo (Priority: P2)

**Goal**: Consumers can change the priority of an existing Todo; other fields are unaffected; invalid values are rejected; omitting priority in an update preserves the current value.

**Independent Test**: Create a Todo with `priority="low"`, `PUT /todos/{id}` with `{"priority": "urgent"}`, assert `200` and `priority == "urgent"` with all other fields unchanged.

### Implementation for User Story 2

- [X] T022 [US2] Add `priority: TodoPriority | None = Field(default=None, ...)` to `TodoUpdate` in `src/project_qwe/schemas/todo.py`; include a docstring note: "When None, the existing priority is preserved unchanged"
- [X] T023 [US2] Update `update_todo()` in `src/project_qwe/services/todo_service.py`: add a `priority` branch — `if todo_data.priority is not None: todo.priority = todo_data.priority`; must not touch other fields
- [X] T024 [US2] Add integration test: create Todo with `priority="low"`, update to `priority="urgent"` → `200`, `priority == "urgent"`, `title` and `status` unchanged in `tests/api/test_todos.py`
- [X] T025 [US2] Add integration test: update Todo with `priority="important"` → `422`, original priority unchanged in `tests/api/test_todos.py`
- [X] T026 [US2] Add integration test: `PUT /todos/{id}` with only `{"title": "New title"}` (no `priority`) → `200`, `priority` unchanged in `tests/api/test_todos.py`
- [X] T027 [US2] Add unit test for `update_todo()` in `tests/services/test_todo_service.py`: assert that when `TodoUpdate(priority=None)` is passed the existing priority is not mutated
- [X] T028 [US2] Run `uv run pytest` — all tests must pass

**Checkpoint**: Priority updates work correctly; non-priority fields are unaffected; invalid values rejected. US2 is independently verifiable alongside US1.

---

## Phase 6: User Story 3 — Filter List by Priority (Priority: P3)

**Goal**: Consumers can pass a `?priority=<level>` query parameter to `GET /todos` to receive only Todos of that level; omitting the parameter preserves the current full-list behaviour.

**Independent Test**: Seed Todos with all four priorities; `GET /todos?priority=urgent` returns only `urgent` Todos; `GET /todos` returns all.

### Implementation for User Story 3

- [X] T029 [US3] Add optional `priority: TodoPriority | None = Query(default=None, ...)` parameter to `get_todos()` route in `src/project_qwe/api/todos.py`; pass it through to the service
- [X] T030 [US3] Update `get_todos()` in `src/project_qwe/services/todo_service.py`: add an optional `priority: TodoPriority | None = None` parameter; when not `None`, append `.where(Todo.priority == priority)` to the SQLAlchemy `select` statement before applying pagination and sorting
- [X] T031 [US3] Update `ALLOWED_SORT_FIELDS` comment in `src/project_qwe/services/todo_service.py` to note that `priority` is not a sort field (filtering only) to prevent future confusion
- [X] T032 [US3] Add unit test for `get_todos(db, priority=TodoPriority.URGENT)` in `tests/services/test_todo_service.py`: seed 3 Todos (`urgent`, `high`, `low`), assert only `urgent` is returned
- [X] T033 [US3] Add unit test for `get_todos(db, priority=None)` in `tests/services/test_todo_service.py`: assert all Todos are returned unchanged (backward compat)
- [X] T034 [US3] Add integration test: `GET /todos?priority=urgent` returns only `urgent` items; zero-result when none seeded in `tests/api/test_todos.py`
- [X] T035 [US3] Add integration test: `GET /todos?priority=invalid` → `422` in `tests/api/test_todos.py`
- [X] T036 [US3] Add integration test: `GET /todos` (no filter) returns all Todos — existing list behaviour preserved in `tests/api/test_todos.py`
- [X] T037 [US3] Run `uv run pytest` — all tests must pass

**Checkpoint**: Priority-filtered list works; full-list behaviour unchanged. US3 is independently verifiable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete validation, documentation, and housekeeping across all stories.

- [X] T038 [P] Add docstrings to all new and modified public functions in `src/project_qwe/services/todo_service.py` (`create_todo`, `get_todos`, `update_todo`) per Constitution Principle VI
- [X] T039 [P] Add docstrings to all new and modified public classes and fields in `src/project_qwe/schemas/todo.py` (`TodoBase`, `TodoUpdate`, `TodoResponse`) per Constitution Principle VI
- [X] T040 [P] Add a docstring to `TodoPriority` enum in `src/project_qwe/models/todo.py` explaining the four levels and their semantics
- [X] T041 Run the full quickstart validation guide at [`quickstart.md`](quickstart.md) end-to-end against the running development server to confirm all 10 scenarios pass
- [X] T042 Run `uv run alembic downgrade -1` and confirm the migration rolls back cleanly; then re-apply with `uv run alembic upgrade head`
- [X] T043 Run `uv run pytest` one final time across the entire test suite — zero failures, zero errors required

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all user stories**
- **US4 / Phase 3** (P1): Depends on Phase 2 — must complete before US1 and US2 so response schema is consistent
- **US1 / Phase 4** (P1): Depends on Phase 3 (US4 schema changes already in place)
- **US2 / Phase 5** (P2): Depends on Phase 3; can run in parallel with US1 (Phase 4)
- **US3 / Phase 6** (P3): Depends on Phase 2; can run in parallel with US1 + US2 (different files: service filter + route param)
- **Polish (Phase 7)**: Depends on all user story phases complete

### User Story Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational: enum + migration)
            ├── Phase 3 (US4: response schema) ──┐
            │       ├── Phase 4 (US1: create)    │ can run in parallel
            │       └── Phase 5 (US2: update)    │
            └── Phase 6 (US3: filter) ───────────┘
                        └── Phase 7 (Polish)
```

### Within Each Phase

- ORM model changes before schema changes
- Schema changes before service changes
- Service changes before route changes
- Implementation before tests (tests added after, per project convention)

### Parallel Opportunities

- T014–T017 (four create-with-priority tests) are parallel — independent test functions in the same file
- T029 (route param) and T030 (service filter) can be written in parallel — different files
- T038–T040 (docstrings) are parallel — different files/classes
- US2 (Phase 5) and US3 (Phase 6) can be worked on in parallel once Phase 3 is complete

---

## Parallel Example: User Story 1 (Phase 4)

```text
# After T012 and T013 are complete, launch T014–T017 in parallel:
Task T014: POST /todos with priority=urgent → test in tests/api/test_todos.py
Task T015: POST /todos with priority=high   → test in tests/api/test_todos.py
Task T016: POST /todos with priority=medium → test in tests/api/test_todos.py
Task T017: POST /todos with priority=low    → test in tests/api/test_todos.py
```

---

## Implementation Strategy

### MVP First (US4 + US1 Only)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Foundational (enum + migration) — **critical blocker**
3. Complete Phase 3: US4 — priority in all responses
4. Complete Phase 4: US1 — priority on create
5. **STOP and VALIDATE**: Run `uv run pytest` + quickstart Scenarios 1–4
6. Deploy/demo — consumers can now set and see priority on new Todos

### Incremental Delivery

1. Phases 1–4 → MVP: create with priority, see priority in responses
2. Phase 5 (US2) → Update priority on existing Todos
3. Phase 6 (US3) → Filter list by priority
4. Phase 7 → Polish and final sign-off

### Single Developer Strategy

Work sequentially in phase order: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7. Run `uv run pytest` after every phase checkpoint.
