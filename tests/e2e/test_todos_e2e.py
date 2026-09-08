"""End-to-End (E2E) automated tests for the Todos API service."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient


def test_todo_full_lifecycle_e2e(client: TestClient) -> None:
    """E2E workflow: Create -> Read -> Update (multiple steps) -> Verify in List -> Delete -> Verify 404."""
    # 1. Initial State: List should be empty
    initial_res = client.get("/todos")
    assert initial_res.status_code == 200
    assert initial_res.json()["items"] == []

    # 2. Create a new todo
    payload = {
        "title": "Automate QA workflow",
        "description": "Write end-to-end API test suite for Todos",
        "due_at": "2026-09-15T18:00:00Z",
    }
    create_res = client.post("/todos", json=payload)
    assert create_res.status_code == 201
    created_todo = create_res.json()

    todo_id = created_todo["id"]
    assert created_todo["title"] == payload["title"]
    assert created_todo["description"] == payload["description"]
    assert created_todo["status"] == "created"
    assert created_todo["due_at"] is not None
    assert "created_at" in created_todo
    assert "updated_at" in created_todo

    # 3. Read specific todo by ID
    get_res = client.get(f"/todos/{todo_id}")
    assert get_res.status_code == 200
    assert get_res.json() == created_todo

    # 4. Transition to inprogress and update notes
    update_payload_1 = {
        "status": "inprogress",
        "description": "Writing tests now with high coverage",
    }
    update_res_1 = client.put(f"/todos/{todo_id}", json=update_payload_1)
    assert update_res_1.status_code == 200
    updated_1 = update_res_1.json()
    assert updated_1["status"] == "inprogress"
    assert updated_1["description"] == update_payload_1["description"]
    assert updated_1["title"] == payload["title"]

    # 5. Transition to completed
    update_payload_2 = {"status": "completed"}
    update_res_2 = client.put(f"/todos/{todo_id}", json=update_payload_2)
    assert update_res_2.status_code == 200
    updated_2 = update_res_2.json()
    assert updated_2["status"] == "completed"

    # 6. Verify todo is listed in paginated collection
    list_res = client.get("/todos")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["id"] == todo_id
    assert list_data["items"][0]["status"] == "completed"

    # 7. Delete todo
    delete_res = client.delete(f"/todos/{todo_id}")
    assert delete_res.status_code == 200
    assert delete_res.json() == {"message": "Todo deleted successfully"}

    # 8. Verify get by ID returns 404
    get_after_delete = client.get(f"/todos/{todo_id}")
    assert get_after_delete.status_code == 404
    assert get_after_delete.json()["detail"] == f"Todo with id {todo_id} not found"

    # 9. Verify listing is empty again
    list_after_delete = client.get("/todos")
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["items"] == []


def test_todos_pagination_and_sorting_flow_e2e(client: TestClient) -> None:
    """E2E workflow: Batch creation, multi-page pagination navigation, and multi-field sorting."""
    # Seed 5 items with distinct titles and due dates
    items_to_seed = [
        {"title": "Task A", "due_at": "2026-10-01T09:00:00Z"},
        {"title": "Task B", "due_at": "2026-10-02T09:00:00Z"},
        {"title": "Task C", "due_at": "2026-10-03T09:00:00Z"},
        {"title": "Task D", "due_at": "2026-10-04T09:00:00Z"},
        {"title": "Task E", "due_at": "2026-10-05T09:00:00Z"},
    ]

    for item in items_to_seed:
        res = client.post("/todos", json=item)
        assert res.status_code == 201

    # Traverse pages with per_page = 2 sorted by due_at:asc
    # Page 1
    p1 = client.get("/todos?page=1&per_page=2&sort=due_at:asc")
    assert p1.status_code == 200
    p1_data = p1.json()
    assert p1_data["page"] == 1
    assert p1_data["per_page"] == 2
    assert p1_data["has_next_page"] is True
    assert [x["title"] for x in p1_data["items"]] == ["Task A", "Task B"]

    # Page 2
    p2 = client.get("/todos?page=2&per_page=2&sort=due_at:asc")
    assert p2.status_code == 200
    p2_data = p2.json()
    assert p2_data["page"] == 2
    assert p2_data["per_page"] == 2
    assert p2_data["has_next_page"] is True
    assert [x["title"] for x in p2_data["items"]] == ["Task C", "Task D"]

    # Page 3 (final page with remaining 1 item)
    p3 = client.get("/todos?page=3&per_page=2&sort=due_at:asc")
    assert p3.status_code == 200
    p3_data = p3.json()
    assert p3_data["page"] == 3
    assert p3_data["per_page"] == 2
    assert p3_data["has_next_page"] is False
    assert [x["title"] for x in p3_data["items"]] == ["Task E"]

    # Verify descending sort by due_at
    p_desc = client.get("/todos?page=1&per_page=3&sort=due_at:desc")
    assert p_desc.status_code == 200
    assert [x["title"] for x in p_desc.json()["items"]] == ["Task E", "Task D", "Task C"]


def test_todos_error_resilience_and_validation_e2e(client: TestClient) -> None:
    """E2E workflow: Validate error responses, payload constraints, query bounds, and system resilience."""
    # 1. Reject missing required fields
    res_missing_title = client.post("/todos", json={"description": "Missing title"})
    assert res_missing_title.status_code == 422

    # 2. Reject payload with empty string title (min_length=1 constraint)
    res_empty_title = client.post("/todos", json={"title": ""})
    assert res_empty_title.status_code == 422

    # 3. Reject description exceeding 1000 chars (max_length=1000 constraint)
    res_huge_desc = client.post(
        "/todos", json={"title": "Valid title", "description": "x" * 1001}
    )
    assert res_huge_desc.status_code == 422

    # 5. Reject invalid status enum value
    res_invalid_status = client.post(
        "/todos", json={"title": "Valid title", "status": "done_and_dusted"}
    )
    assert res_invalid_status.status_code == 422

    # 6. Reject pagination out of allowed boundaries [1, 100]
    assert client.get("/todos?page=0").status_code == 422
    assert client.get("/todos?page=101").status_code == 422
    assert client.get("/todos?per_page=0").status_code == 422
    assert client.get("/todos?per_page=101").status_code == 422

    # 7. Reject invalid sort parameters
    assert client.get("/todos?sort=unindexed_column:asc").status_code == 422
    assert client.get("/todos?sort=created_at:random").status_code == 422
    assert client.get("/todos?sort=malformed").status_code == 422

    # 8. Reject operations on non-existent resource IDs
    assert client.get("/todos/88888").status_code == 404
    assert client.put("/todos/88888", json={"title": "Non-existent"}).status_code == 404
    assert client.delete("/todos/88888").status_code == 404

    # 9. Ensure database remains completely uncorrupted / clean after failures
    clean_check = client.get("/todos")
    assert clean_check.status_code == 200
    assert clean_check.json()["items"] == []


def test_todos_slash_routing_compatibility_e2e(client: TestClient) -> None:
    """E2E workflow: Verify both trailing slash and non-trailing slash routes respond identically."""
    # POST with trailing slash
    res_slash = client.post("/todos/", json={"title": "Trailing slash test"})
    assert res_slash.status_code == 201
    item_id = res_slash.json()["id"]

    # GET with trailing slash
    res_list_slash = client.get("/todos/")
    assert res_list_slash.status_code == 200
    assert len(res_list_slash.json()["items"]) == 1

    # GET without trailing slash
    res_list_no_slash = client.get("/todos")
    assert res_list_no_slash.status_code == 200
    assert len(res_list_no_slash.json()["items"]) == 1

    # Cleanup
    assert client.delete(f"/todos/{item_id}").status_code == 200
