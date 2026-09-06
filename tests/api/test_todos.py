from datetime import datetime, timezone
from fastapi.testclient import TestClient


def test_create_todo_default_status(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "Buy groceries"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] is None
    assert data["status"] == "created"
    assert data["due_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_todo_with_description(client: TestClient) -> None:
    response = client.post(
        "/todos",
        json={"title": "Buy groceries", "description": "Milk, eggs, and bread"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk, eggs, and bread"


def test_create_todo_with_max_length_description(client: TestClient) -> None:
    desc = "a" * 1000
    response = client.post(
        "/todos",
        json={"title": "Boundary Task", "description": desc},
    )
    assert response.status_code == 201
    assert response.json()["description"] == desc


def test_create_todo_description_exceeds_max_length(client: TestClient) -> None:
    desc = "a" * 1001
    response = client.post(
        "/todos",
        json={"title": "Too Long Task", "description": desc},
    )
    assert response.status_code == 422


def test_create_todo_with_valid_statuses(client: TestClient) -> None:
    for status in ["created", "inprogress", "completed"]:
        response = client.post("/todos", json={"title": f"Task {status}", "status": status})
        assert response.status_code == 201
        assert response.json()["status"] == status


def test_create_todo_invalid_status(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "Invalid task", "status": "unknown_status"})
    assert response.status_code == 422


def test_create_todo_with_due_at(client: TestClient) -> None:
    due_date = "2026-08-20T18:00:00Z"
    response = client.post("/todos", json={"title": "Pay bills", "due_at": due_date})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Pay bills"
    assert data["status"] == "created"
    assert data["due_at"] is not None


def test_create_todo_invalid_payload(client: TestClient) -> None:
    response = client.post("/todos", json={})
    assert response.status_code == 422


def test_get_todos_empty(client: TestClient) -> None:
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "per_page": 20,
        "has_next_page": False,
    }


def test_get_todos_populated(client: TestClient) -> None:
    client.post("/todos", json={"title": "Task 1", "description": "First task", "status": "created"})
    client.post("/todos", json={"title": "Task 2", "status": "inprogress", "due_at": "2026-08-25T12:00:00Z"})

    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["has_next_page"] is False
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Task 2"
    assert data["items"][1]["title"] == "Task 1"


def test_get_todos_custom_page_and_limit(client: TestClient) -> None:
    for i in range(10):
        client.post("/todos", json={"title": f"Task {i:02d}"})

    response = client.get("/todos?page=2&per_page=3&sort=id:asc")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["per_page"] == 3
    assert data["has_next_page"] is True
    assert len(data["items"]) == 3
    assert [item["title"] for item in data["items"]] == ["Task 03", "Task 04", "Task 05"]


def test_get_todos_valid_custom_sort_and_case_insensitivity(client: TestClient) -> None:
    client.post("/todos", json={"title": "Beta Task", "due_at": "2026-09-02T10:00:00Z"})
    client.post("/todos", json={"title": "Alpha Task", "due_at": "2026-09-01T10:00:00Z"})

    response = client.get("/todos?sort=DUE_AT:ASC")
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["title"] == "Alpha Task"
    assert data["items"][1]["title"] == "Beta Task"


def test_get_todos_has_next_page_boundary(client: TestClient) -> None:
    for i in range(5):
        client.post("/todos", json={"title": f"Item {i}"})

    # Page 1 of 2 items -> has_next_page is True
    res1 = client.get("/todos?page=1&per_page=2")
    assert res1.status_code == 200
    assert res1.json()["has_next_page"] is True
    assert len(res1.json()["items"]) == 2

    # Page 3 of 2 items (last page with 1 item) -> has_next_page is False
    res3 = client.get("/todos?page=3&per_page=2")
    assert res3.status_code == 200
    assert res3.json()["has_next_page"] is False
    assert len(res3.json()["items"]) == 1


def test_get_todos_invalid_sort_field_422(client: TestClient) -> None:
    response = client.get("/todos?sort=secret_column:asc")
    assert response.status_code == 422


def test_get_todos_invalid_sort_direction_422(client: TestClient) -> None:
    response = client.get("/todos?sort=due_at:sideways")
    assert response.status_code == 422


def test_get_todos_page_bounds_422(client: TestClient) -> None:
    res_min = client.get("/todos?page=0")
    assert res_min.status_code == 422

    res_max = client.get("/todos?page=101")
    assert res_max.status_code == 422


def test_get_todos_per_page_bounds_422(client: TestClient) -> None:
    res_min = client.get("/todos?per_page=0")
    assert res_min.status_code == 422

    res_max = client.get("/todos?per_page=101")
    assert res_max.status_code == 422


def test_get_todo_by_id_success(client: TestClient) -> None:
    created = client.post(
        "/todos",
        json={"title": "Read a book", "description": "Chapter 1 to 5", "status": "inprogress"},
    ).json()
    todo_id = created["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Read a book"
    assert data["description"] == "Chapter 1 to 5"
    assert data["status"] == "inprogress"
    assert "due_at" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_todo_by_id_not_found(client: TestClient) -> None:
    response = client.get("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo with id 9999 not found"


def test_update_todo_status(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "In-progress task"}).json()
    todo_id = created["id"]
    assert created["status"] == "created"

    response = client.put(f"/todos/{todo_id}", json={"status": "completed"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["status"] == "completed"
    assert data["title"] == "In-progress task"


def test_update_todo_description(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Task with desc", "description": "Old notes"}).json()
    todo_id = created["id"]
    assert created["description"] == "Old notes"

    response = client.put(f"/todos/{todo_id}", json={"description": "Updated notes"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["description"] == "Updated notes"


def test_update_todo_clear_description(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Task to clear", "description": "Will be cleared"}).json()
    todo_id = created["id"]
    assert created["description"] == "Will be cleared"

    response = client.put(f"/todos/{todo_id}", json={"description": None})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["description"] is None


def test_update_todo_due_at(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Scheduled task"}).json()
    todo_id = created["id"]
    assert created["due_at"] is None

    new_due = "2026-09-01T10:00:00Z"
    response = client.put(f"/todos/{todo_id}", json={"due_at": new_due})
    assert response.status_code == 200
    data = response.json()
    assert data["due_at"] is not None


def test_update_todo_invalid_status(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Sample task"}).json()
    todo_id = created["id"]

    response = client.put(f"/todos/{todo_id}", json={"status": "invalid_status_value"})
    assert response.status_code == 422


def test_update_todo_not_found(client: TestClient) -> None:
    response = client.put("/todos/9999", json={"title": "Updated title"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo with id 9999 not found"


def test_delete_todo_success(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Delete me"}).json()
    todo_id = created["id"]

    delete_response = client.delete(f"/todos/{todo_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Todo deleted successfully"}

    get_response = client.get(f"/todos/{todo_id}")
    assert get_response.status_code == 404


def test_delete_todo_not_found(client: TestClient) -> None:
    response = client.delete("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo with id 9999 not found"

