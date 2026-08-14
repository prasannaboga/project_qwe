from fastapi.testclient import TestClient


def test_create_todo(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "Buy groceries"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_todo_invalid(client: TestClient) -> None:
    response = client.post("/todos", json={})
    assert response.status_code == 422


def test_get_todos_empty(client: TestClient) -> None:
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []


def test_get_todos_populated(client: TestClient) -> None:
    client.post("/todos", json={"title": "Task 1"})
    client.post("/todos", json={"title": "Task 2"})

    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Task 1"
    assert data[1]["title"] == "Task 2"


def test_get_todo_by_id_success(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Read a book"}).json()
    todo_id = created["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Read a book"


def test_get_todo_by_id_not_found(client: TestClient) -> None:
    response = client.get("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo with id 9999 not found"


def test_update_todo_success(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "Initial title"}).json()
    todo_id = created["id"]

    response = client.put(f"/todos/{todo_id}", json={"title": "Updated title"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Updated title"


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
