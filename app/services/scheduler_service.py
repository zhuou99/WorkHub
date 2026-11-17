"""定时同步与自动备份：对应 C# 的 WorkHub/Services/SchedulerService.cs。

后台与手动共用同一把进程内锁，避免 RSS/GitHub 同步或备份重叠执行。
设置与状态都存 SysConfig（JSON），随数据库一起备份。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime

from app.common.scheduler_options import SchedulerOptions, SchedulerState, is_backup_due, is_due, normalize
from app.services.audit_service import AuditService
from app.services.config_service import ConfigStore

__all__ = ["SchedulerService", "OPTIONS_KEY", "STATE_KEY"]

OPTIONS_KEY = "workhub.scheduler.options"
STATE_KEY = "workhub.scheduler.state"

_gate = threading.Lock()


class SchedulerService:
    def __init__(self, config: ConfigStore, audit: AuditService, rss, repos, backup):
        self._config = config
        self._audit = audit
        self._rss = rss
        self._repos = repos
        self._backup = backup

    def get_options(self) -> SchedulerOptions:
        raw = self._config.get(OPTIONS_KEY)
        if not raw:
            return SchedulerOptions()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return SchedulerOptions()
        return normalize(SchedulerOptions(
            enabled=bool(_pick(data, "Enabled", "enabled", False)),
            rss_minutes=int(_pick(data, "RssMinutes", "rssMinutes", 30)),
            repo_minutes=int(_pick(data, "RepoMinutes", "repoMinutes", 60)),
            backup_enabled=bool(_pick(data, "BackupEnabled", "backupEnabled", False)),
            backup_hour=int(_pick(data, "BackupHour", "backupHour", 3)),
        ))

    def save_options(self, options: SchedulerOptions) -> str:
        normalized = normalize(options)
        self._config.set_json(OPTIONS_KEY, _to_dict(normalized))
        self._audit.write(
            "settings", "scheduler-save", True,
            f"启用={normalized.enabled}；RSS={normalized.rss_minutes} 分；仓库={normalized.repo_minutes} 分；"
            f"备份={normalized.backup_enabled}@{normalized.backup_hour} 点",
        )
        return "定时任务设置已保存。"

    def get_state(self) -> SchedulerState:
        raw = self._config.get(STATE_KEY)
        if not raw:
            return SchedulerState()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return SchedulerState()
        return SchedulerState(
            last_rss=_parse_dt(_pick(data, "LastRss", "lastRss", None)),
            last_repo=_parse_dt(_pick(data, "LastRepo", "lastRepo", None)),
            last_backup=_parse_dt(_pick(data, "LastBackup", "lastBackup", None)),
            last_run_at=_parse_dt(_pick(data, "LastRunAt", "lastRunAt", None)),
            last_message=_pick(data, "LastMessage", "lastMessage", None),
        )

    def run(self, job: str) -> str:
        job = (job or "").strip().lower()
        if job not in ("rss", "repo", "backup"):
            raise ValueError("未知的定时任务。")

        if not _gate.acquire(blocking=False):
            raise TimeoutError("已有同步任务在跑，请稍后再试。")
        try:
            state = self.get_state()
            ok, message = self._execute(job, state)
            state.last_run_at = datetime.now()
            self._config.set_json(STATE_KEY, _state_to_dict(state))
            if not ok:
                raise RuntimeError(message)
            return message
        finally:
            _gate.release()

    def run_due(self) -> str:
        options = self.get_options()
        if not options.enabled:
            return "定时任务未启用。"

        if not _gate.acquire(blocking=False):
            raise TimeoutError("已有同步任务在跑，本轮跳过。")
        try:
            state = self.get_state()
            now = datetime.now()
            ran: list[str] = []
            failed = 0

            if is_due(now, state.last_rss, options.rss_minutes):
                ok, _ = self._execute("rss", state)
                ran.append("RSS 同步")
                if not ok:
                    failed += 1
            if is_due(now, state.last_repo, options.repo_minutes):
                ok, _ = self._execute("repo", state)
                ran.append("GitHub 同步")
                if not ok:
                    failed += 1
            if options.backup_enabled and is_backup_due(now, state.last_backup, options.backup_hour):
                ok, _ = self._execute("backup", state)
                ran.append("自动备份")
                if not ok:
                    failed += 1

            if not ran:
                return "暂无到期任务。"

            state.last_run_at = now
            self._config.set_json(STATE_KEY, _state_to_dict(state))
            text = f"本轮执行 {'、'.join(ran)}" + (f"，失败 {failed} 项" if failed > 0 else "")
            if failed > 0:
                raise RuntimeError(text)
            return text
        finally:
            _gate.release()

    def _execute(self, job: str, state: SchedulerState) -> tuple[bool, str]:
        now = datetime.now()
        try:
            if job == "rss":
                message = self._rss.sync_all()
            elif job == "repo":
                message = self._repos.sync_all()
            else:
                message = self._backup.run()
            ok = True
        except Exception as exc:
            ok = False
            message = str(exc)

        label = {"rss": "RSS 同步", "repo": "GitHub 同步", "backup": "自动备份"}[job]
        text = f"{label} {now:%m-%d %H:%M}：{'成功' if ok else '失败'}" + (f" {message}" if message else "。")

        if job == "rss":
            state.last_rss = now
        elif job == "repo":
            state.last_repo = now
        else:
            state.last_backup = now
        state.last_message = text

        self._audit.write("scheduler", f"scheduler-{job}", ok, text)
        return ok, text


def _pick(data: dict, *names, default=None):
    for name in names:
        if name in data:
            return data[name]
    lowered = {str(key).lower(): value for key, value in data.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return default


def _to_dict(options: SchedulerOptions) -> dict:
    return {
        "Enabled": options.enabled,
        "RssMinutes": options.rss_minutes,
        "RepoMinutes": options.repo_minutes,
        "BackupEnabled": options.backup_enabled,
        "BackupHour": options.backup_hour,
    }


def _state_to_dict(state: SchedulerState) -> dict:
    return {
        "LastRss": state.last_rss.isoformat(sep=" ", timespec="microseconds") if state.last_rss else None,
        "LastRepo": state.last_repo.isoformat(sep=" ", timespec="microseconds") if state.last_repo else None,
        "LastBackup": state.last_backup.isoformat(sep=" ", timespec="microseconds") if state.last_backup else None,
        "LastRunAt": state.last_run_at.isoformat(sep=" ", timespec="microseconds") if state.last_run_at else None,
        "LastMessage": state.last_message,
    }


def _parse_dt(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
