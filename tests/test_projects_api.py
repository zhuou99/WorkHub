"""项目接口：里程碑级联、解绑、删除影响预览的分组顺序。"""

from __future__ import annotations

from sqlalchemy import select

from app.models.crm import WhMilestone, WhProject, WhTask


def _create_project(client, name="官网改造", **extra) -> dict:
    response = client.post("/api/projects", json={"name": name, **extra})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_and_list_project(auth_client):
    created = _create_project(auth_client, "官网改造", amount=10000, clientId="c1")
    assert created["name"] == "官网改造"
    assert created["amount"] == 10000
    assert created["status"] == "talking"

    rows = auth_client.get("/api/projects").json()["data"]
    assert len(rows) == 1


def test_project_list_puts_finished_last(auth_client):
    _create_project(auth_client, "进行中", status="active")
    _create_project(auth_client, "已完结", status="done")
    rows = auth_client.get("/api/projects").json()["data"]
    assert [row["name"] for row in rows] == ["进行中", "已完结"]


def test_milestone_round_trip(auth_client):
    project_id = _create_project(auth_client)["id"]
    response = auth_client.post("/api/projects/milestones", json={"projectId": project_id, "title": "上线"})
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "上线"

    rows = auth_client.get("/api/projects/milestones").json()["data"]
    assert len(rows) == 1


def test_delete_impact_group_order(auth_client):
    project_id = _create_project(auth_client)["id"]
    auth_client.post("/api/projects/milestones", json={"projectId": project_id, "title": "上线"})
    auth_client.post("/api/tasks", json={"title": "写代码", "projectId": project_id})

    response = auth_client.get(f"/api/projects/delete-impact/{project_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert [group["label"] for group in data["groups"]] == [
        "里程碑", "任务", "发票", "支出", "开源仓库", "回款计划", "文章",
    ]
    assert data["groups"][0]["mode"] == "cascade"
    assert data["groups"][5]["mode"] == "cascade"
    assert data["groups"][0]["count"] == 1
    assert data["groups"][1]["count"] == 1


def test_delete_cascades_milestones_and_plans(auth_client, app):
    project_id = _create_project(auth_client)["id"]
    auth_client.post("/api/projects/milestones", json={"projectId": project_id, "title": "上线"})
    auth_client.post("/api/finance/plans", json={"projectId": project_id, "title": "首款", "amount": 3000})

    response = auth_client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert "里程碑" in response.json()["message"]

    with app.state.sessionmaker() as session:
        assert session.execute(select(WhMilestone).where(WhMilestone.ProjectId == project_id)).scalars().all() == []
        assert session.execute(select(WhProject).where(WhProject.Id == project_id)).scalars().all() == []


def test_delete_with_detach_clears_task_reference(auth_client, app):
    project_id = _create_project(auth_client)["id"]
    task = auth_client.post("/api/tasks", json={"title": "写代码", "projectId": project_id}).json()["data"]

    auth_client.delete(f"/api/projects/{project_id}?detach=true")

    with app.state.sessionmaker() as session:
        kept = session.execute(select(WhTask).where(WhTask.Id == task["id"])).scalars().first()
        assert kept is not None and kept.ProjectId == ""


def test_delete_without_detach_keeps_task_reference(auth_client, app):
    project_id = _create_project(auth_client)["id"]
    task = auth_client.post("/api/tasks", json={"title": "写代码", "projectId": project_id}).json()["data"]

    auth_client.delete(f"/api/projects/{project_id}?detach=false")

    with app.state.sessionmaker() as session:
        kept = session.execute(select(WhTask).where(WhTask.Id == task["id"])).scalars().first()
        assert kept is not None and kept.ProjectId == project_id
