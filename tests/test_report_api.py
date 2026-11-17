"""周报生成。"""

from __future__ import annotations


def _seed(auth_client):
    from datetime import datetime

    auth_client.post("/api/tasks", json={"title": "写代码"})
    task = auth_client.get("/api/tasks").json()["data"][0]
    auth_client.post(f"/api/tasks/{task['id']}/move", json={"status": "done"})

    client = auth_client.post("/api/clients", json={"name": "甲方"}).json()["data"]
    auth_client.post(
        "/api/finance/invoices",
        json={"clientId": client["id"], "amount": 1000, "taxRate": 6, "issueDate": datetime.now().isoformat()},
    )
    auth_client.post("/api/notes", json={"title": "一篇笔记", "content": "内容"})


def test_report_build(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/report", params={"days": 7})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["days"] == 7
    assert data["markdown"].startswith("# 周报")
    assert "任务" in data["markdown"]
    assert "财务" in data["markdown"]


def test_report_days_clamped(auth_client):
    response = auth_client.get("/api/report", params={"days": 999})
    assert response.status_code == 200
    assert response.json()["data"]["days"] == 7


def test_report_save_as_note(auth_client):
    response = auth_client.post("/api/report/note", json={"title": "小结", "markdown": "# 内容"})
    assert response.status_code == 200
    notes = auth_client.get("/api/notes").json()["data"]
    assert any(note["tags"] == "周报" for note in notes)


def test_report_save_empty_returns_400(auth_client):
    response = auth_client.post("/api/report/note", json={"title": "x", "markdown": ""})
    assert response.status_code == 400
