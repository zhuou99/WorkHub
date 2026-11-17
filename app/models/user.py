"""账号表：口令只存 PBKDF2 散列，角色决定可见菜单与写权限。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, TextDateTime


class WhUser(EntityBaseMixin, Base):
    __tablename__ = "wh_user"

    UserName: Mapped[str] = mapped_column("UserName", Text, nullable=False)
    DisplayName: Mapped[str | None] = mapped_column("DisplayName", Text, nullable=True)
    PasswordHash: Mapped[str | None] = mapped_column("PasswordHash", Text, nullable=True)
    Role: Mapped[str | None] = mapped_column("Role", Text, nullable=True)
    Enabled: Mapped[bool] = mapped_column("Enabled", BoolAsInteger, nullable=False, default=True)
    SetTime: Mapped[datetime] = mapped_column("SetTime", TextDateTime(), nullable=False)
    LastLoginTime: Mapped[datetime | None] = mapped_column("LastLoginTime", TextDateTime(), nullable=True)
