from fastapi.testclient import TestClient


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tasks_allow_direct_access(client: TestClient):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client: TestClient):
    response = client.post("/tasks", json={"title": "Test Task"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["completed"] is False
    assert "id" in data


def test_get_tasks(client: TestClient):
    client.post("/tasks", json={"title": "Test Task"})
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Task"


def test_update_task(client: TestClient):
    create_response = client.post("/tasks", json={"title": "Test Task"})
    task_id = create_response.json()["id"]
    response = client.put(f"/tasks/{task_id}", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_delete_task(client: TestClient):
    create_response = client.post("/tasks", json={"title": "Test Task"})
    task_id = create_response.json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Task deleted successfully"}
    assert client.get("/tasks").json() == []


def test_get_task_not_found(client: TestClient):
    assert client.get("/tasks/999").status_code == 404


def test_update_task_not_found(client: TestClient):
    response = client.put("/tasks/999", json={"completed": True})
    assert response.status_code == 404


def test_delete_task_not_found(client: TestClient):
    assert client.delete("/tasks/999").status_code == 404


def test_create_task_missing_title(client: TestClient):
    assert client.post("/tasks", json={}).status_code == 422


def test_create_task_invalid_title_type(client: TestClient):
    assert client.post("/tasks", json={"title": 123}).status_code == 422


def test_create_task_empty_title(client: TestClient):
    assert client.post("/tasks", json={"title": "   "}).status_code == 422


def test_update_task_empty_title(client: TestClient):
    task_id = client.post("/tasks", json={"title": "Test Task"}).json()["id"]
    response = client.put(f"/tasks/{task_id}", json={"title": ""})
    assert response.status_code == 422
