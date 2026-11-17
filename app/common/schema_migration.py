"""数据库结构版本：版本号存 SysConfig，不另开版本表。

对应 C# 的 WorkHub/Common/SchemaMigration.cs。

所有语句必须幂等（CREATE INDEX IF NOT EXISTS），这样在旧库上重跑、
或迁移中途失败后再次启动都不会报错。版本号只在整条迁移成功后前移。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = [
    "SchemaMigration",
    "ALL",
    "VERSION_KEY",
    "latest",
    "resolve_version",
    "pending",
    "run",
]

logger = logging.getLogger("workhub.schema")

VERSION_KEY = "workhub.schema.version"


@dataclass(frozen=True)
class SchemaMigration:
    """一条迁移：版本号、名称与按序执行的幂等语句。"""

    version: int
    name: str
    statements: tuple[str, ...]


ALL: tuple[SchemaMigration, ...] = (
    SchemaMigration(
        1,
        "索引基线",
        (
            "CREATE INDEX IF NOT EXISTS ix_wh_expense_date ON wh_expense(HappenDate);",
            "CREATE INDEX IF NOT EXISTS ix_wh_payment_date ON wh_payment(PayDate);",
            "CREATE INDEX IF NOT EXISTS ix_wh_invoice_date ON wh_invoice(IssueDate);",
            "CREATE INDEX IF NOT EXISTS ix_wh_payment_plan_due ON wh_payment_plan(DueDate);",
            "CREATE INDEX IF NOT EXISTS ix_wh_audit_time ON wh_audit(Time);",
        ),
    ),
)


def latest() -> int:
    return max(m.version for m in ALL)


def resolve_version(stored: int) -> int:
    """库里读到的版本收敛到 [0, 最新版]，防止脏数据或回退旧程序后越界。"""
    return min(latest(), max(0, stored))


def pending(current: int) -> list[SchemaMigration]:
    """待执行迁移：版本大于当前值，按版本升序。"""
    return sorted((m for m in ALL if m.version > current), key=lambda m: m.version)


def _read_version(session: Session) -> int:
    try:
        row = session.execute(
            text("SELECT ConfigValue FROM SysConfig WHERE AppId = :app AND ConfigKey = :key"),
            {"app": "WorkHub", "key": VERSION_KEY},
        ).first()
    except Exception:
        # 读不到版本按 0 起算：最坏结果是把幂等迁移重跑一遍，不会动坏已有数据。
        return 0
    if not row or row[0] is None:
        return 0
    try:
        return int(str(row[0]).strip())
    except ValueError:
        return 0


def _save_version(session: Session, version: int) -> None:
    session.execute(
        text(
            "INSERT INTO SysConfig (AppId, ConfigKey, ConfigValue) VALUES (:app, :key, :value) "
            "ON CONFLICT(AppId, ConfigKey) DO UPDATE SET ConfigValue = excluded.ConfigValue"
        ),
        {"app": "WorkHub", "key": VERSION_KEY, "value": str(version)},
    )


def _has_data(session: Session) -> bool:
    """探测有没有业务数据；探测失败按「有数据」处理，宁可多备一份。"""
    try:
        return bool(session.execute(text("SELECT COUNT(1) FROM wh_bookmark")).scalar() or 0)
    except Exception:
        return True


def run(session: Session, backup: Callable[[], object] | None = None) -> int:
    """启动期执行迁移，返回执行到的版本。

    全新空库不备份；已有数据时先打一个包（备份失败不阻断迁移）。
    某条语句失败就停在当前版本之前，下次启动从同一版重试（语句均幂等）。
    """
    current = resolve_version(_read_version(session))
    todo = pending(current)
    if not todo:
        logger.info("数据库结构已是最新（v%s）", current)
        return current

    if _has_data(session) and backup is not None:
        try:
            backup()
        except Exception as exc:  # 备份失败不阻断迁移
            logger.warning("数据库迁移前备份失败，继续迁移：%s", exc)

    done = current
    for migration in todo:
        try:
            for sql in migration.statements:
                session.execute(text(sql))
        except Exception:
            # 失败就停在上一版：版本号不前移，下次启动会重跑这一版。
            logger.exception("数据库迁移 v%s 失败：%s", migration.version, migration.name)
            session.rollback()
            return done

        _save_version(session, migration.version)
        session.commit()
        done = migration.version
        logger.info("数据库迁移：v%s %s（%s 条语句）", migration.version, migration.name, len(migration.statements))

    return done


def statements_are_idempotent(migrations: Sequence[SchemaMigration] = ALL) -> bool:
    """每条语句都必须以 CREATE INDEX IF NOT EXISTS 开头（只允许建索引）。"""
    return all(
        statement.startswith("CREATE INDEX IF NOT EXISTS")
        for migration in migrations
        for statement in migration.statements
    )
