"""账号管理接口：增删改、重名、最后一个 Owner 的保护。"""

from __future__ import annotations

from sqlalchemy import select

from app.models.system import WhAuditLog


def _audit(app) -> list[tuple[str, str]]:
    with app.state.sessionmaker() as session:
        rows = session.execute(select(WhAuditLog)).scalars().all()
    return [(row.Kind, row.Action) for row in rows]


def test_list_users_requires_owner(auth_client):
    response = auth_client.get("/api/users")
    assert response.status_code == 200
    names = [item["userName"] for item in response.json()["data"]]
    assert "admin" in names


def test_list_users_hides_password_hash(auth_client):
    response = auth_client.get("/api/users")
    assert response.status_code == 200
    assert "passwordHash" not in response.json()["data"][0]


def test_create_user(auth_client):
    response = auth_client.post(
        "/api/users",
        json={"userName": "editor1", "displayName": "编辑一号", "password": "secret123", "role": "Editor"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["userName"] == "editor1"
    assert data["role"] == "Editor"
    assert data["enabled"] is True


def test_create_user_rejects_duplicate_ignoring_case(auth_client):
    auth_client.post("/api/users", json={"userName": "dup", "password": "secret123", "role": "Editor"})
    response = auth_client.post("/api/users", json={"userName": "DUP", "password": "secret123", "role": "Editor"})
    assert response.status_code == 400
    assert "已存在" in response.json()["message"]


def test_create_user_rejects_bad_role(auth_client):
    response = auth_client.post("/api/users", json={"userName": "x1", "password": "secret123", "role": "Guest"})
    assert response.status_code == 400
    assert "Owner / Editor / Viewer" in response.json()["message"]


def test_create_user_rejects_short_password(auth_client):
    response = auth_client.post("/api/users", json={"userName": "x2", "password": "123", "role": "Editor"})
    assert response.status_code == 400
    assert "6 位" in response.json()["message"]


def test_create_user_rejects_illegal_name(auth_client):
    response = auth_client.post("/api/users", json={"userName": "a b", "password": "secret123", "role": "Editor"})
    assert response.status_code == 400
    assert "空格" in response.json()["message"]


def test_last_enabled_owner_cannot_be_disabled(auth_client):
    users = auth_client.get("/api/users").json()["data"]
    admin = next(item for item in users if item["userName"] == "admin")
    response = auth_client.patch(f"/api/users/{admin['id']}", json={"role": "Owner", "enabled": False})
    assert response.status_code == 400
    assert "最后一个启用中的 Owner" in response.json()["message"]


def test_last_enabled_owner_cannot_be_deleted(app):
    """服务层的兜底保护。

    走 HTTP 时这条路到不了：删自己先被「不能删除当前登录的账号」拦下，
    删别人时对方不是 Owner 也不触发——与 C# 那边同样的检查顺序。
    """
    from app.common.exceptions import WorkHubError
    from app.services.audit_service import AuditService
    from app.services.user_service import UserService

    with app.state.sessionmaker() as session:
        users = UserService(session, AuditService(session))
        admin = users.find("admin")
        try:
            users.delete(admin.Id, current_user_name="someone-else")
        except WorkHubError as exc:
            assert "最后一个启用中的 Owner" in str(exc)
        else:
            raise AssertionError("最后一个 Owner 应该删不掉")


def test_cannot_delete_current_account(auth_client):
    users = auth_client.get("/api/users").json()["data"]
    admin = next(item for item in users if item["userName"] == "admin")
    response = auth_client.delete(f"/api/users/{admin['id']}")
    assert response.status_code == 400
    assert "当前登录" in response.json()["message"]


def test_reset_password(auth_client):
    users = auth_client.get("/api/users").json()["data"]
    admin = next(item for item in users if item["userName"] == "admin")
    response = auth_client.post(f"/api/users/{admin['id']}/password", json={"password": "newpass123"})
    assert response.status_code == 200
    assert auth_client.post("/api/auth/login", json={"userName": "admin", "password": "newpass123"}).status_code == 200


def test_update_role(auth_client):
    auth_client.post("/api/users", json={"userName": "viewer1", "password": "secret123", "role": "Editor"})
    users = auth_client.get("/api/users").json()["data"]
    viewer = next(item for item in users if item["userName"] == "viewer1")
    response = auth_client.patch(f"/api/users/{viewer['id']}", json={"role": "Viewer", "enabled": True})
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "Viewer"


def test_user_management_writes_audit(auth_client, app):
    auth_client.post("/api/users", json={"userName": "audited", "password": "secret123", "role": "Editor"})
    assert ("settings", "user-create") in _audit(app)


def test_viewer_cannot_manage_users(auth_client, client):
    """建一个 Viewer，它连账号列表都看不到。"""
    auth_client.post("/api/users", json={"userName": "viewer1", "password": "secret123", "role": "Viewer"})
    users = auth_client.get("/api/users").json()["data"]
    viewer = next(item for item in users if item["userName"] == "viewer1")

    # 换一个新客户端登录 Viewer（避免 Cookie 串号）
    from fastapi.testclient import TestClient

    with TestClient(auth_client.app) as other:
        assert other.post("/api/auth/login", json={"userName": "viewer1", "password": "secret123"}).status_code == 200
        assert other.get("/api/users").status_code == 403
        assert other.get("/api/clients").status_code == 200
        response = other.post("/api/clients", json={"name": "试试"})
        assert response.status_code == 403
    assert viewer["role"] == "Viewer"
