"""备份与恢复路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_audit, get_config_store, get_content_root, get_database_backup, get_db, get_storage, require_owner, require_user
from app.schemas.auth import UserInfo
from app.schemas.backup import BackupInfo, BackupOptions
from app.schemas.common import BaseIn
from app.services.audit_service import AuditService
from app.services.backup_service import BackupService
from app.services.config_service import ConfigStore

router = APIRouter(prefix="/api/backup", tags=["备份"])


class RestoreRequest(BaseIn):
    Name: str = Field(..., max_length=100)


def _service(
    db: Session = Depends(get_db),
    config: ConfigStore = Depends(get_config_store),
    audit: AuditService = Depends(get_audit),
    storage=Depends(get_storage),
    content_root: Path = Depends(get_content_root),
    database=Depends(get_database_backup),
) -> BackupService:
    return BackupService(db, config, audit, storage, content_root, database)


@router.post("/run", response_model=Result[None], summary="一键备份")
def run(service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    try:
        return Result(message=service.run())
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/restore", response_model=Result[None], summary="从备份恢复")
def restore(payload: RestoreRequest, service: BackupService = Depends(_service), _: UserInfo = Depends(require_owner)):
    try:
        return Result(message=service.restore(payload.Name))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list", response_model=Result[list[BackupInfo]], summary="备份列表")
def list_backups(service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.list())


@router.delete("/{name}", response_model=Result[None], summary="删除备份")
def delete_backup(name: str, service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    try:
        return Result(message=service.delete(name))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/folder", response_model=Result[str], summary="备份目录")
def folder(service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.get_folder())


@router.get("/options", response_model=Result[BackupOptions], summary="备份设置")
def get_options(service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.get_options())


@router.post("/options", response_model=Result[None], summary="保存备份设置")
def save_options(payload: BackupOptions, service: BackupService = Depends(_service), _: UserInfo = Depends(require_user)):
    try:
        return Result(message=service.save_options(payload))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
