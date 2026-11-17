"""审计日志与运行错误路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_audit, get_db, require_owner, require_user
from app.schemas.auth import UserInfo
from app.schemas.tool import AuditLogOut, ErrorOut
from app.services.audit_service import AuditService
from app.services.error_log_service import ErrorLogService

router = APIRouter(prefix="/api", tags=["日志"])


def _errors(db: Session = Depends(get_db)) -> ErrorLogService:
    return ErrorLogService(db)


@router.get("/audit", response_model=Result[list[AuditLogOut]], summary="审计日志")
def audit_logs(
    take: int = Query(50, ge=1, le=500),
    audit: AuditService = Depends(get_audit),
    _: UserInfo = Depends(require_user),
):
    return Result(
        data=[
            AuditLogOut(
                Id=item.Id,
                CreateBy=item.CreateBy or "",
                CreateTime=item.CreateTime,
                ModifyBy=item.ModifyBy,
                ModifyTime=item.ModifyTime,
                Version=item.Version or 1,
                Time=item.Time,
                Kind=item.Kind,
                Action=item.Action,
                UserName=item.UserName,
                Ip=item.Ip,
                Success=bool(item.Success),
                Detail=item.Detail,
            )
            for item in audit.recent(take)
        ]
    )


@router.delete("/audit", response_model=Result[int], summary="清空审计日志")
def clear_audit(audit: AuditService = Depends(get_audit), _: UserInfo = Depends(require_owner)):
    return Result(data=audit.clear(), message="已清空审计日志。")


@router.get("/errors", response_model=Result[list[ErrorOut]], summary="运行错误")
def error_logs(
    take: int = Query(50, ge=1, le=200),
    service: ErrorLogService = Depends(_errors),
    _: UserInfo = Depends(require_user),
):
    return Result(
        data=[
            ErrorOut(
                Id=item.Id,
                CreateBy=item.CreateBy or "",
                CreateTime=item.CreateTime,
                ModifyBy=item.ModifyBy,
                ModifyTime=item.ModifyTime,
                Version=item.Version or 1,
                Time=item.Time,
                Level=item.Level,
                Source=item.Source,
                Message=item.Message,
                Detail=item.Detail,
                Path=item.Path,
                UserName=item.UserName,
            )
            for item in service.recent(take)
        ]
    )


@router.delete("/errors", response_model=Result[int], summary="清空运行错误")
def clear_errors(service: ErrorLogService = Depends(_errors), _: UserInfo = Depends(require_owner)):
    return Result(data=service.clear(), message="已清空运行错误。")
