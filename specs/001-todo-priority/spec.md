# Feature Specification: Todo Priority Levels

**Feature Branch**: `001-todo-priority`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Add priority to the Todo API. Each Todo should have a priority, and the API must restrict priority values to exactly four predefined options. Let the specification define the names and semantics of those four priority levels."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assign Priority When Creating a Todo (Priority: P1)

As an API consumer, I want to set a priority level when I create a new Todo, so that the importance of each item is captured from the start.

**Why this priority**: Creating a Todo is the most fundamental operation. Capturing priority at creation time is the primary entry point for the feature and delivers the core value immediately.

**Independent Test**: Can be fully tested by sending a create-Todo request with each of the four valid priority values and verifying the returned Todo contains the correct priority. Delivering this story alone lets clients categorise every new item they create.

**Acceptance Scenarios**:

1. **Given** a request to create a Todo with priority `urgent`, **When** the request is submitted, **Then** the created Todo is returned with priority set to `urgent`.
2. **Given** a request to create a Todo with priority `high`, **When** the request is submitted, **Then** the created Todo is returned with priority set to `high`.
3. **Given** a request to create a Todo with priority `medium`, **When** the request is submitted, **Then** the created Todo is returned with priority set to `medium`.
4. **Given** a request to create a Todo with priority `low`, **When** the request is submitted, **Then** the created Todo is returned with priority set to `low`.
5. **Given** a request to create a Todo with an unrecognised priority value (e.g. `"critical"` or `"5"`), **When** the request is submitted, **Then** the service rejects the request with a descriptive validation error and no Todo is created.
6. **Given** a request to create a Todo with no priority field supplied, **When** the request is submitted, **Then** the Todo is created with a default priority of `medium`.

---

### User Story 2 - Update the Priority of an Existing Todo (Priority: P2)

As an API consumer, I want to change the priority of an existing Todo, so that I can reflect shifting importance without recreating the item.

**Why this priority**: Priorities change over time. Without update support the feature is partially useful; updating is the second most-valuable interaction but depends on creation being present first.

**Independent Test**: Can be fully tested by creating a Todo with one priority, updating it to each other valid priority in turn, and confirming the persisted value matches the requested value.

**Acceptance Scenarios**:

1. **Given** an existing Todo with priority `low`, **When** a request updates it to `urgent`, **Then** the Todo is returned with priority `urgent` and all other fields unchanged.
2. **Given** an existing Todo, **When** a request attempts to update priority to an invalid value, **Then** the service returns a descriptive validation error and the Todo's priority is not changed.
3. **Given** an existing Todo, **When** a partial update request omits the priority field entirely, **Then** the Todo's existing priority is preserved unchanged.

---

### User Story 3 - Retrieve Todos Filtered by Priority (Priority: P3)

As an API consumer, I want to list Todos filtered by one or more priority levels, so that I can focus on items of a specific importance at any given time.

**Why this priority**: Filtering by priority unlocks the primary productivity benefit of the feature. It builds on the ability to create and update priorities (P1, P2) and adds the consumer-facing query capability.

**Independent Test**: Can be fully tested by seeding Todos with different priorities and verifying that filtering by a given priority returns only matching items, with no cross-contamination from other priority levels.

**Acceptance Scenarios**:

1. **Given** Todos with priorities `urgent`, `high`, `medium`, and `low` exist, **When** a list request filters by `urgent`, **Then** only Todos with priority `urgent` are returned.
2. **Given** Todos with mixed priorities exist, **When** a list request supplies no priority filter, **Then** all Todos are returned (existing behaviour is preserved).
3. **Given** no Todos match the requested priority filter, **When** the list request is submitted, **Then** an empty list is returned (no error).

---

### User Story 4 - View Priority in Todo Responses (Priority: P1)

As an API consumer, I want every Todo response to include the priority field, so that I do not need a separate call to discover an item's importance.

**Why this priority**: Priority is a core attribute of every Todo. Exposing it in all responses (single-item and list) is a prerequisite for all other stories to deliver visible value.

**Independent Test**: Can be tested independently by retrieving a single Todo and a list of Todos and asserting the priority field is present and contains a valid priority level in every object.

**Acceptance Scenarios**:

1. **Given** a Todo with priority `high`, **When** a single-item retrieval request is made, **Then** the response includes `"priority": "high"`.
2. **Given** a list of Todos with various priorities, **When** a list request is made, **Then** every Todo object in the response includes the `priority` field with its correct value.

