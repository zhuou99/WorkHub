"""SysConfig：Known 的 KV 配置表，AppId 固定 "WorkHub"。"""

from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SysConfig(Base):
    __tablename__ = "SysConfig"

    AppId: Mapped[str] = mapped_column("AppId", Text, primary_key=True)
    ConfigKey: Mapped[str] = mapped_column("ConfigKey", Text, primary_key=True)
    ConfigValue: Mapped[str | None] = mapped_column("ConfigValue", Text, nullable=True)
