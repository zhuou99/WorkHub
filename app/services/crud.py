"""通用读写助手：对应 C# 的 WorkHub/Common/Crud.cs（CrudDb 扩展方法）。

C# 那边用「先读回、再逐字段拷贝」是因为 Known 的乐观锁要求 UPDATE 带 Version，
浏览器 JSON 往返过来的对象没有原始快照，直接更新会静默失败。
SQLAlchemy 直接改已加载的对象就没这个问题，但字段白名单的口径要照搬：
**保存只允许改 upsert 列表里的字段**，其余列（Id / CreateBy / Version…）不碰。
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import TypeVar

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

__all__ = ["LOCAL", "new_id", "now", "upsert", "assign", "unbind", "has_table", "delete_where"]

#: 写入 CreateBy / ModifyBy 的固定值
LOCAL = "local"

T = TypeVar("T")


def new_id() -> str:
    """生成 36 位主键（与 Known 生成的 GUID 字符串同长）。"""
    return str(uuid.uuid4())


def now() -> datetime:
    """当前本地时间（C# 那边用的是 DateTime.Now）。"""
    return datetime.now()


def assign(target, source, fields: Iterable[str]) -> None:
    """把 source 的白名单字段拷到 target。"""
    for name in fields:
        setattr(target, name, getattr(source, name))


def upsert(session: Session, entity: T, fields: Iterable[str]) -> T:
    """插入或更新一行，返回落库后的实体。"""
    field_list = list(fields)
    if not getattr(entity, "Id", None):
        entity.Id = new_id()
        entity.CreateBy = LOCAL
        entity.CreateTime = now()
        entity.Version = 1
        session.add(entity)
        session.commit()
        return entity

    old = session.get(type(entity), entity.Id)
    if old is None:
        entity.CreateBy = LOCAL
        entity.CreateTime = now()
        entity.Version = 1
        session.add(entity)
        session.commit()
        return entity

    assign(old, entity, field_list)
    old.ModifyBy = LOCAL
    old.ModifyTime = now()
    old.Version = (old.Version or 0) + 1
    session.add(old)
    session.commit()
    return old


def unbind(session: Session, model, predicate, field: str) -> int:
    """把匹配行的外键置空（保留数据，不留悬空引用）。返回处理条数。"""
    rows = session.execute(select(model).where(predicate)).scalars().all()
    for row in rows:
        setattr(row, field, "")
        row.ModifyBy = LOCAL
        row.ModifyTime = now()
        session.add(row)
    session.commit()
    return len(rows)


def delete_where(session: Session, model, predicate) -> int:
    """按条件删除，返回删除条数。"""
    rows = session.execute(select(model).where(predicate)).scalars().all()
    for row in rows:
        session.delete(row)
    session.commit()
    return len(rows)


def has_table(session: Session, name: str) -> bool:
    """表是否存在。阶段 2 的表还没建时，删除影响预览要能优雅跳过。"""
    return inspect(session.get_bind()).has_table(name)
