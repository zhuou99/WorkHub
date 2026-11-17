"""pytest 夹具。

测试库用 tmp_path 临时文件而不是 :memory:：
真实文件能覆盖与生产一致的 WAL/pragma 行为；:memory: 需要 StaticPool，
一旦开第二条连接就静默失效（阶段 2 的 FTS5 裸 sqlite3 检查会踩到）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_db_engine, create_sessionmaker
from app.main import create_app

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "admin123"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "workhub-test.db"


@pytest.fixture
def engine(db_path: Path):
    eng = create_db_engine(db_path)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine) -> Session:
    factory = create_sessionmaker(engine)
    with factory() as db:
        yield db


@pytest.fixture
def app(db_path: Path):
    """一个隔离的应用实例（自己的临时库）。"""
    application = create_app(Settings(db_path=db_path, session_key="test-session-key"))
    with TestClient(application) as test_client:
        application.state.test_client = test_client
        yield application


@pytest.fixture
def client(app) -> TestClient:
    return app.state.test_client


@pytest.fixture
def auth_client(client) -> TestClient:
    """已登录的客户端（出厂口令 admin/admin123）。"""
    response = client.post("/api/auth/login", json={"userName": DEFAULT_USER, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200, response.text
    return client


def login(client: TestClient, user_name: str, password: str):
    return client.post("/api/auth/login", json={"userName": user_name, "password": password})
