"""定时任务路由。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.common.scheduler_options import SchedulerOptions
from app.core.result import Result
from app.deps import (
    get_audit,
    get_config_store,
    get_content_root,
    get_database_backup,
    get_db,
    get_protector,
    get_storage,
    require_owner,
    require_user,
)
from app.platforms.database_backup import DatabaseBackup
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.services.audit_service import AuditService
from app.services.backup_service import BackupService
from app.services.config_service import ConfigStore
from app.services.repo_service import RepoService
from app.services.rss_service import RssService
from app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api/scheduler", tags=["定时任务"])


class SchedulerOptionsIn(BaseIn):
    Enabled: bool = False
    RssMinutes: int = 30
    RepoMinutes: int = 60
    BackupEnabled: bool = False
    BackupHour: int = 3


class RunRequest(BaseIn):
    Job: str = Field(..., max_length=20)


class SchedulerStateOut(BaseIn):
    LastRss: datetime | None = None
    LastRepo: datetime | None = None
    LastBackup: datetime | None = None
    LastRunAt: datetime | None = None
    LastMessage: str | None = None


def _service(
    db: Session = Depends(get_db),
    config: ConfigStore = Depends(get_config_store),
    audit: AuditService = Depends(get_audit),
    storage=Depends(get_storage),
    protector=Depends(get_protector),
    content_root=Depends(get_content_root),
    database: DatabaseBackup = Depends(get_database_backup),
) -> SchedulerService:
    rss = RssService(db, storage)
    repos = RepoService(db, config, protector)
    backup = BackupService(db, config, audit, storage, content_root, database)
    return SchedulerService(config, audit, rss, repos, backup)


def _options_out(options: SchedulerOptions) -> dict:
    return {
        "enabled": options.enabled,
        "rssMinutes": options.rss_minutes,
        "repoMinutes": options.repo_minutes,
        "backupEnabled": options.backup_enabled,
        "backupHour": options.backup_hour,
    }


@router.get("/options", response_model=Result[dict], summary="定时任务设置")
def get_options(service: SchedulerService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=_options_out(service.get_options()))


@router.post("/options", response_model=Result[None], summary="保存定时任务设置")
def save_options(payload: SchedulerOptionsIn, service: SchedulerService = Depends(_service), _: UserInfo = Depends(require_owner)):
    options = SchedulerOptions(
        enabled=payload.Enabled,
        rss_minutes=payload.RssMinutes,
        repo_minutes=payload.RepoMinutes,
        backup_enabled=payload.BackupEnabled,
        backup_hour=payload.BackupHour,
    )
    return Result(message=service.save_options(options))


@router.get("/state", response_model=Result[SchedulerStateOut], summary="定时任务状态")
def get_state(service: SchedulerService = Depends(_service), _: UserInfo = Depends(require_user)):
    state = service.get_state()
    return Result(data=SchedulerStateOut(
        LastRss=state.last_rss, LastRepo=state.last_repo, LastBackup=state.last_backup,
        LastRunAt=state.last_run_at, LastMessage=state.last_message,
    ))


@router.post("/run", response_model=Result[None], summary="手动触发任务")
def run(payload: RunRequest, service: SchedulerService = Depends(_service), _: UserInfo = Depends(require_owner)):
    try:
        return Result(message=service.run(payload.Job))
    except (ValueError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run-due", response_model=Result[None], summary="运行到期任务")
def run_due(service: SchedulerService = Depends(_service), _: UserInfo = Depends(require_owner)):
    try:
        return Result(message=service.run_due())
    except (TimeoutError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
