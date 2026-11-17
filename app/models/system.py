"""审计日志、运行错误、工具历史。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, TextDateTime


class WhAuditLog(EntityBaseMixin, Base):
    """关键动作留痕：登录、访问拒绝、备份恢复、调度任务、设置变更。"""

    __tablename__ = "wh_audit"

    Time: Mapped[datetime] = mapped_column("Time", TextDateTime(), nullable=False)
    Kind: Mapped[str | None] = mapped_column("Kind", Text, nullable=True)
    Action: Mapped[str | None] = mapped_column("Action", Text, nullable=True)
    UserName: Mapped[str | None] = mapped_column("UserName", Text, nullable=True)
    Ip: Mapped[str | None] = mapped_column("Ip", Text, nullable=True)
    Success: Mapped[bool] = mapped_column("Success", BoolAsInteger, nullable=False, default=True)
    Detail: Mapped[str | None] = mapped_column("Detail", Text, nullable=True)


class WhError(EntityBaseMixin, Base):
    """运行错误留痕：出问题时不必只翻日志文件，最近若干条可直接查看。"""

    __tablename__ = "wh_error"

    Time: Mapped[datetime] = mapped_column("Time", TextDateTime(), nullable=False)
    Level: Mapped[str | None] = mapped_column("Level", Text, nullable=True)
    Source: Mapped[str | None] = mapped_column("Source", Text, nullable=True)
    Message: Mapped[str | None] = mapped_column("Message", Text, nullable=True)
    Detail: Mapped[str | None] = mapped_column("Detail", Text, nullable=True)
    Path: Mapped[str | None] = mapped_column("Path", Text, nullable=True)
    UserName: Mapped[str | None] = mapped_column("UserName", Text, nullable=True)


class WhToolPref(EntityBaseMixin, Base):
    """工具输入历史：每工具只留最近 30 条。"""

    __tablename__ = "wh_tool_pref"

    ToolId: Mapped[str] = mapped_column("ToolId", Text, nullable=False)
    ToolName: Mapped[str | None] = mapped_column("ToolName", Text, nullable=True)
    Input: Mapped[str | None] = mapped_column("Input", Text, nullable=True)
