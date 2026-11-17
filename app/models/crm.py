"""客户档案、沟通记录、项目、任务、里程碑。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, DecimalAsFloat, TextDateTime


class WhClient(EntityBaseMixin, Base):
    """客户档案：联系人直接内联，一人公司不需要独立的联系人表。"""

    __tablename__ = "wh_client"

    Name: Mapped[str] = mapped_column("Name", Text, nullable=False)
    Contact: Mapped[str | None] = mapped_column("Contact", Text, nullable=True)
    Phone: Mapped[str | None] = mapped_column("Phone", Text, nullable=True)
    Email: Mapped[str | None] = mapped_column("Email", Text, nullable=True)
    Wechat: Mapped[str | None] = mapped_column("Wechat", Text, nullable=True)
    Source: Mapped[str | None] = mapped_column("Source", Text, nullable=True)
    Tags: Mapped[str | None] = mapped_column("Tags", Text, nullable=True)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)
    Archived: Mapped[bool] = mapped_column("Archived", BoolAsInteger, nullable=False, default=False)


class WhCommLog(EntityBaseMixin, Base):
    """沟通留痕：一条时间线记录，挂在客户下。"""

    __tablename__ = "wh_comm_log"

    ClientId: Mapped[str] = mapped_column("ClientId", Text, nullable=False)
    Type: Mapped[str | None] = mapped_column("Type", Text, nullable=True, default="wechat")
    Content: Mapped[str] = mapped_column("Content", Text, nullable=False)
    HappenTime: Mapped[datetime] = mapped_column("HappenTime", TextDateTime(), nullable=False)
    Next: Mapped[str | None] = mapped_column("Next", Text, nullable=True)


class WhProject(EntityBaseMixin, Base):
    """项目台账：合同与报价的关键信息直接内联在 project 上，不另开合同表。"""

    __tablename__ = "wh_project"

    Name: Mapped[str] = mapped_column("Name", Text, nullable=False)
    ClientId: Mapped[str | None] = mapped_column("ClientId", Text, nullable=True)
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="talking")
    Amount: Mapped[Decimal] = mapped_column("Amount", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    SignedDate: Mapped[datetime | None] = mapped_column("SignedDate", TextDateTime(), nullable=True)
    StartDate: Mapped[datetime | None] = mapped_column("StartDate", TextDateTime(), nullable=True)
    EndDate: Mapped[datetime | None] = mapped_column("EndDate", TextDateTime(), nullable=True)
    ExpireDate: Mapped[datetime | None] = mapped_column("ExpireDate", TextDateTime(), nullable=True)
    ContractFile: Mapped[str | None] = mapped_column("ContractFile", Text, nullable=True)
    Terms: Mapped[str | None] = mapped_column("Terms", Text, nullable=True)
    Description: Mapped[str | None] = mapped_column("Description", Text, nullable=True)


class WhTask(EntityBaseMixin, Base):
    """任务：看板四列（待办/进行中/已完成/搁置），可挂到项目。"""

    __tablename__ = "wh_task"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="todo")
    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    DueDate: Mapped[datetime | None] = mapped_column("DueDate", TextDateTime(), nullable=True)
    Priority: Mapped[str | None] = mapped_column("Priority", Text, nullable=True, default="normal")
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)
    DoneTime: Mapped[datetime | None] = mapped_column("DoneTime", TextDateTime(), nullable=True)


class WhMilestone(EntityBaseMixin, Base):
    """项目里程碑：可勾选完成，起止日期供甘特图排布。"""

    __tablename__ = "wh_milestone"

    ProjectId: Mapped[str] = mapped_column("ProjectId", Text, nullable=False)
    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    StartDate: Mapped[datetime | None] = mapped_column("StartDate", TextDateTime(), nullable=True)
    DueDate: Mapped[datetime | None] = mapped_column("DueDate", TextDateTime(), nullable=True)
    Done: Mapped[bool] = mapped_column("Done", BoolAsInteger, nullable=False, default=False)
    DoneTime: Mapped[datetime | None] = mapped_column("DoneTime", TextDateTime(), nullable=True)
    Sort: Mapped[int] = mapped_column("Sort", Integer, nullable=False, default=0)
