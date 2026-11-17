"""运行错误留痕：对应 C# 的 WorkHub/Services/ErrorLogService.cs。

出问题时不必只翻日志文件，最近若干条可直接在设置页查看。
"""

from __future__ import annotations

import logging
import traceback

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.error_log_rules import title as error_title
from app.common.error_log_rules import trim
from app.models.system import WhError
from app.services.crud import LOCAL, now

logger = logging.getLogger("workhub.error")

__all__ = ["ErrorLogService"]


class ErrorLogService:
    def __init__(self, session: Session):
        self._session = session

    def write(
        self,
        level: str,
        source: str,
        message: str,
        detail: str | None = None,
        path: str | None = None,
        user_name: str | None = None,
    ) -> None:
        """写一条错误。永远不抛异常。"""
        try:
            self._session.add(
                WhError(
                    Time=now(),
                    Level=trim(level, 20),
                    Source=trim(source, 100),
                    Message=trim(message, 300),
                    Detail=trim(detail, 4000),
                    Path=trim(path, 300),
                    UserName=trim(user_name, 50),
                    CreateBy=LOCAL,
                    CreateTime=now(),
                )
            )
            self._session.commit()
        except Exception as exc:
            logger.warning("错误日志写入失败：%s", exc)
            self._session.rollback()

    def write_exception(
        self,
        exc: BaseException,
        path: str | None = None,
        user_name: str | None = None,
        source: str | None = None,
    ) -> None:
        """把异常写进库（类型 + 消息首行 + 完整堆栈）。"""
        self.write(
            "Error",
            source or error_title(exc),
            str(exc),
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            path,
            user_name,
        )

    def recent(self, take: int = 50) -> list[WhError]:
        """最近若干条，按时间倒序。"""
        count = min(200, max(1, int(take)))
        rows = self._session.execute(select(WhError)).scalars().all()
        return sorted(rows, key=lambda item: item.Time or now(), reverse=True)[:count]

    def clear(self) -> int:
        rows = self._session.execute(select(WhError)).scalars().all()
        for row in rows:
            self._session.delete(row)
        self._session.commit()
        return len(rows)
