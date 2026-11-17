"""工具历史记录：对应 C# 的 WorkHub/Services/ToolService.cs。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import WhToolPref
from app.services.crud import LOCAL, now

__all__ = ["ToolService", "KEEP", "INPUT_LIMIT"]

KEEP = 30
INPUT_LIMIT = 1800


class ToolService:
    def __init__(self, session: Session):
        self._session = session

    def record(self, tool_id: str, tool_name: str | None, input_text: str) -> str:
        """记录一次工具输入（超长截断，每工具仅保留最近 30 条）。"""
        if not (tool_id or "").strip() or not (input_text or "").strip():
            return ""
        if not input_text:
            return ""

        history = self.history(tool_id)
        # 与上一条相同则不重复记账
        if history and history[0].Input == input_text:
            return ""

        truncated = input_text[:INPUT_LIMIT] + "…（已截断）" if len(input_text) > INPUT_LIMIT else input_text
        self._session.add(
            WhToolPref(
                ToolId=tool_id,
                ToolName=tool_name,
                Input=truncated,
                CreateBy=LOCAL,
                CreateTime=now(),
            )
        )
        self._session.commit()

        rows = self._all_for(tool_id)
        for old in rows[KEEP:]:
            self._session.delete(old)
        self._session.commit()
        return "已记录"

    def history(self, tool_id: str) -> list[WhToolPref]:
        """取该工具最近的输入记录（新→旧，最多 10 条）。"""
        if not (tool_id or "").strip():
            return []
        return self._all_for(tool_id)[:10]

    def all_prefs(self) -> list[WhToolPref]:
        """全部工具使用记录。"""
        return list(self._session.execute(select(WhToolPref)).scalars().all())

    def _all_for(self, tool_id: str) -> list[WhToolPref]:
        rows = list(self._session.execute(select(WhToolPref).where(WhToolPref.ToolId == tool_id)).scalars().all())
        return sorted(rows, key=lambda item: item.CreateTime or now(), reverse=True)