---

### Edge Cases

- What happens when a client sends an integer or numeric string (e.g. `1`, `"3"`) as a priority value? → The service MUST reject the request with a validation error listing the four accepted string values.
- What happens when a client sends the priority value in a different letter-case (e.g. `"URGENT"`, `"High"`)? → The service MUST reject the request; priority values are case-sensitive lowercase strings.
- What happens when a Todo was created before this feature was introduced (i.e. has no stored priority)? → Legacy Todos are treated as having priority `medium` and are returned with that value.
- What happens when a bulk-import request includes a mix of valid and invalid priorities? → Each invalid Todo entry is rejected individually with a descriptive error; valid entries are unaffected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each Todo MUST have exactly one priority value drawn from a fixed set of four levels: `urgent`, `high`, `medium`, and `low`.
- **FR-002**: The four priority levels carry the following semantics:
  - **`urgent`**: Requires immediate attention; blockers or time-critical tasks.
  - **`high`**: Important work that should be addressed in the current work period.
  - **`medium`**: Standard work with no exceptional urgency (default level).
  - **`low`**: Nice-to-have or background work that can be deferred.
- **FR-003**: The service MUST reject any create or update request that supplies a priority value outside the four defined levels, returning a descriptive error that names all valid options.
- **FR-004**: The `priority` field MUST be optional on create requests; when omitted, the service MUST assign `medium` as the default.
- **FR-005**: The `priority` field MUST be returned in every Todo response object, including single-item retrieval and list responses.
- **FR-006**: The service MUST allow consumers to filter the Todo list by priority level; the filter MUST accept one valid priority value per request.
- **FR-007**: Updating a Todo's priority MUST leave all other fields (title, description, completion status, timestamps) unchanged.
- **FR-008**: Priority values MUST be treated as case-sensitive; values not matching exact lowercase forms MUST be rejected.
- **FR-009**: Todos that pre-date this feature (stored without a priority) MUST be surfaced with priority `medium` in all responses.
- **FR-010**: The set of valid priority values MUST be enforced at the service boundary so that no invalid value can ever be persisted.

### Key Entities *(include if feature involves data)*

- **Todo**: An existing entity representing a task. Gains a `priority` attribute that holds exactly one of the four defined priority levels. The default priority is `medium`. Priority is immutable by the system (only changed explicitly by the consumer).
- **Priority Level**: A constrained value type with four members — `urgent`, `high`, `medium`, `low` — ordered from highest to lowest importance. Not a standalone stored entity; an attribute of Todo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of create and update requests supplying an invalid priority value receive a rejection response that explicitly names all four valid options, with no invalid value persisted.
- **SC-002**: All existing Todo retrieval operations continue to return correct results after the feature is introduced, with zero regressions to pre-existing fields or behaviours.
- **SC-003**: Priority-filtered list requests return only Todos matching the requested level, with a false-positive rate of 0%.
- **SC-004**: Consumers can assign, change, and query Todo priorities without any additional round-trips beyond the single create, update, or list request.
- **SC-005**: Legacy Todos (created before this feature) appear with priority `medium` in all responses — 100% of pre-existing records are surfaced without error.
- **SC-006**: The end-to-end flow of creating a Todo with a priority, updating that priority, and retrieving it by priority filter completes within the same response-time envelope as equivalent operations without priority (no measurable latency regression).

## Assumptions

- The Todo API already exists and supports create, read, update, and list operations for Todo items; this feature extends that existing API.
- Backward compatibility is required: existing clients that do not send a priority field will continue to function correctly because priority defaults to `medium`.
- Adding the `priority` field to responses is a non-breaking additive change (per Constitution Principle V); no new API version prefix is introduced.
- Only a single priority value per Todo is required; multi-priority tagging is out of scope.
- Priority filtering supports exactly one priority value per list request; multi-value filtering (e.g. `urgent` OR `high` in a single request) is out of scope for this iteration.
- The ordering of Todos in list responses based on priority rank (i.e. `urgent` first) is out of scope; sorting is a separate concern.
- Authentication and authorisation rules for who may change priority follow whatever rules already govern Todo updates; no new permission model is introduced by this feature.
- All four priority levels are considered permanent; dynamic addition or removal of priority levels at runtime is out of scope.
