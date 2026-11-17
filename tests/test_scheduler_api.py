"""定时任务：设置与状态。"""

from __future__ import annotations


def test_scheduler_defaults(auth_client):
    response = auth_client.get("/api/scheduler/options")
    assert response.status_code == 200
    options = response.json()["data"]
    assert options["enabled"] is False
    assert options["rssMinutes"] == 30
    assert options["repoMinutes"] == 60
    assert options["backupEnabled"] is False
    assert options["backupHour"] == 3


def test_scheduler_save_clamps(auth_client):
    response = auth_client.post(
        "/api/scheduler/options",
        json={"enabled": True, "rssMinutes": 9999, "repoMinutes": -5, "backupEnabled": True, "backupHour": 30},
    )
    assert response.status_code == 200

    options = auth_client.get("/api/scheduler/options").json()["data"]
    assert options["rssMinutes"] == 1440
    assert options["repoMinutes"] == 0
    assert options["backupHour"] == 23


def test_scheduler_state(auth_client):
    response = auth_client.get("/api/scheduler/state")
    assert response.status_code == 200
    state = response.json()["data"]
    assert state["lastRss"] is None
    assert state["lastMessage"] is None


def test_scheduler_unknown_job(auth_client):
    response = auth_client.post("/api/scheduler/run", json={"job": "nope"})
    assert response.status_code == 400


def test_scheduler_requires_owner(auth_client, client):
    auth_client.post("/api/users", json={"userName": "viewer1", "password": "secret123", "role": "Viewer"})
    from fastapi.testclient import TestClient

    with TestClient(auth_client.app) as other:
        other.post("/api/auth/login", json={"userName": "viewer1", "password": "secret123"})
        assert other.post("/api/scheduler/options", json={"enabled": True}).status_code == 403
