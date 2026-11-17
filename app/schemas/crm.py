"""客户、项目、任务、里程碑的 schema。

字段清单以 C# 的 upsert lambda 为准——那才是「保存允许改哪些字段」的权威列表。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import BaseIn, EntityOut, Money

__all__ = [
    "ClientIn",
    "ClientOut",
    "CommLogIn",
    "CommLogOut",
    "ProjectIn",
    "ProjectOut",
    "MilestoneIn",
    "MilestoneOut",
    "TaskIn",
    "TaskOut",
]


class ClientIn(BaseIn):
    Name: str = Field(..., max_length=100)
    Contact: str | None = Field(default=None, max_length=60)
    Phone: str | None = Field(default=None, max_length=30)
    Email: str | None = Field(default=None, max_length=80)
    Wechat: str | None = Field(default=None, max_length=50)
    Source: str | None = Field(default=None, max_length=20)
    Tags: str | None = Field(default=None, max_length=200)
    Note: str | None = Field(default=None, max_length=1000)
    Archived: bool = False


class ClientOut(EntityOut):
    Name: str = ""
    Contact: str | None = None
    Phone: str | None = None
    Email: str | None = None
    Wechat: str | None = None
    Source: str | None = None
    Tags: str | None = None
    Note: str | None = None
    Archived: bool = False


class CommLogIn(BaseIn):
    ClientId: str = Field(..., max_length=36)
    Type: str | None = Field(default="wechat", max_length=20)
    Content: str = Field(..., max_length=1000)
    HappenTime: datetime | None = None
    Next: str | None = Field(default=None, max_length=500)


class CommLogOut(EntityOut):
    ClientId: str = ""
    Type: str | None = None
    Content: str = ""
    HappenTime: datetime | None = None
    Next: str | None = None


class ProjectIn(BaseIn):
    Name: str = Field(..., max_length=200)
    ClientId: str | None = Field(default=None, max_length=36)
    Status: str | None = Field(default="talking", max_length=20)
    Amount: Money = Decimal("0")
    SignedDate: datetime | None = None
    StartDate: datetime | None = None
    EndDate: datetime | None = None
    ExpireDate: datetime | None = None
    ContractFile: str | None = Field(default=None, max_length=300)
    Terms: str | None = Field(default=None, max_length=1000)
    Description: str | None = None


class ProjectOut(EntityOut):
    Name: str = ""
    ClientId: str | None = None
    Status: str | None = None
    Amount: Money = Decimal("0")
    SignedDate: datetime | None = None
    StartDate: datetime | None = None
    EndDate: datetime | None = None
    ExpireDate: datetime | None = None
    ContractFile: str | None = None
    Terms: str | None = None
    Description: str | None = None


class MilestoneIn(BaseIn):
    ProjectId: str = Field(..., max_length=36)
    Title: str = Field(..., max_length=200)
    StartDate: datetime | None = None
    DueDate: datetime | None = None
    Done: bool = False
    DoneTime: datetime | None = None
    Sort: int = 0


class MilestoneOut(EntityOut):
    ProjectId: str = ""
    Title: str = ""
    StartDate: datetime | None = None
    DueDate: datetime | None = None
    Done: bool = False
    DoneTime: datetime | None = None
    Sort: int = 0


class TaskIn(BaseIn):
    Title: str = Field(..., max_length=300)
    Status: str | None = Field(default="todo", max_length=20)
    ProjectId: str | None = Field(default=None, max_length=36)
    DueDate: datetime | None = None
    Priority: str | None = Field(default="normal", max_length=10)
    Note: str | None = Field(default=None, max_length=1000)
    DoneTime: datetime | None = None


class TaskOut(EntityOut):
    Title: str = ""
    Status: str | None = None
    ProjectId: str | None = None
    DueDate: datetime | None = None
    Priority: str | None = None
    Note: str | None = None
    DoneTime: datetime | None = None
