"""实体基类：Known 的 EntityBase 在每张实体表上带的 9 个公共列。"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.types import TextDateTime


def new_id() -> str:
    """生成 36 位主键（与 Known 生成的 GUID 字符串同长）。"""
    return str(uuid.uuid4())


class EntityBaseMixin:
    """公共列。列名保持 PascalCase，与 C# 版及旧库逐字一致。"""

    Id: Mapped[str] = mapped_column("Id", Text, primary_key=True, default=new_id)
    CreateBy: Mapped[str] = mapped_column("CreateBy", Text, nullable=False)
    CreateTime: Mapped[str] = mapped_column("CreateTime", TextDateTime(), nullable=False)
    ModifyBy: Mapped[str | None] = mapped_column("ModifyBy", Text, nullable=True)
    ModifyTime: Mapped[str | None] = mapped_column("ModifyTime", TextDateTime(), nullable=True)
    Version: Mapped[int] = mapped_column("Version", Integer, nullable=False, default=1)
    Extension: Mapped[str | None] = mapped_column("Extension", Text, nullable=True)
    AppId: Mapped[str | None] = mapped_column("AppId", Text, nullable=True)
    CompNo: Mapped[str | None] = mapped_column("CompNo", Text, nullable=True)


__all__ = ["Base", "EntityBaseMixin"]
