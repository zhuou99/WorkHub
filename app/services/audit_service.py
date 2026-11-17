"""审计留痕：对应 C# 的 WorkHub/Services/AuditService.cs。

写失败只记日志，绝不把业务动作判成失败——审计是旁路。
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import WhAuditLog
from app.services.crud import LOCAL, now

logger = logging.getLogger("workhub.audit")

__all__ = ["AuditService"]


class AuditService:
    def __init__(self, session: Session):
        self._session = session

    def write(
        self,
        kind: str,
        action: str,
        success: bool,
        detail: str | None = None,
        user_name: str | None = None,
        ip: str | None = None,
    ) -> None:
        """写一条审计。永远不抛异常。"""
        try:
            self._session.add(
                WhAuditLog(
                    Time=now(),
                    Kind=_trim(kind, 20),
                    Action=_trim(action, 50),
                    UserName=_trim(user_name, 50),
                    Ip=_trim(ip, 64),
                    Success=success,
                    Detail=_trim(detail, 500),
                    CreateBy=LOCAL,
                    CreateTime=now(),
                )
            )
            self._session.commit()
        except Exception as exc:
            # 审计是旁路：数据库忙、表结构未同步时都不能影响登录/备份等主流程。
            logger.warning("审计写入失败：%s/%s：%s", kind, action, exc)
            self._session.rollback()

    def recent(self, take: int = 50) -> list[WhAuditLog]:
        """最近若干条，按时间倒序。"""
        count = min(500, max(1, int(take)))
        rows = self._session.execute(select(WhAuditLog)).scalars().all()
        return sorted(rows, key=lambda item: item.Time or now(), reverse=True)[:count]

    def clear(self) -> int:
        """清空全部审计，返回删除条数。"""
        rows = self._session.execute(select(WhAuditLog)).scalars().all()
        for row in rows:
            self._session.delete(row)
        self._session.commit()
        return len(rows)


def _trim(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit] if len(value) > limit else value
