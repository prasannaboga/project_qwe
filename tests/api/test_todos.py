from fastapi.testclient import TestClient

from project_qwe.main import app

client = TestClient(app)


def test_get_todos() -> None:
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == {"message": "Get todos is not implemented yet"}


def test_get_todo_by_id() -> None:
    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Get todo 1 is not implemented yet"}


def test_create_todo() -> None:
    response = client.post("/todos")
    assert response.status_code == 200
    assert response.json() == {"message": "Todo creation is not implemented yet"}


def test_update_todo() -> None:
    response = client.put("/todos/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Update todo 1 is not implemented yet"}


def test_delete_todo() -> None:
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Delete todo 1 is not implemented yet"}
