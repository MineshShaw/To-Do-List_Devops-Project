from fastapi.testclient import TestClient

def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tasks_require_api_key(client: TestClient):
    response = client.get("/tasks")
    assert response.status_code == 401


AUTH_HEADERS = {"X-API-Key": "test-api-key"}


def test_create_task(client: TestClient):
    response = client.post(
        "/tasks", json={"title": "Test Task"}, headers=AUTH_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["completed"] == False
    assert "id" in data

def test_get_tasks(client: TestClient):
    # Create a task first
    client.post("/tasks", json={"title": "Test Task"}, headers=AUTH_HEADERS)
    response = client.get("/tasks", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Task"

def test_update_task(client: TestClient):
    # Create a task first
    create_response = client.post(
        "/tasks", json={"title": "Test Task"}, headers=AUTH_HEADERS
    )
    task_id = create_response.json()["id"]
    # Update the task
    response = client.put(
        f"/tasks/{task_id}", json={"completed": True}, headers=AUTH_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] == True

def test_delete_task(client: TestClient):
    # Create a task first
    create_response = client.post(
        "/tasks", json={"title": "Test Task"}, headers=AUTH_HEADERS
    )
    task_id = create_response.json()["id"]
    # Delete the task
    response = client.delete(f"/tasks/{task_id}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == {"message": "Task deleted successfully"}
    # Verify it's deleted
    get_response = client.get("/tasks", headers=AUTH_HEADERS)
    assert len(get_response.json()) == 0
