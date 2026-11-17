"""设置路由：账号资料与改口令。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_audit, get_db, get_users, require_user
from app.schemas.auth import AccountInfo, ChangePasswordRequest, UserInfo
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/settings", tags=["设置"])


def _service(
    db: Session = Depends(get_db),
    users: UserService = Depends(get_users),
    audit: AuditService = Depends(get_audit),
) -> SettingsService:
    return SettingsService(db, users, audit)


@router.get("/account", response_model=Result[AccountInfo], summary="当前账号资料")
def account(service: SettingsService = Depends(_service), me: UserInfo = Depends(require_user)):
    return Result(data=service.account(me.UserName))


@router.post("/password", response_model=Result[None], summary="修改登录口令")
def change_password(
    payload: ChangePasswordRequest,
    service: SettingsService = Depends(_service),
    me: UserInfo = Depends(require_user),
):
    return Result(message=service.change_password(me.UserName, payload.OldPassword, payload.NewPassword))
