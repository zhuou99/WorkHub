"""认证与账号相关的 schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseIn, BaseOut

__all__ = [
    "LoginRequest",
    "UserInfo",
    "UserView",
    "AccountInfo",
    "AuthGuardState",
    "ChangePasswordRequest",
    "UserCreate",
    "UserUpdate",
    "UserResetPassword",
]


class LoginRequest(BaseIn):
    UserName: str = Field(..., max_length=30)
    Password: str = Field(..., max_length=200)


class UserInfo(BaseOut):
    """当前会话的用户。Token 字段保留是为了跟原来的契约形状一致。"""

    Id: str = ""
    UserName: str = ""
    Name: str = ""
    Role: str | None = None
    AppId: str = ""
    Token: str = ""
    Enabled: bool = True
    LastLoginTime: datetime | None = None


class UserView(BaseOut):
    """账号列表视图：不暴露口令散列。"""

    Id: str = ""
    UserName: str = ""
    DisplayName: str | None = None
    Role: str | None = None
    Enabled: bool = True
    LastLoginTime: datetime | None = None


class AccountInfo(BaseOut):
    """设置页展示的账号资料：不带口令散列。"""

    UserName: str = ""
    DisplayName: str | None = None
    SetTime: datetime | None = None
    DefaultPassword: bool = False


class AuthGuardState(BaseOut):
    """登录页要看到的认证状态：是否锁定、还剩几次、是否仍是出厂口令。"""

    Locked: bool = False
    RemainingSeconds: int = 0
    Failures: int = 0
    RemainingTries: int = 0
    DefaultPassword: bool = False


class ChangePasswordRequest(BaseIn):
    OldPassword: str = Field(..., max_length=200)
    NewPassword: str = Field(..., max_length=200)


class UserCreate(BaseIn):
    UserName: str = Field(..., max_length=30)
    DisplayName: str | None = Field(default=None, max_length=50)
    Password: str = Field(..., max_length=200)
    Role: str = Field(..., max_length=20)


class UserUpdate(BaseIn):
    DisplayName: str | None = Field(default=None, max_length=50)
    Role: str = Field(..., max_length=20)
    Enabled: bool = True


class UserResetPassword(BaseIn):
    Password: str = Field(..., max_length=200)
