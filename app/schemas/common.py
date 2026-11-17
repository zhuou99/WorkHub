"""共用 schema 基类与类型。

线格式走 camelCase（与 ASP.NET Core 默认一致），数据库列名保持 PascalCase。
Python 字段名跟 ORM 属性同名，from_attributes 直接就能读。
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, computed_field

__all__ = [
    "BaseOut",
    "BaseIn",
    "EntityOut",
    "Money",
    "LinkGroup",
    "DeleteImpact",
    "SelectOption",
    "to_camel_case",
]

#: 金额：内部是 Decimal，线上是 JSON 数字（与 C# 的 decimal 序列化一致）。
#: 尾零在线上会丢（56.60 → 56.6），但计算过程一步都不丢精度。
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]

#: PascalCase → camelCase 的分词边界：userName / URLValue / IsOverdue
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def to_camel_case(name: str) -> str:
    """PascalCase 转 camelCase。

    Pydantic 自带的 to_camel 是给 snake_case 输入用的，遇到 PascalCase 会整段小写
    （"RemainingSeconds" → "remainingseconds"），所以这里自己写。
    """
    if not name:
        return name
    parts = _CAMEL_BOUNDARY.sub("_", name).split("_")
    return parts[0].lower() + "".join(part[:1].upper() + part[1:] for part in parts[1:])


class BaseOut(BaseModel):
    """读模型基类。"""

    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel_case, populate_by_name=True
    )


class BaseIn(BaseModel):
    """写入模型基类。字段名与 ORM 属性同名，便于 service 直接拷贝。"""

    model_config = ConfigDict(
        alias_generator=to_camel_case, populate_by_name=True, str_strip_whitespace=False
    )


class EntityOut(BaseOut):
    """实体读模型基类：带上 Known 在每张实体表上都有的 9 个公共列。"""

    Id: str = ""
    CreateBy: str = ""
    CreateTime: datetime | None = None
    ModifyBy: str | None = None
    ModifyTime: datetime | None = None
    Version: int = 1
    Extension: str | None = None
    AppId: str | None = None
    CompNo: str | None = None


class LinkGroup(BaseModel):
    """删除影响预览里的一组引用。"""

    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    Label: str = ""
    Count: int = 0
    #: cascade 表示跟着一起删，detach 表示可以解绑保留。
    Mode: str = "detach"


class DeleteImpact(BaseModel):
    """删除客户 / 项目前的级联预览：谁挂在它身上、各自会被怎么处理。"""

    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    Name: str = ""
    Groups: list[LinkGroup] = []

    @computed_field
    @property
    def Total(self) -> int:
        """引用总数，0 表示随便删、不留尾巴。"""
        return sum(group.Count for group in self.Groups)

    @computed_field
    @property
    def HasRefs(self) -> bool:
        return self.Total > 0


class SelectOption(BaseModel):
    """下拉项：Value 是存库的值，Text 是给人看的文案。"""

    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    Value: str
    Text: str


class TimeRange(BaseModel):
    """时间段。"""

    From: datetime | None = None
    To: datetime | None = None
