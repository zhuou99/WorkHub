"""调度口径：关闭不跑、从未跑过算到期、备份每天只在时间点后跑一次。

移植自 WorkHub.Tests/SchedulerOptionsTests.cs。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.common.scheduler_options import SchedulerOptions, is_backup_due, is_due, normalize


def test_normalize_null_returns_defaults():
    o = normalize(None)
    assert o.enabled is False
    assert o.rss_minutes == 30
    assert o.repo_minutes == 60
    assert o.backup_enabled is False
    assert o.backup_hour == 3


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-5, 0), (0, 0), (15, 15), (1441, 1440)],
)
def test_normalize_clamps_intervals(value, expected):
    o = normalize(SchedulerOptions(rss_minutes=value, repo_minutes=value, backup_hour=30))
    assert o.rss_minutes == expected
    assert o.repo_minutes == expected
    assert o.backup_hour == 23


def test_is_due_never_run_is_due():
    assert is_due(datetime.now(), None, 30) is True


@pytest.mark.parametrize("minutes", [0, -10])
def test_is_due_disabled_never_due(minutes):
    assert is_due(datetime.now(), None, minutes) is False
    assert is_due(datetime.now(), datetime.now() - timedelta(hours=5), minutes) is False


def test_is_due_before_interval_not_due():
    now = datetime(2026, 11, 6, 10, 0, 0)
    assert is_due(now, now - timedelta(minutes=29), 30) is False
    assert is_due(now, now - timedelta(minutes=30), 30) is True
    assert is_due(now, now - timedelta(minutes=31), 30) is True


def test_is_backup_due_runs_once_per_day():
    now = datetime(2026, 11, 6, 3, 5, 0)
    # 从没备份过：过了 3 点就补一次。
    assert is_backup_due(now, None, 3) is True
    # 今天 3 点已经跑过：不再跑。
    assert is_backup_due(now, datetime(2026, 11, 6, 3, 1, 0), 3) is False
    # 昨天跑过：今天到期。
    assert is_backup_due(now, datetime(2026, 11, 5, 3, 1, 0), 3) is True


def test_is_backup_due_before_hour_not_due():
    assert is_backup_due(datetime(2026, 11, 6, 2, 59, 0), None, 3) is False


@pytest.mark.parametrize("hour", [-1, 24])
def test_is_backup_due_invalid_hour_never_due(hour):
    assert is_backup_due(datetime.now(), None, hour) is False
