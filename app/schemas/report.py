"""周报的 schema。"""

from __future__ import annotations

from app.schemas.common import BaseIn

__all__ = ["WeeklySection", "WeeklyReport"]


class WeeklySection(BaseIn):
    Title: str = ""
    Note: str = ""
    Lines: list[str] = []


class WeeklyReport(BaseIn):
    Title: str = ""
    Range: str = ""
    Summary: str = ""
    Days: int = 0
    Sections: list[WeeklySection] = []
    Markdown: str = ""
