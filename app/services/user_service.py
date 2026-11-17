"""账号管理：对应 C# 的 WorkHub/Services/UserService.cs。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.common.hasher import hash_password, verify_password
from app.common.permission_policy import (
    EDITOR_ROLE,
    OWNER_ROLE,
    VIEWER_ROLE,
    is_owner_role,
)
from app.common.user_rules import can_remove, is_role, validate_password, validate_user_name
from app.models.user import WhUser
from app.services.audit_service import AuditService
from app.services.crud import LOCAL, now

__all__ = ["UserService"]


class UserService:
    def __init__(self, session: Session, audit: AuditService):
        self._session = session
        self._audit = audit

    # ---------- 查询 ----------

    def all(self) -> list[WhUser]:
        return list(self._session.execute(select(WhUser)).scalars().all())

    def find(self, user_name: str | None) -> WhUser | None:
        """按账号查找（大小写不敏感）。"""
        name = (user_name or "").strip()
        for user in self.all():
            if (user.UserName or "").lower() == name.lower():
                return user
        return None

    def find_by_id(self, user_id: str) -> WhUser | None:
        for user in self.all():
            if user.Id == user_id:
                return user
        return None

    def authenticate(self, user_name: str, password: str) -> WhUser | None:
        """校验口令；账号不存在或已禁用返回 None。"""
        user = self.find(user_name)
        if user is None or not user.Enabled:
            return None
        return user if verify_password(password, user.PasswordHash) else None

    def any_owner(self) -> bool:
        return any(user.Enabled and is_owner_role(user.Role) for user in self.all())

    def enabled_owners(self) -> int:
        return sum(1 for user in self.all() if user.Enabled and is_owner_role(user.Role))

    def touch_login(self, user_id: str, moment: datetime | None = None) -> None:
        """登录成功后刷新最近登录时间。"""
        user = self.find_by_id(user_id)
        if user is None:
            return
        user.LastLoginTime = moment or now()
        self._session.add(user)
        self._session.commit()

    # ---------- 变更 ----------

    def create(self, user_name: str, display_name: str | None, password: str, role: str) -> WhUser:
        """新建账号。校验不过直接抛 WorkHubError（HTTP 层转 400）。"""
        name = (user_name or "").strip()
        error = validate_user_name(name)
        if error:
            raise WorkHubError(error)
        error = validate_password(password)
        if error:
            raise WorkHubError(error)
        if not is_role(role):
            raise WorkHubError("角色只能是 Owner / Editor / Viewer。")
        if self.find(name) is not None:
            raise WorkHubError(f"账号 {name} 已存在。")

        user = WhUser(
            UserName=name,
            DisplayName=name if not (display_name or "").strip() else display_name.strip(),
            PasswordHash=hash_password(password),
            Role=normalize_role(role),
            Enabled=True,
            SetTime=now(),
            CreateBy=LOCAL,
            CreateTime=now(),
        )
        self._session.add(user)
        self._session.commit()
        self._audit.write("settings", "user-create", True, f"新增账号 {user.UserName}（{user.Role}）", user.UserName)
        return user

    def update(self, user_id: str, display_name: str | None, role: str, enabled: bool) -> WhUser:
        """改账号：显示名、角色、启用状态。"""
        user = self.find_by_id(user_id)
        if user is None:
            raise WorkHubError("这个账号已经不在了。")
        if not is_role(role):
            raise WorkHubError("角色只能是 Owner / Editor / Viewer。")
        if not enabled and not can_remove(user.Enabled, user.Role, self.enabled_owners()):
            raise WorkHubError("这是最后一个启用中的 Owner，不能禁用。")

        user.DisplayName = user.UserName if not (display_name or "").strip() else display_name.strip()
        user.Role = normalize_role(role)
        user.Enabled = enabled
        self._session.add(user)
        self._session.commit()
        self._audit.write(
            "settings", "user-update", True, f"账号 {user.UserName}：角色 {user.Role}，启用 {user.Enabled}", user.UserName
        )
        return user

    def reset_password(self, user_id: str, password: str) -> WhUser:
        """重置口令。"""
        error = validate_password(password)
        if error:
            raise WorkHubError(error)
        user = self.find_by_id(user_id)
        if user is None:
            raise WorkHubError("这个账号已经不在了。")
        user.PasswordHash = hash_password(password)
        user.SetTime = now()
        self._session.add(user)
        self._session.commit()
        self._audit.write("settings", "user-reset", True, f"重置账号 {user.UserName} 的口令", user.UserName)
        return user

    def delete(self, user_id: str, current_user_name: str | None = None) -> str:
        """删除账号。返回给用户看的一句话。"""
        user = self.find_by_id(user_id)
        if user is None:
            raise WorkHubError("这个账号已经不在了。")
        if current_user_name and (user.UserName or "").lower() == current_user_name.lower():
            raise WorkHubError("不能删除当前登录的账号。")
        if not can_remove(user.Enabled, user.Role, self.enabled_owners()):
            raise WorkHubError("这是最后一个启用中的 Owner，不能删除。")

        self._session.delete(user)
        self._session.commit()
        self._audit.write("settings", "user-delete", True, f"删除账号 {user.UserName}", user.UserName)
        return f"已删除账号 {user.UserName}。"


def normalize_role(role: str | None) -> str:
    """角色归一：不是 Owner 也不是 Viewer 的一律当 Editor。"""
    if is_owner_role(role):
        return OWNER_ROLE
    if role is not None and role.strip().lower() == VIEWER_ROLE.lower():
        return VIEWER_ROLE
    return EDITOR_ROLE
