"""任务看板接口：换列语义。"""

from __future__ import annotations


def _create_task(client, title="写代码", **extra) -> dict:
    response = client.post("/api/tasks", json={"title": title, **extra})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_task_defaults(auth_client):
    task = _create_task(auth_client)
    assert task["title"] == "写代码"
    assert task["status"] == "todo"
    assert task["priority"] == "normal"
    assert task["doneTime"] is None


def test_move_to_done_sets_done_time(auth_client):
    task = _create_task(auth_client)
    response = auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["data"]["doneTime"] is not None


def test_move_away_from_done_clears_done_time(auth_client):
    task = _create_task(auth_client)
    auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "done"})
    response = auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "doing"})
    assert response.status_code == 200
    assert response.json()["data"]["doneTime"] is None


def test_move_to_unknown_column_is_404(auth_client):
    task = _create_task(auth_client)
    response = auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "archived"})
    assert response.status_code == 404


def test_move_to_same_column_is_a_no_op(auth_client, app):
    task = _create_task(auth_client)
    auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "doing"})
    before = auth_client.get("/api/tasks").json()["data"][0]["modifyTime"]

    response = auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "doing"})
    assert response.status_code == 200
    after = auth_client.get("/api/tasks").json()["data"][0]["modifyTime"]
    assert before == after


def test_move_unknown_task_is_404(auth_client):
    response = auth_client.post("/api/tasks/does-not-exist/move", json={"status": "done"})
    assert response.status_code == 404


def test_delete_task(auth_client):
    task = _create_task(auth_client)
    assert auth_client.delete(f"/api/tasks/{task['id']}").status_code == 200
    assert auth_client.get("/api/tasks").json()["data"] == []
