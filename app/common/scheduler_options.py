"""定时任务设置：关掉即不调度；间隔 0 表示该任务不跑。

对应 C# 的 WorkHub/Models/SchedulerOptions.cs。阶段 1 只落地纯逻辑，
调度器本体在阶段 2。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = ["SchedulerOptions", "SchedulerState", "normalize", "is_due", "is_backup_due"]


@dataclass
class SchedulerOptions:
    enabled: bool = False
    rss_minutes: int = 30
    repo_minutes: int = 60
    backup_enabled: bool = False
    backup_hour: int = 3

    @classmethod
    def normalize(cls, options: SchedulerOptions | None) -> SchedulerOptions:
        """把配置收敛到合法范围；缺省值原样保留。"""
        return normalize(options)


@dataclass
class SchedulerState:
    """最近一次各任务的执行时间与结果，用于设置页展示。"""

    last_rss: datetime | None = None
    last_repo: datetime | None = None
    last_backup: datetime | None = None
    last_run_at: datetime | None = None
    last_message: str | None = None


def normalize(options: SchedulerOptions | None) -> SchedulerOptions:
    """把配置收敛到合法范围；缺省值原样保留。"""
    source = options if options is not None else SchedulerOptions()
    return SchedulerOptions(
        enabled=source.enabled,
        rss_minutes=min(1440, max(0, source.rss_minutes)),
        repo_minutes=min(1440, max(0, source.repo_minutes)),
        backup_enabled=source.backup_enabled,
        backup_hour=min(23, max(0, source.backup_hour)),
    )


def is_due(now: datetime, last: datetime | None, minutes: int) -> bool:
    """间隔类任务是否到期：关闭（<=0）永不跑；从未跑过算到期。"""
    if minutes <= 0:
        return False
    if last is None:
        return True
    return now >= last + timedelta(minutes=minutes)


def is_backup_due(now: datetime, last: datetime | None, hour: int) -> bool:
    """每日固定时刻任务是否到期：目标时刻是当天 hour 点。

    未到点不跑；从未跑过或上次早于当天目标时刻则跑（首次启用若已过点会补一次）。
    """
    if hour < 0 or hour > 23:
        return False
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now < target:
        return False
    return last is None or last < target
