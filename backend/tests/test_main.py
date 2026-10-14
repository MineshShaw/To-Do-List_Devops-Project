"""Test suite for the JWT-protected To-Do API.

Covers: health, auth (signup/login), task CRUD, cross-user data isolation,
status filtering and request validation.
"""

from fastapi.testclient import TestClient


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --------------------------------------------------------------------------- #
# Auth: signup
# --------------------------------------------------------------------------- #
def test_signup_returns_jwt(client: TestClient):
    response = client.post(
        "/signup", json={"username": "alice", "password": "secret123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_signup_duplicate_username_rejected(client: TestClient):
    client.post("/signup", json={"username": "alice", "password": "secret123"})
    response = client.post(
        "/signup", json={"username": "alice", "password": "other-pass"}
    )
    assert response.status_code == 400


def test_signup_short_password_rejected(client: TestClient):
    response = client.post("/signup", json={"username": "bob", "password": "123"})
    assert response.status_code == 422


def test_signup_missing_password_rejected(client: TestClient):
    response = client.post("/signup", json={"username": "bob"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Auth: login
# --------------------------------------------------------------------------- #
def test_login_returns_jwt(client: TestClient):
    client.post("/signup", json={"username": "alice", "password": "secret123"})
    response = client.post(
        "/login", data={"username": "alice", "password": "secret123"}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_unauthorized(client: TestClient):
    client.post("/signup", json={"username": "alice", "password": "secret123"})
    response = client.post(
        "/login", data={"username": "alice", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_user_unauthorized(client: TestClient):
    response = client.post(
        "/login", data={"username": "ghost", "password": "secret123"}
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Auth failures on protected routes
# --------------------------------------------------------------------------- #
def test_tasks_without_token_returns_401(client: TestClient):
    assert client.get("/tasks").status_code == 401


def test_create_task_without_token_returns_401(client: TestClient):
    response = client.post("/tasks", json={"title": "No auth"})
    assert response.status_code == 401


def test_tasks_with_malformed_token_returns_401(client: TestClient):
    response = client.get(
        "/tasks", headers={"Authorization": "Bearer not-a-real.jwt.token"}
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Task CRUD (authenticated)
# --------------------------------------------------------------------------- #
def test_create_task_defaults_to_pending(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post("/tasks", json={"title": "Test Task"}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "pending"
    assert data["description"] is None
    assert data["due_date"] is None
    assert "id" in data
    assert "owner_id" in data


def test_create_task_with_all_fields(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post(
        "/tasks",
        json={
            "title": "Ship the release",
            "description": "Cut the v2 tag",
            "status": "in-progress",
            "due_date": "2026-01-15",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "in-progress"
    assert data["description"] == "Cut the v2 tag"
    assert data["due_date"] == "2026-01-15"


def test_get_tasks_returns_only_own(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    client.post("/tasks", json={"title": "Test Task"}, headers=headers)
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Task"


def test_get_single_task(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    task_id = client.post(
        "/tasks", json={"title": "Test Task"}, headers=headers
    ).json()["id"]
    response = client.get(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == task_id


def test_update_task_status_and_due_date(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    task_id = client.post(
        "/tasks", json={"title": "Test Task"}, headers=headers
    ).json()["id"]
    response = client.put(
        f"/tasks/{task_id}",
        json={"status": "done", "due_date": "2026-02-01"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["due_date"] == "2026-02-01"
    # Untouched fields are preserved.
    assert data["title"] == "Test Task"


def test_delete_task(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    task_id = client.post(
        "/tasks", json={"title": "Test Task"}, headers=headers
    ).json()["id"]
    response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Task deleted successfully"}
    assert client.get("/tasks", headers=headers).json() == []


def test_get_task_not_found(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    assert client.get("/tasks/9999", headers=headers).status_code == 404


def test_update_task_not_found(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.put("/tasks/9999", json={"status": "done"}, headers=headers)
    assert response.status_code == 404


def test_delete_task_not_found(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    assert client.delete("/tasks/9999", headers=headers).status_code == 404


# --------------------------------------------------------------------------- #
# Data isolation: User A must not touch User B's tasks
# --------------------------------------------------------------------------- #
def test_user_cannot_read_other_users_task(client: TestClient, make_auth_headers):
    alice = make_auth_headers("alice", "secret123")
    bob = make_auth_headers("bob", "secret456")

    bob_task_id = client.post(
        "/tasks", json={"title": "Bob's secret"}, headers=bob
    ).json()["id"]

    response = client.get(f"/tasks/{bob_task_id}", headers=alice)
    assert response.status_code in (403, 404)


def test_user_cannot_update_other_users_task(client: TestClient, make_auth_headers):
    alice = make_auth_headers("alice", "secret123")
    bob = make_auth_headers("bob", "secret456")

    bob_task_id = client.post(
        "/tasks", json={"title": "Bob's secret"}, headers=bob
    ).json()["id"]

    response = client.put(
        f"/tasks/{bob_task_id}", json={"status": "done"}, headers=alice
    )
    assert response.status_code in (403, 404)

    # Confirm the task is genuinely unchanged.
    assert client.get(f"/tasks/{bob_task_id}", headers=bob).json()["status"] == "pending"


def test_user_cannot_delete_other_users_task(client: TestClient, make_auth_headers):
    alice = make_auth_headers("alice", "secret123")
    bob = make_auth_headers("bob", "secret456")

    bob_task_id = client.post(
        "/tasks", json={"title": "Bob's secret"}, headers=bob
    ).json()["id"]

    response = client.delete(f"/tasks/{bob_task_id}", headers=alice)
    assert response.status_code in (403, 404)

    # Bob's task still exists.
    assert client.get(f"/tasks/{bob_task_id}", headers=bob).status_code == 200


def test_task_lists_are_isolated_per_user(client: TestClient, make_auth_headers):
    alice = make_auth_headers("alice", "secret123")
    bob = make_auth_headers("bob", "secret456")

    client.post("/tasks", json={"title": "Alice task"}, headers=alice)
    client.post("/tasks", json={"title": "Bob task"}, headers=bob)

    alice_titles = [t["title"] for t in client.get("/tasks", headers=alice).json()]
    bob_titles = [t["title"] for t in client.get("/tasks", headers=bob).json()]

    assert alice_titles == ["Alice task"]
    assert bob_titles == ["Bob task"]


# --------------------------------------------------------------------------- #
# Filtering by status
# --------------------------------------------------------------------------- #
def _seed_statuses(client, headers):
    client.post("/tasks", json={"title": "A", "status": "pending"}, headers=headers)
    client.post("/tasks", json={"title": "B", "status": "pending"}, headers=headers)
    client.post("/tasks", json={"title": "C", "status": "in-progress"}, headers=headers)
    client.post("/tasks", json={"title": "D", "status": "done"}, headers=headers)


def test_filter_tasks_by_pending(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    _seed_statuses(client, headers)

    response = client.get("/tasks?status=pending", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {task["status"] for task in data} == {"pending"}


def test_filter_tasks_by_done(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    _seed_statuses(client, headers)

    data = client.get("/tasks?status=done", headers=headers).json()
    assert len(data) == 1
    assert data[0]["title"] == "D"


def test_filter_tasks_by_in_progress(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    _seed_statuses(client, headers)

    data = client.get("/tasks?status=in-progress", headers=headers).json()
    assert len(data) == 1
    assert data[0]["title"] == "C"


def test_filter_returns_empty_when_none_match(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    client.post("/tasks", json={"title": "A", "status": "pending"}, headers=headers)

    response = client.get("/tasks?status=done", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_filter_invalid_status_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.get("/tasks?status=archived", headers=headers)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_create_task_invalid_status_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post(
        "/tasks", json={"title": "Bad status", "status": "archived"}, headers=headers
    )
    assert response.status_code == 422


def test_update_task_invalid_status_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    task_id = client.post(
        "/tasks", json={"title": "Test Task"}, headers=headers
    ).json()["id"]
    response = client.put(
        f"/tasks/{task_id}", json={"status": "archived"}, headers=headers
    )
    assert response.status_code == 422


def test_create_task_invalid_due_date_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post(
        "/tasks", json={"title": "Bad date", "due_date": "not-a-date"}, headers=headers
    )
    assert response.status_code == 422


def test_create_task_missing_title_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    assert client.post("/tasks", json={}, headers=headers).status_code == 422


def test_create_task_invalid_title_type_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post("/tasks", json={"title": 123}, headers=headers)
    assert response.status_code == 422


def test_create_task_empty_title_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    response = client.post("/tasks", json={"title": "   "}, headers=headers)
    assert response.status_code == 422


def test_update_task_empty_title_returns_422(client: TestClient, make_auth_headers):
    headers = make_auth_headers()
    task_id = client.post(
        "/tasks", json={"title": "Test Task"}, headers=headers
    ).json()["id"]
    response = client.put(
        f"/tasks/{task_id}", json={"title": ""}, headers=headers
    )
    assert response.status_code == 422
