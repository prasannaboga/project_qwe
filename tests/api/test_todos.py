from datetime import datetime, timezone
from fastapi.testclient import TestClient


def test_create_todo_default_status(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "Buy groceries"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["status"] == "created"
    assert data["due_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_todo_with_valid_statuses(client: TestClient) -> None:
    for status in ["created", "process", "completed"]:
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
    assert response.json() == []


def test_get_todos_populated(client: TestClient) -> None:
    client.post("/todos", json={"title": "Task 1", "status": "created"})
    client.post("/todos", json={"title": "Task 2", "status": "process", "due_at": "2026-08-25T12:00:00Z"})

    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Task 1"
    assert data[0]["status"] == "created"
    assert data[1]["title"] == "Task 2"
    assert data[1]["status"] == "process"
    assert data[1]["due_at"] is not None


def test_get_todo_by_id_success(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Read a book", "status": "process"}).json()
    todo_id = created["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Read a book"
    assert data["status"] == "process"
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
