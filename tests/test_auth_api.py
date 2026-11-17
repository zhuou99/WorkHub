"""认证接口：登录、锁定、会话、登出。"""

from __future__ import annotations

from sqlalchemy import select

from app.models.sysconfig import SysConfig
from app.models.system import WhAuditLog


def _guard(client) -> dict:
    response = client.get("/api/auth/guard")
    assert response.status_code == 200
    return response.json()["data"]


def _audit_actions(app) -> list[str]:
    """直接从库里读审计——失败登录的用例里客户端并没有登录态。"""
    with app.state.sessionmaker() as session:
        rows = session.execute(select(WhAuditLog)).scalars().all()
    return [row.Action for row in rows]


def test_health_is_anonymous_and_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["schemaVersion"] == 1


def test_guard_is_anonymous(client):
    body = _guard(client)
    assert body["remainingTries"] == 5
    assert body["locked"] is False
    assert body["defaultPassword"] is True


def test_login_with_default_credentials(client):
    response = client.post("/api/auth/login", json={"userName": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["userName"] == "admin"
    assert data["role"] == "Owner"
    assert data["name"] == "主人"
    assert "workhub_session" in response.cookies


def test_login_with_blank_username_does_not_touch_counter(client, app):
    response = client.post("/api/auth/login", json={"userName": "", "password": "x"})
    assert response.status_code == 401
    assert _guard(client)["failures"] == 0
    assert "login-fail" not in _audit_actions(app)


def test_login_with_wrong_password_counts_failures(client, app):
    response = client.post("/api/auth/login", json={"userName": "admin", "password": "wrong"})
    assert response.status_code == 401
    assert _guard(client)["failures"] == 1
    assert "login-fail" in _audit_actions(app)


def test_fifth_failure_locks_the_account(client, app):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"userName": "admin", "password": "wrong"}).status_code == 401
    guard = _guard(client)
    assert guard["locked"] is True
    assert guard["remainingSeconds"] > 0
    # 计数在触发锁定时归零
    assert guard["failures"] == 0
    assert "login-fail-locked" in _audit_actions(app)


def test_locked_account_rejects_correct_password(client, app):
    for _ in range(5):
        client.post("/api/auth/login", json={"userName": "admin", "password": "wrong"})
    response = client.post("/api/auth/login", json={"userName": "admin", "password": "admin123"})
    assert response.status_code == 401
    assert "login-locked" in _audit_actions(app)


def test_successful_login_resets_the_counter(client, app):
    client.post("/api/auth/login", json={"userName": "admin", "password": "wrong"})
    assert _guard(client)["failures"] == 1
    client.post("/api/auth/login", json={"userName": "admin", "password": "admin123"})
    assert _guard(client)["failures"] == 0


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_the_signed_in_user(auth_client):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["data"]["userName"] == "admin"


def test_logout_clears_the_session(auth_client):
    assert auth_client.post("/api/auth/logout").status_code == 200
    assert auth_client.get("/api/auth/me").status_code == 401


def test_guard_key_is_stored_per_account(client, app):
    """失败计数按账号存，不串号。"""
    client.post("/api/auth/login", json={"userName": "admin", "password": "wrong"})
    with app.state.sessionmaker() as session:
        rows = session.execute(
            select(SysConfig.ConfigKey, SysConfig.ConfigValue).where(SysConfig.ConfigKey.like("workhub.auth.guard%"))
        ).all()
    keys = {row[0] for row in rows}
    assert "workhub.auth.guard.admin" in keys


def test_login_writes_audit_row(app, auth_client):
    with app.state.sessionmaker() as session:
        rows = session.execute(select(WhAuditLog).where(WhAuditLog.Action == "login-success")).scalars().all()
    assert len(rows) == 1
    assert rows[0].UserName == "admin"
