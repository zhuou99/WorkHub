"""工具台与审计日志的 schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseIn, BaseOut, EntityOut

__all__ = [
    "ToolOption",
    "ToolInfo",
    "ToolRunRequest",
    "ToolRunResult",
    "ToolRecordRequest",
    "ToolPrefOut",
    "AuditLogOut",
    "ErrorOut",
    "AuditWriteRequest",
]


class ToolOption(BaseOut):
    """工具的下拉项。"""

    Label: str = ""
    Value: str = ""


class ToolInfo(BaseOut):
    """工具定义。"""

    Id: str = ""
    Name: str = ""
    Category: str = ""
    Icon: str = ""
    Description: str = ""
    Kind: str = "io"
    Options: list[ToolOption] = []
    Params: list[str] = []


class ToolRunRequest(BaseIn):
    """执行工具的请求。"""

    Input: str = ""
    Option: str = ""
    Params: dict[str, Any] = {}


class ToolRunResult(BaseOut):
    """执行结果：文本输出 + 结构化数据。"""

    Output: str = ""
    Data: dict[str, Any] | None = None


class ToolRecordRequest(BaseIn):
    ToolName: str | None = Field(default=None, max_length=50)
    Input: str = Field(default="", max_length=4000)


class ToolPrefOut(EntityOut):
    ToolId: str = ""
    ToolName: str | None = None
    Input: str | None = None


class AuditLogOut(EntityOut):
    Time: datetime | None = None
    Kind: str | None = None
    Action: str | None = None
    UserName: str | None = None
    Ip: str | None = None
    Success: bool = True
    Detail: str | None = None


class ErrorOut(EntityOut):
    Time: datetime | None = None
    Level: str | None = None
    Source: str | None = None
    Message: str | None = None
    Detail: str | None = None
    Path: str | None = None
    UserName: str | None = None


class AuditWriteRequest(BaseIn):
    Kind: str = Field(..., max_length=20)
    Action: str = Field(..., max_length=50)
    Success: bool = True
    Detail: str | None = Field(default=None, max_length=500)
