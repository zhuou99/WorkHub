"""SQLite 连接与 Session 工厂。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """所有实体的声明式基类。"""


def create_db_engine(db_path: Path | str) -> Engine:
    """建 SQLite 引擎并挂上 PRAGMA。原库就是 SQLite 单文件，配置沿用同一套。"""
    path = Path(db_path)
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):  # pragma: no cover - 驱动回调
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


def create_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    """expire_on_commit=False：提交后对象仍可读，组装响应不必重新查。"""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all(engine: Engine) -> None:
    """建齐所有表。已存在的表不改动（与 C# 版「只补缺表」的策略一致）。"""
    from app import models  # noqa: F401  触发所有模型注册到 metadata

    Base.metadata.create_all(engine)
