"""迁移口径：版本从 1 起严格递增，待执行集合按版本升序，越界版本收敛到合法区间。

移植自 WorkHub.Tests/SchemaMigrationTests.cs。
"""

from __future__ import annotations

from app.common.schema_migration import (
    ALL,
    latest,
    pending,
    resolve_version,
    statements_are_idempotent,
)


def test_all_starts_at_one():
    assert ALL[0].version == 1
    for i in range(1, len(ALL)):
        assert ALL[i].version > ALL[i - 1].version


def test_latest_matches_last_version():
    assert latest() == ALL[-1].version


def test_pending_zero_returns_all():
    todo = pending(0)
    assert len(todo) == len(ALL)
    for i in range(1, len(todo)):
        assert todo[i].version > todo[i - 1].version


def test_pending_latest_returns_empty():
    assert pending(latest()) == []


def test_pending_one_returns_only_newer():
    todo = pending(1)
    assert all(m.version > 1 for m in todo)
    assert len(todo) == len([m for m in ALL if m.version > 1])


def test_resolve_version_negative_clamps_to_zero():
    assert resolve_version(-7) == 0


def test_resolve_version_beyond_latest_clamps_to_latest():
    assert resolve_version(latest() + 10) == latest()


def test_resolve_version_in_range_unchanged():
    assert resolve_version(0) == 0
    assert resolve_version(latest()) == latest()


def test_all_statements_are_idempotent():
    # 幂等是重跑与失败重试的前提，禁止以后塞入非幂等语句。
    assert statements_are_idempotent()
    for migration in ALL:
        for sql in migration.statements:
            assert sql.startswith("CREATE INDEX IF NOT EXISTS"), f"{migration.name} 含非幂等语句：{sql}"
