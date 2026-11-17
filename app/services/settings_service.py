"""当前账号资料与改口令：对应 C# 的 WorkHub/Services/LocalSettingsService.cs。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.common.hasher import verify_password
from app.schemas.auth import AccountInfo
from app.services.audit_service import AuditService
from app.services.auth_service import DEFAULT_PASSWORD
from app.services.user_service import UserService

__all__ = ["SettingsService"]


class SettingsService:
    def __init__(self, session: Session, users: UserService, audit: AuditService):
        self._session = session
        self._users = users
        self._audit = audit

    def account(self, user_name: str) -> AccountInfo:
        """当前登录账号资料（不带口令散列）。"""
        user = self._users.find(user_name)
        if user is None:
            return None
        return AccountInfo(
            UserName=user.UserName or "",
            DisplayName=user.DisplayName,
            SetTime=user.SetTime,
            DefaultPassword=verify_password(DEFAULT_PASSWORD, user.PasswordHash),
        )

    def change_password(self, user_name: str, old_password: str, new_password: str) -> str:
        """校验旧口令后改为新口令。"""
        if not old_password or not new_password:
            raise WorkHubError("旧口令与新口令均不能为空。")
        if len(new_password) < 6:
            raise WorkHubError("新口令至少 6 位。")

        user = self._users.find(user_name)
        if user is None:
            raise WorkHubError("账号已不存在，请重新登录。")

        if not verify_password(old_password, user.PasswordHash):
            self._audit.write("settings", "password-change", False, "旧口令不正确", user.UserName)
            raise WorkHubError("旧口令不正确。")

        self._users.reset_password(user.Id, new_password)
        self._audit.write("settings", "password-change", True, "登录口令已更新", user.UserName)
        return "口令已更新。"
